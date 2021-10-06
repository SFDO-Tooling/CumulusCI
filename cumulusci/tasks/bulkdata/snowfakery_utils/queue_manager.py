# TODO: make it so jobs are striped across shards
# TODO: pass recipe options to recipe
# TODO: implement full serial mode

import random
import shutil
import typing as T
from collections import defaultdict
from pathlib import Path

import cumulusci.core.exceptions as exc
from cumulusci.core.config import OrgConfig
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


class SnowfakeryShardManager:
    def __init__(
        self,
        *,
        project_config,
        logger,
    ):
        self.results_reporter = WorkerQueue.context.Queue()
        self.shards = []
        self.project_config = project_config
        self.logger = logger

    def add_shard(
        self,
        org_config: OrgConfig,
        num_generator_workers: int,
        working_directory: Path,
        subtask_configurator: SubtaskConfigurator,
    ):
        self.shards.append(
            Shard(
                project_config=self.project_config,
                org_config=org_config,
                num_generator_workers=num_generator_workers,
                working_directory=working_directory,
                subtask_configurator=subtask_configurator,
                logger=self.logger,
                results_reporter=self.results_reporter,
            )
        )

    @property
    def num_loader_workers(self):
        return sum(shard.num_loader_workers for shard in self.shards)

    def tick(
        self,
        upload_status,
        template_path: Path,
        tempdir: Path,
        portions: PortionGenerator,
        get_upload_status: T.Callable,
    ):
        """Called every few seconds, to make new data generators if needed."""
        # advance each shard's queues
        for shard in self.shards:
            shard.tick()

        # populate shards that have space
        self.populate_shards(
            upload_status,
            template_path,
            tempdir,
            portions,
            get_upload_status,
        )

    def populate_shards(
        self,
        upload_status,
        template_path: Path,
        tempdir: Path,
        portions: PortionGenerator,
        get_upload_status: T.Callable,
    ):
        def ready_shards():
            return [shard for shard in self.shards if not shard.full]

        new_workers = [True]
        shards = ready_shards()
        while (
            shards
            and any(new_workers)
            and not portions.done(upload_status.total_sets_working_on_or_uploaded)
        ):
            # randomize shards so the first one doesn't always grab all slots
            random.shuffle(shards)
            new_workers = [
                shard.make_new_worker(
                    upload_status, template_path, tempdir, portions, get_upload_status
                )
                for shard in shards
            ]
            shards = ready_shards()

    def get_upload_status(self):
        summed_statuses = defaultdict(int)
        for shard in self.shards:
            for key, value in shard.get_upload_status_for_shard().items():
                summed_statuses[key] += value
        return summed_statuses

    def failure_descriptions(self) -> T.List[str]:
        """Log failures from sub-processes to main process"""
        ret = []
        for shard in self.shards:
            ret.extend(shard.failure_descriptions())
        return ret

    def check_finished(self) -> bool:
        for shard in self.shards:
            shard.tick()
        return all([shard.check_finished() for shard in self.shards])

    def get_results_report(self, block=False):
        return self.results_reporter.get(block=block)

    # @property
    # def outbox_dir(self):
    #     outbox_dirs = [shard.outbox_dir for shard in self.shards]
    #     # should be just one
    #     assert len(set(outbox_dirs)) == 1, set(outbox_dirs)
    #     return outbox_dirs[0]


class Shard:
    def __init__(
        self,
        *,
        project_config,
        org_config,
        num_generator_workers: int,
        working_directory: Path,
        subtask_configurator: SubtaskConfigurator,
        logger,
        results_reporter=None,
    ):
        self.project_config = project_config
        self.org_config = org_config
        self.num_generator_workers = num_generator_workers
        self.job_counter = 0
        self.working_directory = working_directory
        self.subtask_configurator = subtask_configurator
        self.run_until = subtask_configurator.run_until
        self.logger = logger
        self.results_reporter = results_reporter
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
        self.load_data_q = WorkerQueue(load_data_q_config, self.results_reporter)

        self.data_gen_q.feeds_data_to(self.load_data_q)
        return self.data_gen_q, self.load_data_q

    def data_loader_new_directory_name(self, working_directory):
        return data_loader_new_directory_name(working_directory, self.run_until)

    @property
    def num_loader_workers(self):
        return self.num_generator_workers * WORKER_TO_LOADER_RATIO

    def tick(
        self,
    ):
        """Called every few seconds, to make new data generators if needed."""
        self.data_gen_q.tick()

    @property
    def full(self):
        return self.data_gen_q.full

    def make_new_worker(
        self,
        upload_status,
        template_path: Path,
        tempdir: Path,
        portions: PortionGenerator,
        get_upload_status: T.Callable,
    ):
        if self.data_gen_q.num_free_workers and self.data_gen_q.full:
            self.logger.info("Waiting before datagen (load queue is full)")
        else:
            upload_status = get_upload_status(
                portions.next_batch_size,
                template_path,
            )
            self.job_counter += 1
            batch_size = portions.next_batch(
                upload_status.total_sets_working_on_or_uploaded
            )
            if not batch_size:
                self.logger.info("All scheduled portions generated and being uploaded")
                return

            job_dir = self.generator_data_dir(
                self.job_counter, template_path, batch_size, tempdir
            )
            self.data_gen_q.push(job_dir)
            return job_dir

    def generator_data_dir(self, idx, template_path, batch_size, parent_dir):
        """Create a new generator directory with a name based on index and batch_size"""
        assert batch_size > 0
        data_dir = parent_dir / (str(idx) + "_" + str(batch_size))
        shutil.copytree(template_path, data_dir)
        return data_dir

    def get_upload_status_for_shard(self):
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

    @property
    def outbox_dir(self):
        return self.load_data_q.outbox_dir


# TODO: This function is actually based on the number generated,
#       because it is called before the load.
#       If there are row errors, it will drift out of correctness
#       Code needs to be updated to rename again after load.
#       Or move away from using directory names for math altogether.
def data_loader_new_directory_name(working_dir: Path, run_until):
    """Change the directory name to reflect the true number of sets created."""

    if not run_until.sobject_name:
        return working_dir

    wd = SnowfakeryWorkingDirectory(working_dir)
    count = wd.get_record_counts()[run_until.sobject_name]

    path, _ = str(working_dir).rsplit("_", 1)
    new_working_dir = Path(path + "_" + str(count))
    return new_working_dir
