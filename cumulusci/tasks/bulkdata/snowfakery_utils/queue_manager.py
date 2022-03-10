import queue
import random
import shutil
import time
import typing as T
from collections import defaultdict
from multiprocessing import Lock
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


class SnowfakeryChannelManager:
    """The channels describe the 'shape' of the communication

    The normal case is a single, parallelized, bulk channel,
    multi-threaded on client and server, using a single user
    account.

    Using .load.yml you can add more channels, utilizing
    more user accounts which can speed up throughput in
    a few cases."""

    def __init__(
        self,
        subtask_configurator,
        *,
        project_config,
        logger,
    ):
        # Look at the docstring on get_results_report to understand
        # what this queue is for.
        #
        # Be careful to use a Queue class appropriate to
        # the spawn type (thread, process) you're using.
        #
        # Snowfakery runs its loader in threads, so queue.Queue()
        # works.
        #
        # multiprocessing.Manager().Queue() also seems to work,
        # and work across processes, (PR #3080) but it's dramatically
        # slower. See attachment to PR #3076
        self.results_reporter = queue.Queue()
        self.channels = []
        self.project_config = project_config
        self.logger = logger
        self.subtask_configurator = subtask_configurator
        self.start_time = time.time()

    def add_channel(
        self,
        org_config: OrgConfig,
        num_generator_workers: int,
        num_loader_workers: T.Optional[int],
        working_directory: Path,
        recipe_options: dict,
    ):
        if not num_loader_workers:
            num_loader_workers = num_generator_workers * WORKER_TO_LOADER_RATIO

        self.channels.append(
            Channel(
                project_config=self.project_config,
                org_config=org_config,
                num_generator_workers=num_generator_workers,
                num_loader_workers=num_loader_workers,
                working_directory=working_directory,
                subtask_configurator=self.subtask_configurator,
                logger=self.logger,
                results_reporter=self.results_reporter,
                recipe_options=recipe_options,
            )
        )

    def tick(
        self,
        upload_status,
        template_path: Path,
        tempdir: Path,
        portions: PortionGenerator,
        get_upload_status: T.Callable,
    ):
        """Called every few seconds, to make new data generators if needed."""
        # advance each channel's queues
        for channel in self.channels:
            channel.tick()

        # populate channels that have space
        self.assign_work_to_channels(
            upload_status,
            template_path,
            tempdir,
            portions,
            get_upload_status,
        )

    def assign_work_to_channels(
        self,
        upload_status,
        template_path: Path,
        tempdir: Path,
        portions: PortionGenerator,
        get_upload_status: T.Callable,
    ):
        def channel_with_free_space():
            return [channel for channel in self.channels if not channel.full]

        new_workers = [True]  # initial value to get into the while loop
        channels = channel_with_free_space()
        while (
            channels
            and any(new_workers)
            and not portions.done(upload_status.total_sets_working_on_or_uploaded)
        ):
            # randomize channels so the first one doesn't always grab all slots
            random.shuffle(channels)
            new_workers = [
                channel.make_new_worker(
                    template_path, tempdir, portions, get_upload_status
                )
                for channel in channels
            ]
            channels = channel_with_free_space()

    def get_upload_status(self, batch_size, sets_finished_while_generating_template):
        """Combine information from the different data sources into a single "report".

        Useful for debugging but also for making decisions about what to do next."""
        summed_statuses = defaultdict(int)
        for channel in self.channels:
            for key, value in channel.get_upload_status_for_channel().items():
                summed_statuses[key] += value

        summed_statuses["sets_finished"] += sets_finished_while_generating_template
        return UploadStatus(
            target_count=self.subtask_configurator.run_until.gap,
            elapsed_seconds=int(self.elapsed_seconds()),
            batch_size=batch_size,
            channels=len(self.channels),
            **summed_statuses,
        )

    def elapsed_seconds(self):
        return time.time() - self.start_time

    def failure_descriptions(self) -> T.List[str]:
        """Log failures from sub-processes to main process"""
        ret = []
        for channel in self.channels:
            ret.extend(channel.failure_descriptions())
        return ret

    def check_finished(self) -> bool:
        for channel in self.channels:
            channel.tick()
        return all([channel.check_finished() for channel in self.channels])

    def get_results_report(self, block=False):
        """
        This is a realtime reporting channel which could, in theory, be updated
        before sub-tasks finish. Currently no sub-tasks are coded to do that.

        The logical next step is to allow LoadData to monitor steps one by
        one or even batches one by one.

        Note that until we implement that, we are paying the complexity
        cost of a real-time channel but not getting the benefits of it."""
        return self.results_reporter.get(block=block)


class Channel:
    def __init__(
        self,
        *,
        project_config,
        org_config,
        num_generator_workers: int,
        num_loader_workers: int,
        working_directory: Path,
        subtask_configurator: SubtaskConfigurator,
        logger,
        recipe_options=None,
        results_reporter=None,
    ):
        self.project_config = project_config
        self.org_config = org_config
        self.num_generator_workers = num_generator_workers
        self.num_loader_workers = num_loader_workers
        self.working_directory = working_directory
        self.subtask_configurator = subtask_configurator
        self.run_until = subtask_configurator.run_until
        self.logger = logger
        self.results_reporter = results_reporter
        self.filesystem_lock = Lock()
        self.job_counter = 0
        recipe_options = recipe_options or {}
        self._configure_queues(recipe_options)

    def _configure_queues(self, recipe_options):
        """Configure two ParallelWorkerQueues for datagen and dataload"""
        try:
            connected_app = self.project_config.keychain.get_service(
                "connected_app", self.org_config.connected_app
            )
        except exc.ServiceNotConfigured:  # pragma: no cover
            # to discuss...when can this happen? What are the consequences?
            connected_app = None

        def data_generator_opts_callback(*args, **kwargs):
            return self.subtask_configurator.data_generator_opts(
                *args, recipe_options=recipe_options, **kwargs
            )

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
            make_task_options=data_generator_opts_callback,
            queue_size=0,
            num_workers=self.num_generator_workers,
        )
        # datagen queues do not get a result reporter because
        # a) we are less curious about how many records have
        #    been generated than we aare about how many are loaded
        # b) finding a queue type which is not prone to race conditions
        #    or perf slowdowns with "Process" task types (sub-processes)
        # is a challenge.
        self.data_gen_q = WorkerQueue(data_gen_q_config, self.filesystem_lock)

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
        self.load_data_q = WorkerQueue(
            load_data_q_config, self.filesystem_lock, self.results_reporter
        )

        self.data_gen_q.feeds_data_to(self.load_data_q)
        return self.data_gen_q, self.load_data_q

    def data_loader_new_directory_name(self, working_directory):
        return data_loader_new_directory_name(working_directory, self.run_until)

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
        template_path: Path,
        tempdir: Path,
        portions: PortionGenerator,
        get_upload_status: T.Callable,
    ):
        if (
            self.data_gen_q.num_free_workers and self.data_gen_q.full
        ):  # pragma: no cover
            # TODO: investigate the consequences of taking this branch out
            self.logger.info("Waiting before datagen (load queue is full)")
        else:
            upload_status = get_upload_status(
                portions.next_batch_size,
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

    def get_upload_status_for_channel(self):
        with self.filesystem_lock:

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
                "sets_being_loaded": set_count_from_names(
                    self.load_data_q.inprogress_jobs
                ),
                "max_num_loader_workers": self.num_loader_workers,
                "max_num_generator_workers": self.num_generator_workers,
                # todo: use row-level result from org load for better accuracy
                "sets_finished": set_count_from_names(self.load_data_q.outbox_jobs),
                "sets_failed": len(self.load_data_q.failed_jobs),
                # TODO: are these two redundant?
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
        with self.filesystem_lock:
            still_running = (
                len(
                    self.data_gen_q.workers
                    + self.data_gen_q.queued_job_dirs
                    + self.data_gen_q.inprogress_jobs
                    + self.load_data_q.workers
                    + self.load_data_q.inprogress_jobs
                    + self.load_data_q.queued_job_dirs
                )
                > 0
            )
        return not still_running


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


class UploadStatus(T.NamedTuple):
    """Single "report" of the current status of our processes."""

    batch_size: int
    sets_being_generated: int
    sets_queued_to_be_generated: int
    sets_being_loaded: int
    sets_queued_for_loading: int
    sets_finished: int
    target_count: int
    max_num_loader_workers: int
    max_num_generator_workers: int
    elapsed_seconds: int
    sets_failed: int
    inprogress_generator_jobs: int
    inprogress_loader_jobs: int
    data_gen_free_workers: int
    channels: int

    @property
    def total_in_flight(self):
        return (
            self.sets_queued_to_be_generated
            + self.sets_being_generated
            + self.sets_queued_for_loading
            + self.sets_being_loaded
        )

    @property
    def total_sets_working_on_or_uploaded(
        self,
    ):
        return self.total_in_flight + self.sets_finished

    def _display(self, detailed=False):
        most_important_stats = [
            "target_count",
            "total_sets_working_on_or_uploaded",
            "sets_finished",
            "sets_failed",
        ]
        if self.channels > 1:
            most_important_stats.append("channels")

        queue_stats = [
            "inprogress_generator_jobs",
            "inprogress_loader_jobs",
        ]

        def display_stats(keys):
            def format(a):
                return f"{a.replace('_', ' ').title()}: {getattr(self, a):,}"

            return (
                "\n"
                + "\n".join(
                    format(a)
                    for a in keys
                    if not a[0] == "_" and not callable(getattr(self, a))
                )
                + "\n"
            )

        rc = display_stats(most_important_stats)
        rc += "\n   ** Workers **\n"
        rc += display_stats(queue_stats)
        if detailed:
            rc += "\n   ** Internals **\n"
            rc += display_stats(
                set(dir(self)) - (set(most_important_stats) & set(queue_stats))
            )
        return rc
