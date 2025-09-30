import json
import logging
import shutil
import typing as T
from contextlib import contextmanager
from multiprocessing import Queue
from pathlib import Path
from traceback import format_exc

from pydantic.v1 import BaseModel

from cumulusci.core.config import (
    BaseConfig,
    BaseProjectConfig,
    ConnectedAppOAuthConfig,
    OrgConfig,
    TaskConfig,
    UniversalConfig,
)
from cumulusci.core.keychain.subprocess_keychain import SubprocessKeychain
from cumulusci.core.utils import import_global


class SharedConfig(BaseModel):
    "Properties available both in the Queue and also each worker"
    task_class: type
    project_config: BaseProjectConfig
    org_config: OrgConfig
    failures_dir: Path
    redirect_logging: bool
    connected_app: T.Optional[BaseConfig]  # a connected app service
    outbox_dir: Path  # where do jobs go when they are done

    class Config:
        arbitrary_types_allowed = True


class WorkerConfig(SharedConfig):
    working_dir: Path
    task_options: T.Mapping

    def as_dict(self):
        """Convert to a dict of basic data structures/types, similar to JSON."""
        # runs in the parent process
        return {
            "task_class": dotted_class_name(self.task_class),
            "org_config_class": dotted_class_name(self.org_config.__class__),
            "task_options": self.task_options,
            "working_dir": str(self.working_dir),
            "outbox_dir": str(self.outbox_dir),
            "failures_dir": str(self.failures_dir),
            "org_config": (
                self.org_config.config,
                self.org_config.name,
            ),
            "connected_app": self.connected_app.config if self.connected_app else None,
            "redirect_logging": self.redirect_logging,
            "project_config": {
                "project": {"package": self.project_config.config["project"]["package"]}
            },
        }

    @staticmethod
    def from_dict(worker_config_json):  # todo: rename to `worker_config_dct`
        """Read from a dict of basic data structures/types, similar to JSON."""
        # runs in the child process
        org_config_class = import_global(worker_config_json["org_config_class"])
        org_config = org_config_class(*worker_config_json["org_config"])

        task_options = worker_config_json["task_options"]

        universal_config = UniversalConfig()
        project_config = BaseProjectConfig(
            universal_config,
            config=worker_config_json["project_config"],
        )
        return WorkerConfig(
            task_class=import_global(worker_config_json["task_class"]),
            task_options=task_options,
            project_config=project_config,
            org_config=org_config,
            working_dir=Path(worker_config_json["working_dir"]),
            outbox_dir=Path(worker_config_json["outbox_dir"]),
            failures_dir=Path(worker_config_json["failures_dir"]),
            connected_app=ConnectedAppOAuthConfig(worker_config_json["connected_app"])
            if worker_config_json["connected_app"]
            else None,
            redirect_logging=worker_config_json["redirect_logging"],
        )


def dotted_class_name(cls):
    """Generate a dotted class name for a class object"""
    return cls.__module__ + "." + cls.__name__


class TaskWorker:
    """This class runs in a sub-thread or sub-process"""

    def __init__(self, worker_dict, results_reporter, filesystem_lock):
        self.worker_config = WorkerConfig.from_dict(worker_dict)
        self.redirect_logging = worker_dict["redirect_logging"]
        self.results_reporter = results_reporter
        self.filesystem_lock = filesystem_lock
        assert filesystem_lock

    def __getattr__(self, name):
        """Easy access to names from the config"""
        return getattr(self.worker_config, name)

    def _make_task(self, task_class, logger):
        """Instantiate a CCI task"""
        if "working_directory" in self.task_class.task_options:
            self.task_options["working_directory"] = self.worker_config.working_dir
        task_config = TaskConfig({"options": self.task_options})
        connected_app = self.connected_app
        keychain = SubprocessKeychain(connected_app)
        self.project_config.set_keychain(keychain)
        self.org_config.keychain = keychain
        return task_class(
            project_config=self.project_config,
            task_config=task_config,
            org_config=self.org_config,
            logger=logger,
        )

    def save_exception(self, e):
        """Write an exception to disk for later analysis"""
        exception_file = self.working_dir / "exception.txt"
        exception_file.write_text(format_exc())

    def run(self):
        """The main code that runs in a sub-thread or sub-process"""
        with self.make_logger() as (logger, logfile):
            try:
                self.subtask = self._make_task(self.task_class, logger)
                self.subtask()
                logger.info(str(self.subtask.return_values))
                logger.info("SubTask Success!")
                if self.results_reporter:
                    self.results_reporter.put(
                        {
                            "status": "success",
                            "results": self.subtask.return_values,
                            "directory": str(self.working_dir),
                        }
                    )
            except BaseException as e:
                logger.info(f"Failure detected: {e}")
                self.save_exception(e)
                self.failures_dir.mkdir(exist_ok=True)
                logfile.close()
                with self.filesystem_lock:
                    shutil.move(str(self.working_dir), str(self.failures_dir))
                if self.results_reporter:
                    self.results_reporter.put({"status": "error", "error": str(e)})
                raise

        try:
            with self.filesystem_lock:
                self.outbox_dir.mkdir(exist_ok=True)
                shutil.move(str(self.working_dir), str(self.outbox_dir))
        except BaseException as e:
            self.save_exception(e)
            raise

    @contextmanager
    def make_logger(self):
        """Log to a file for potential later inspection"""
        filename = self.working_dir / f"{self.task_class.__name__}.log"
        with filename.open("w", encoding="utf-8") as f:
            logger = logging.Logger(self.task_class.__name__)

            formatter = logging.Formatter(fmt="%(asctime)s: %(message)s")
            handler = logging.StreamHandler(stream=f)
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.propagate = False
            yield logger, f


def run_task_in_worker(worker_dict: dict, results_reporter: Queue, filesystem_lock):
    assert filesystem_lock
    worker = TaskWorker(worker_dict, results_reporter, filesystem_lock)
    return worker.run()


def simplify(x):
    if isinstance(x, Path):
        return str(x)


class ParallelWorker:
    """Representation of the worker in the controller processs"""

    def __init__(
        self,
        spawn_class,
        worker_config: WorkerConfig,
        results_reporter: Queue,
        filesystem_lock,
    ):
        self.spawn_class = spawn_class
        self.worker_config = worker_config
        self.results_reporter = results_reporter
        self.filesystem_lock = filesystem_lock
        assert filesystem_lock

    def _validate_worker_config_is_simple(self, worker_config):
        assert json.dumps(worker_config, default=simplify)

    def start(self):
        """Simplify config to 'json'-like datastructure, and pass to sub-process"""
        dct = self.worker_config.as_dict()
        self._validate_worker_config_is_simple(dct)

        # under the covers, Python will pass this as Pickles.
        self.process = self.spawn_class(
            target=run_task_in_worker,
            args=[dct, self.results_reporter, self.filesystem_lock],
            # quit if the parent process decides to exit (e.g. after a timeout)
            daemon=True,
        )
        self.process.start()

    def is_alive(self) -> bool:
        return self.process.is_alive()

    def terminate(self):
        # Note that this will throw an exception for threads
        # and should be used carefully for processes because
        # they won't necesssarily cleanup tempdirs and other
        # resources.
        self.process.terminate()

    def __repr__(self):
        return f"<Worker {self.worker_config.task_class.__name__} {self.worker_config.working_dir.name} Alive: {self.is_alive()}>"
