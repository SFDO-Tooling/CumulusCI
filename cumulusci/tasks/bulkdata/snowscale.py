import shutil
import time
import queue
import os
import typing as T

from pathlib import Path
from multiprocessing import Process
from cumulusci.utils.parallel.queue_workaround import MyQueue, SharedCounter
from contextlib import contextmanager
import logging
import coloredlogs
from tempfile import TemporaryDirectory


from cumulusci.tasks.bulkdata.generate_from_yaml import GenerateDataFromYaml
from cumulusci.tasks.bulkdata.load import LoadData
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.tasks.bulkdata.generate_and_load_data_from_yaml import (
    GenerateAndLoadDataFromYaml,
)
from cumulusci.core.config import TaskConfig
from cumulusci.cli.logger import init_logger

bulkgen_task = "cumulusci.tasks.bulkdata.generate_from_yaml.GenerateDataFromYaml"


class SnowScale(BaseSalesforceApiTask):
    """ """

    task_docs = """
    """
    default_max_batch_size = 300  # FIXME

    task_options = {
        **GenerateAndLoadDataFromYaml.task_options,
        "max_batch_size": {},
        "num_generator_workers": {},
        "num_uploader_workers": {},
    }

    def _init_options(self, kwargs):
        args = {"data_generation_task": bulkgen_task, **kwargs}
        super()._init_options(args)

    def _validate_options(self):
        # long-term solution: psutil.cpu_count(logical=False)
        self.num_generator_workers = int(self.options.get("num_generator_workers", 4))
        self.num_uploader_workers = int(self.options.get("num_uploader_workers", 25))

    def _run_task(self):
        self.upload_queue = MyQueue()
        self.job_counter = SharedCounter(0)
        with self._generate_and_load_initial_batch() as (tempdir, template_path):
            os.system(f"code {tempdir}")  # FIXME
            assert tempdir.exists()
            generators_path = Path(tempdir) / "generators"
            generators_path.mkdir()
            loaders_path = Path(tempdir) / "loaders"
            loaders_path.mkdir()
            self.queue_for_loading_directory = loaders_path / "queue"
            self.queue_for_loading_directory.mkdir()
            self.archive_directory = Path(tempdir, "archive")
            self.archive_directory.mkdir()

            def new_generate_process(idx):
                idx = idx + 1  # use 1-based indexing
                args = [
                    generators_path / str(idx),
                    template_path,
                    idx,
                ]
                return Process(target=self._generate_process, args=args)

            def new_upload_process(idx):
                idx = idx + 1  # use 1-based indexing
                args = [loaders_path, idx]
                return Process(target=self._load_process, args=args)

            self._spawn_processes(new_generate_process, self.num_generator_workers)
            num_uploader_workers = self._spawn_processes(
                new_upload_process, self.num_uploader_workers
            )
            assert tempdir.exists()
            for worker in num_uploader_workers:
                assert tempdir.exists()
                worker.join()
            print("DONE!!!!")  # FIXME

            # for worker in num_uploader_workers:
            #     num_uploader_workers.join()

    @staticmethod
    def _spawn_processes(func, number):
        processes = list(map(func, range(number)))
        for process in processes:
            process.start()
        return processes

    def _generate_process(
        self, working_parent_dir: Path, template_path: Path, worker_idx: int
    ):
        working_parent_dir.mkdir(exist_ok=True)
        batch_size = 10000
        while 1:  # FIXME
            while self.upload_queue.qsize() > self.num_uploader_workers:
                print(f"Waiting due to queue size of {self.upload_queue.qsize()}")
                batch_size = min(batch_size * 2, 250000)
                print(f"Expanding batch_size to {batch_size}")
                time.sleep(10)
            idx = self.job_counter.increment()
            working_dir = working_parent_dir / str(idx)
            shutil.copytree(template_path, working_dir)
            print(__file__, "Workingdir", working_dir)
            database_file = working_dir / "generated_data.db"
            # not needed once just_once is implemented
            mapping_file = working_dir / "temp_mapping.yml"
            database_url = f"sqlite:///{database_file}"
            # f"{working_directory}/continuation.yml"
            assert working_dir.exists()
            options = {
                **self.options,
                "database_url": database_url,
                "working_directory": working_dir,
                "num_records": batch_size,  # FIXME
                "generate_mapping_file": mapping_file,
                # continuation_file =       # FIXME
            }
            self._invoke_subtask(GenerateDataFromYaml, options, working_dir)
            assert mapping_file.exists()
            print("GENERATED", working_dir)
            outdir = shutil.move(working_dir, self.queue_for_loading_directory)
            self.upload_queue.put(outdir)
            print("Queued", outdir)

    def _load_process(self, working_parent_dir: Path, worker_idx: int):
        working_parent_dir.mkdir(exist_ok=True)
        while 1:  # FIXME
            try:
                generator_working_directory = self.upload_queue.get(block=False)
            except queue.Empty:
                generator_working_directory = None
                time.sleep(10)
            if generator_working_directory:
                working_directory = shutil.move(
                    generator_working_directory, working_parent_dir
                )
                working_directory = Path(working_directory)
                mapping_file = working_directory / "temp_mapping.yml"
                database_file = working_directory / "generated_data.db"
                assert mapping_file.exists(), mapping_file
                assert database_file.exists(), database_file
                database_url = f"sqlite:///{database_file}"

                options = {
                    "mapping": mapping_file,
                    "reset_oids": False,
                    "database_url": database_url,
                }
                self._invoke_subtask(LoadData, options, working_directory)
                shutil.move(working_directory, self.archive_directory)

    def _invoke_subtask(
        self, TaskClass: type, subtask_options: T.Mapping[str, T.Any], working_dir: Path
    ):
        subtask_config = TaskConfig({"options": subtask_options})
        subtask = TaskClass(
            project_config=self.project_config,
            task_config=subtask_config,
            org_config=self.org_config,
            flow=self.flow,
            name=self.name,
            stepnum=self.stepnum,
        )
        with self._add_tempfile_logger(working_dir / f"{TaskClass.__name__}.log"):
            subtask()

    @contextmanager
    def _generate_and_load_initial_batch(self) -> Path:
        with TemporaryDirectory() as tempdir:
            template_dir = Path(tempdir) / "template"
            template_dir.mkdir()
            # FIXME:
            # self._generate_and_load_batch(template_dir, {"num_records": 1})
            yield Path(tempdir), template_dir

    def _generate_and_load_batch(self, tempdir, options) -> Path:
        options = {**self.options, **options, "working_directory": tempdir}
        self._invoke_subtask(GenerateAndLoadDataFromYaml, options, tempdir)
        print("Generated and Loaded")

    # def _generate_batch(self, tempdir, options) -> Path:
    #     options = {**self.options, **options, "working_directory": tempdir}
    #     task_config = TaskConfig({"options": options})
    #     task = GenerateDataFromYaml(
    #         self.project_config, task_config, org_config=self.org_config
    #     )
    #     with self._add_tempfile_logger(working_directory):
    #         task()
    #     print("Generated")

    # def _load_batch(self, working_directory, options) -> Path:
    #     mapping_file = f"{working_directory}/temp_mapping.yml"
    #     database_url = f"sqlite:///{working_directory}/generated_data.db"
    #     continuation_file = f"{working_directory}/continuation.yml"
    #     assert mapping_file.exists()
    #     subtask_options = {
    #         **options,
    #         "continuation_file": str(continuation_file),
    #         "mapping": str(mapping_file),
    #         "reset_oids": False,
    #         "database_url": database_url,
    #         "working_directory": working_directory,
    #     }

    #     task_config = TaskConfig({"options": options})
    #     task = LoadData(
    #         self.project_config, task_config, org_config=self.org_config
    #     )
    #     with self._add_tempfile_logger(working_directory):
    #         task()
    #     print("Loaded")

    # def _generate_subsequent_batch(
    #     self, mytempdir: Path, template_path: Path, worker_index: int
    # ):
    #     print(f"Copying {template_path} -> {mytempdir}")
    #     shutil.copytree(template_path, mytempdir)
    #     # self.re_init_loggers()
    #     with self._add_tempfile_logger(mytempdir):
    #         total_workers = self.num_workers
    #         max_batch_size = int(
    #             self.options.get("max_batch_size", self.default_max_batch_size)
    #         )
    #         min_batch_size = max_batch_size // self.num_workers
    #         new_batch_size = min_batch_size * worker_index
    #         self._generate_batches(mytempdir, {"batch_size": new_batch_size})

    @contextmanager
    def _add_tempfile_logger(self, my_log: Path):
        init_logger()
        rootLogger = logging.getLogger("cumulusci")
        with open(my_log, "w") as f:
            handler = logging.StreamHandler(stream=f)
            handler.setLevel(logging.DEBUG)
            formatter = coloredlogs.ColoredFormatter(fmt="%(asctime)s: %(message)s")
            handler.setFormatter(formatter)

            rootLogger.addHandler(handler)
            try:
                yield f
            finally:
                rootLogger.removeHandler(handler)
