import shutil
import typing as T
from pathlib import Path

import cumulusci.core.exceptions as exc
from cumulusci.tasks.bulkdata.generate_from_yaml import GenerateDataFromYaml
from cumulusci.tasks.bulkdata.load import LoadData
from cumulusci.utils.parallel.task_worker_queues.parallel_worker_queue import (
    WorkerQueue,
    WorkerQueueConfig,
)

from .snowfakery_run_until import PortionGenerator
from .snowfakery_working_directory import SnowfakeryWorkingDirectory
from .subtask_configurator import SubtaskConfigurator

# number of portions we will allow to be on-disk waiting to be loaded
# higher numbers use more disk space.
LOAD_QUEUE_SIZE = 15
# more loader workers than generators because they spend so much time
# waiting for responses. 4:1 is an experimentally derived ratio
WORKER_TO_LOADER_RATIO = 4


# TODO: This class is too closely tied with the task parent
#       It was refactored out and future refactorings will
#       need to loosen the coupling further
class SnowfakeryQueueManager:
    def __init__(
        self,
        *,
        project_config,
        org_config,
        num_generator_workers: int,
        working_directory: Path,
        subtask_configurator: SubtaskConfigurator,
        logger,
    ):
        self.project_config = project_config
        self.org_config = org_config
        self.num_generator_workers = num_generator_workers
        self.job_counter = 0
        self.working_directory = working_directory
        self.subtask_configurator = subtask_configurator
        self.run_until = subtask_configurator.run_until
        self.logger = logger
        self.cached_counts = {}
        self._configure_queues()

    def _configure_queues(self):
        """Configure two ParallelWorkerQueues for datagen and dataload"""
        try:
            # in the future, the connected_app should come from the org
            connected_app = self.project_config.keychain.get_service("connected_app")
        except exc.ServiceNotConfigured:  # pragma: no cover
            # to discuss...when can this happen? What are the consequences?
            connected_app = None

        data_gen_q_config = WorkerQueueConfig(
            project_config=self.project_config,
            org_config=self.org_config,
            connected_app=connected_app,
            redirect_logging=True,
            # processes are better for compute-heavy tasks (in Python)
            spawn_class=WorkerQueue.Process,
            parent_dir=self.working_directory,
            name="data_gen",
            task_class=GenerateDataFromYaml,
            make_task_options=self.subtask_configurator.data_generator_opts,
            queue_size=0,
            num_workers=self.num_generator_workers,
        )
        self.data_gen_q = WorkerQueue(data_gen_q_config)

        load_data_q_config = WorkerQueueConfig(
            project_config=self.project_config,
            org_config=self.org_config,
            connected_app=connected_app,
            redirect_logging=True,
            spawn_class=WorkerQueue.Thread,
            parent_dir=self.working_directory,
            name="data_load",
            task_class=LoadData,
            make_task_options=self.subtask_configurator.data_loader_opts,
            queue_size=LOAD_QUEUE_SIZE,
            num_workers=self.num_loader_workers,
            rename_directory=self.data_loader_new_directory_name,
        )
        self.load_data_q = WorkerQueue(load_data_q_config)

        self.data_gen_q.feeds_data_to(self.load_data_q)
        return self.data_gen_q, self.load_data_q

    @property
    def num_loader_workers(self):
        return self.num_generator_workers * WORKER_TO_LOADER_RATIO

    def tick(
        self,
        upload_status,
        template_path: Path,
        tempdir: Path,
        portions: PortionGenerator,
        get_upload_status: T.Callable,
    ):
        """Called every few seconds, to make new data generators if needed."""
        self.data_gen_q.tick()

        if portions.done(
            upload_status.total_sets_working_on_or_uploaded
        ):  # pragma: no cover
            self.logger.info("Finished Generating")
        # queue is full
        elif self.data_gen_q.num_free_workers and self.data_gen_q.full:
            self.logger.info("Waiting before datagen (load queue is full)")
        else:
            for i in range(self.data_gen_q.num_free_workers):
                upload_status = get_upload_status(
                    portions.next_batch_size,
                    template_path,
                )
                self.job_counter += 1
                batch_size = portions.next_batch(
                    upload_status.total_sets_working_on_or_uploaded
                )
                if not batch_size:
                    self.logger.info(
                        "All scheduled portions generated and being uploaded"
                    )
                    break
                job_dir = self.generator_data_dir(
                    self.job_counter, template_path, batch_size, tempdir
                )
                self.data_gen_q.push(job_dir)

    # TODO: This method is actually based on the number generated,
    #       because it is called before the load.
    #       If there are row errors, it will drift out of correctness
    #       Code needs to be updated to rename again after load.
    #       Or move away from using directory names for math altogether.
    def data_loader_new_directory_name(self, working_dir: Path):
        """Change the directory name to reflect the true number of sets created."""

        cached_counts = self.cached_counts
        wd = SnowfakeryWorkingDirectory(working_dir)
        key = wd.index
        if key not in cached_counts:
            cached_counts[key] = wd.get_record_counts()

        if not self.run_until.sobject_name:
            return working_dir

        count = cached_counts[key][self.run_until.sobject_name]

        path, _ = str(working_dir).rsplit("_", 1)
        new_working_dir = Path(path + "_" + str(count))
        return new_working_dir

    def generator_data_dir(self, idx, template_path, batch_size, parent_dir):
        """Create a new generator directory with a name based on index and batch_size"""
        assert batch_size > 0
        data_dir = parent_dir / (str(idx) + "_" + str(batch_size))
        shutil.copytree(template_path, data_dir)
        return data_dir

    def get_upload_status(self):
        def set_count_from_names(names):
            return sum(int(name.split("_")[1]) for name in names)

        return {
            "sets_queued_to_be_generated": set_count_from_names(
                self.data_gen_q.queued_jobs
            ),
            "sets_being_generated": set_count_from_names(
                self.data_gen_q.inprogress_jobs
            ),
            "sets_queued_for_loading": set_count_from_names(
                self.load_data_q.queued_jobs
            ),
            # note that these may count as already imported in the org
            "sets_being_loaded": set_count_from_names(self.load_data_q.inprogress_jobs),
            "user_max_num_loader_workers": self.num_loader_workers,
            # todo: use row-level result from org load for better accuracy
            "sets_finished": set_count_from_names(self.load_data_q.outbox_jobs),
            "sets_failed": len(self.load_data_q.failed_jobs),
            "inprogress_generator_jobs": len(self.data_gen_q.inprogress_jobs),
            "inprogress_loader_jobs": len(self.load_data_q.inprogress_jobs),
            "data_gen_free_workers": self.data_gen_q.num_free_workers,
        }

    def failure_descriptions(self) -> T.List[str]:
        """Log failures from sub-processes to main process"""
        failure_dirs = set(
            self.load_data_q.failed_job_dirs + self.data_gen_q.failed_job_dirs
        )

        def error_from_dir(failure_dir: Path) -> T.Optional[str]:
            f = Path(failure_dir) / "exception.txt"
            if not f.exists():  # pragma: no cover
                return
            return f.read_text(encoding="utf-8").strip().split("\n")[-1]

        errors = [error_from_dir(failure_dir) for failure_dir in failure_dirs]
        return [error for error in errors if error is not None]

    def check_finished(self) -> bool:
        self.data_gen_q.tick()
        still_running = len(self.data_gen_q.workers + self.load_data_q.workers) > 0
        return not still_running

    def get_results_reporter(self, block=False):
        return self.load_data_q.results_reporter.get(block=block)

    @property
    def outbox_dir(self):
        return self.load_data_q.outbox_dir
