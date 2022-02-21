"""Represents an inbox and configuration for a set of processes
   that represent the same "step" in a pipeline.
   """

import logging
import shutil
import typing as T
from multiprocessing import get_context
from pathlib import Path
from queue import Queue
from tempfile import gettempdir
from threading import Thread

from .parallel_worker import ParallelWorker, SharedConfig, WorkerConfig

logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)


class WorkerQueueConfig(SharedConfig):
    """Configure a worker queue to do its job"""

    name: str
    parent_dir: Path
    failures_dir: Path = None  # where to put failures
    task_class: T.Callable  # what task class to use  # probably redundant
    queue_size: int  # how many jobs can be waiting before we start rejecting
    num_workers: int  # how many simultaneous workers?
    spawn_class: T.Callable  # spawner, e.g. threading.Thread, mp.Process, Inline
    # callable to generate task options
    make_task_options: T.Callable[..., T.Mapping[str, T.Any]]
    rename_directory: T.Optional[T.Callable]

    def __init__(self, **kwargs):
        kwargs.setdefault("failures_dir", kwargs["parent_dir"] / "failures")
        kwargs.setdefault(
            "outbox_dir", Path(kwargs["parent_dir"], kwargs["name"] + "_outbox")
        )
        super().__init__(**kwargs)


class WorkerQueue:
    """Represents an inbox and configuration for a set of processes
    that represent the same "step" in a pipeline.

    Queues are backed by folders which roughly follow the
    "hot folder" design pattern.

    "A folder that serves as a staging area for some purpose. The hot
    folder is continuously monitored, and when files are copied or
    dropped into it, they are automatically processed."

    The use of file system folders makes the queue's work
    externally observable.
    """

    next_queue = None  # is there another queue in the pipeline?
    context = get_context("spawn")  # use spawn strategy for processes

    # client uses these like enum values in WorkerQueueConfig.spawn_class
    Process = context.Process
    Thread = Thread

    def __init__(
        self,
        queue_config: WorkerQueueConfig,
        # be careful to pass a Queue compatible with your spawn_type
        # also, be VERY careful of race conditions.
        # multiprocessing.Queue seems prone to delays that cause
        # race conditions. See PR #3076 for more info.
        filesystem_lock,
        results_reporter: Queue = None,
    ):
        self.config = queue_config
        # convenience access to names
        self._create_dirs()
        self.workers = []
        self.results_reporter = results_reporter
        self.filesystem_lock = filesystem_lock

    def __getattr__(self, name):
        """Convenience proxy for config values
        note that local values will shadow them."""

        return getattr(self.config, name)

    def _create_dirs(self):
        """Setup my local dirs"""
        # work arrives in here
        self.inbox_dir = self.parent_dir / f"{self.name}_inbox"
        self.inbox_dir.mkdir()

        # I move it here for processing
        self.inprogress_dir = self.parent_dir / f"{self.name}_inprogress"
        self.inprogress_dir.mkdir()

        # And move it here when I am done.
        self.outbox_dir.mkdir()

    def feeds_data_to(self, other_queue: "WorkerQueue"):
        """Establish the relationship to the next queue"""
        self.next_queue = other_queue
        try:
            # cleanup, but not a problem if it fails
            self.outbox_dir.rmdir()
        except OSError:
            logger.info("Cannot remove outbox dir when connecting queues")
        # my output is your input.
        self.outbox_dir = other_queue.inbox_dir

    @property
    def full(self):
        i_am_full = not self.free_space
        downstream_is_full = bool(self.next_queue and self.next_queue.full)
        return i_am_full or downstream_is_full

    @property
    def free_space(self):
        return max(self.num_free_workers + self.queue_size - len(self.queued_jobs), 0)

    @property
    def empty(self):
        return (not self.queued_job_dirs) and (not self.inprogress_job_dirs)

    @property
    def num_free_workers(self) -> int:
        return self.config.num_workers - self.num_busy_workers

    @property
    def num_busy_workers(self) -> int:
        return len([w for w in self.workers if w.is_alive()])

    @property
    def queued_job_dirs(self):
        return list(self.inbox_dir.iterdir())

    @property
    def queued_jobs(self):
        return [job.name for job in self.queued_job_dirs]

    @property
    def inprogress_job_dirs(self):
        return list(self.inprogress_dir.iterdir())

    @property
    def inprogress_jobs(self):
        return [job.name for job in self.inprogress_job_dirs]

    @property
    def outbox_job_dirs(self):
        return list(self.outbox_dir.iterdir())

    @property
    def outbox_jobs(self):
        return [job.name for job in self.outbox_job_dirs]

    @property
    def failed_job_dirs(self):
        return list(self.failures_dir.iterdir()) if self.failures_dir.exists() else []

    @property
    def failed_jobs(self):
        return [job.name for job in self.failed_job_dirs]

    def push(
        self,
        job_dir: T.Optional[Path] = None,
        name: str = None,
    ):
        "Push a job (represented by a directory, or a name) onto this queue"

        # if there is no job_dir then the job is brand new and
        # has no data. Presumably my task class knows how to create
        # it. So I'll make my own job_dir based on `name`.

        assert not (job_dir and name), "Supply name or job_dir, not both"
        assert job_dir or name, "Supply name or job_dir"

        if self.full:
            raise ValueError("Queue is full")

        # as described above. No job_dir means I create one.
        if not job_dir:
            job_dir = Path(gettempdir()) / "parallel_temp" / name
            job_dir.mkdir(parents=True, exist_ok=True)

        self._queue_job(job_dir)
        self.tick()

    def _queue_job(self, job_dir: Path):
        """Enqueue a job"""
        shutil.move(str(job_dir), str(self.inbox_dir))

    def _start_job(self, job_dir: Path):
        """Start a job"""
        self.inprogress_dir.mkdir(exist_ok=True)
        working_dir = Path(shutil.move(str(job_dir), str(self.inprogress_dir)))

        # Jobs can rename their directories in case they store metadata
        # in directory names.
        if self.rename_directory:
            old_working_dir = working_dir
            working_dir = self.rename_directory(old_working_dir)
            shutil.move(str(old_working_dir), str(working_dir))

        # Individual jobs can override or add task options to the ones
        # generic to jobs in this queue. E.g. the number of records to
        # generate in a datagen context.
        task_options = self.make_task_options(working_dir)

        worker_config_data = self.config.__dict__.copy()
        worker_config_data.update(
            {
                "outbox_dir": self.outbox_dir,  # may have changed from default config
                "working_dir": working_dir,
                "task_options": task_options,
            }
        )

        worker_config = WorkerConfig(
            **worker_config_data,
        )

        worker = ParallelWorker(
            self.config.spawn_class,
            worker_config,
            self.results_reporter,
            self.filesystem_lock,
        )
        worker.start()
        self.workers.append(worker)

    def tick(self):
        """Things are moved from place to place in the 'tick'.
        The tick runs in the parent/controller/original process
        so there are no threading/locking issues."""
        self.workers = [w for w in self.workers if w.is_alive()]

        for idx, job_dir in zip(range(self.num_free_workers), self.queued_job_dirs):
            logger.info(f"Starting job {job_dir}")
            self._start_job(job_dir)
        if self.next_queue:
            self.next_queue.tick()
