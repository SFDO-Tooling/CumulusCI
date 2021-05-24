import typing as T
import shutil
from pathlib import Path
import json
import logging

from contextlib import contextmanager
from multiprocessing import get_context
from threading import Thread
from tempfile import gettempdir

from cumulusci.core.config import (
    UniversalConfig,
    BaseProjectConfig,
    OrgConfig,
)


from .parallel_worker import SharedConfig, WorkerConfig, ParallelWorker


logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)


class WorkerQueueConfig(SharedConfig):
    name: str
    parent_dir: Path
    failures_dir: Path = None
    task_class: T.Callable
    queue_size: int
    num_workers: int
    spawn_class: T.Callable
    outbox_dir: Path
    make_task_options: T.Callable[..., T.Mapping[str, T.Any]]

    def __init__(self, **kwargs):
        kwargs.setdefault("failures_dir", kwargs["parent_dir"] / "failures")
        kwargs.setdefault("outbox_dir", kwargs["parent_dir"] / "finished")
        super().__init__(True, **kwargs)


class WorkerQueue:
    next_queue = None
    context = get_context("spawn")
    Process = context.Process
    Thread = Thread

    def __init__(
        self,
        queue_config: WorkerQueueConfig,
    ):
        self.config = queue_config
        # convenience access to names
        self.__dict__.update(queue_config.__dict__)

        self.inbox_dir = self.parent_dir / f"{self.name}_inbox"
        self.inbox_dir.mkdir()
        self.inprogress_dir = self.parent_dir / f"{self.name}_inprogress"
        self.inprogress_dir.mkdir()

        self.outbox_dir = self.parent_dir / f"{self.name}_outbox"
        self.outbox_dir.mkdir()

        self.workers = []

    @property
    def full(self):
        i_am_full = not self.free_space
        upstream_is_full = bool(self.next_queue and self.next_queue.full)
        return i_am_full or upstream_is_full

    @property
    def free_space(self):
        return max(self.free_workers + self.queue_size - len(self.queued_jobs), 0)

    @property
    def empty(self):
        return (not self.queued_job_dirs) and (not self.inprogress_job_dirs)

    def feeds(self, other_queue: "WorkerQueue"):
        self.next_queue = other_queue
        try:
            # cleanup, but not a problem if it fails
            self.outbox_dir.rmdir()
        except OSError:
            pass
        self.outbox_dir = other_queue.inbox_dir

    @property
    def free_workers(self) -> int:
        return self.config.num_workers - len(self.workers)

    def push(
        self,
        job_dir: T.Optional[Path],
        name: str = None,
    ):
        assert not (job_dir and name), "Supply name or job_dir, not both"
        assert job_dir or name, "Supply name or job_dir"

        if self.full:
            raise ValueError("Queue is full")

        if not job_dir:
            job_dir = Path(gettempdir()) / "parallel_temp" / name
            job_dir.mkdir(parents=True, exist_ok=True)

        self._queue_job(job_dir)
        self.tick()

    @property
    def queued_job_dirs(self):
        return list(self.inbox_dir.iterdir())

    @property
    def queued_jobs(self):
        return [job.name for job in self.queued_job_dirs]

    @property
    def inprogress_job_dirs(self):
        # print("QQQ", list(self.inprogress_dir.iterdir()), str(self.inprogress_dir))
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

    def _start_job(self, job_dir: Path):
        options = self._get_job_options(job_dir)
        self.inprogress_dir.mkdir(exist_ok=True)

        working_dir = Path(shutil.move(job_dir, self.inprogress_dir))
        task_options = self.make_task_options(working_dir)
        worker_config = WorkerConfig(
            **self.config.__dict__,
            working_dir=working_dir,
            output_dir=self.outbox_dir,
            task_options=task_options,
        )
        worker_config.task_options.update(options)
        worker = ParallelWorker(self.config.spawn_class, worker_config)
        worker.start()
        self.workers.append(worker)

    def _get_job_options(self, job_dir: Path):
        job_dir_options = job_dir / "options.json"
        rc = {}
        if job_dir_options.exists():
            rc = json.loads(job_dir_options.read_text())
            # consider: should I delete this?
            # job_dir_options.unlink()

        return rc

    def _queue_job(self, job_dir: Path):
        job_dir = shutil.move(job_dir, self.inbox_dir)

    def terminate_all(self):
        for worker in self.workers:
            if worker.is_alive():
                try:
                    worker.terminate()
                except Exception as e:
                    logger.warn(f"Could not terminate worker: {e}")

    def tick(self):
        live_workers = []
        dead_workers = []
        for worker in self.workers:
            if worker.is_alive():
                live_workers.append(worker)
            else:
                dead_workers.append(worker)

        self.workers = live_workers

        for idx, job_dir in zip(range(self.free_workers), self.queued_job_dirs):
            logger.info(f"Starting job {job_dir}")
            self._start_job(job_dir)
        if self.next_queue:
            self.next_queue.tick()


import pytest
from cumulusci.tasks.util import Sleep


class DelaySpawner:
    def __init__(self, target, args):
        logger.info(f"Creating spawner {target} {args}")
        self.target = target
        self.args = args
        self._is_alive = False

    def start(self):
        logger.info(f"Starting spawner {self}")
        self._is_alive = True

    def _finish(self):
        self.target(*self.args)
        self._is_alive = False

    def is_alive(self):
        logger.info(f"Checking alive: {self}: {self._is_alive}")
        return self._is_alive


class TestWorkerQueue:
    @contextmanager
    def configure_worker_queue(self, parent_dir, **kwargs):
        project_config = BaseProjectConfig(
            UniversalConfig(),
            config={"project": {"package": "packageA"}},
        )
        org_config = OrgConfig({}, "dummy_config")

        config = WorkerQueueConfig(
            project_config=project_config,
            org_config=org_config,
            connected_app=None,
            redirect_logging=True,
            spawn_class=DelaySpawner,
            parent_dir=Path(parent_dir),
            **kwargs,
        )
        q = WorkerQueue(config)

        yield q

    def test_worker_queue(self, tmpdir):
        with self.configure_worker_queue(
            parent_dir=tmpdir,
            name="start",
            task_class=Sleep,
            make_task_options=lambda *args, **kwargs: {"seconds": 0},
            queue_size=3,
            num_workers=2,
        ) as q:
            assert not q.full
            assert q.free_workers == 2
            assert q.queued_job_dirs == []
            q.push(None, {}, "a")
            assert not q.full
            assert q.free_workers == 1
            assert len(q.queued_job_dirs) == 0
            q.tick()
            assert not q.full
            assert q.free_workers == 1
            assert len(q.queued_job_dirs) == 0
            q.workers[0].process._finish()
            q.tick()
            assert not q.full
            assert q.free_workers == 2
            assert len(q.queued_job_dirs) == 0
            q.tick()
            assert not q.full
            assert q.free_workers == 2
            assert len(q.queued_job_dirs) == 0
            q.push(None, {}, "bb")
            q.tick()
            assert not q.full
            assert q.free_workers == 1
            assert len(q.queued_job_dirs) == 0
            q.push(None, {}, "cc")
            q.tick()
            assert not q.full
            assert q.free_workers == 0
            assert len(q.queued_job_dirs) == 0
            q.push(None, {}, "dd")
            q.tick()
            assert not q.full
            assert q.free_workers == 0
            assert len(q.queued_job_dirs) == 1
            q.push(None, {}, "ee")
            q.tick()
            assert not q.full
            assert q.free_workers == 0
            assert len(q.queued_job_dirs) == 2
            q.push(None, {}, "ff")
            q.tick()
            assert q.full
            assert q.free_workers == 0
            assert len(q.queued_job_dirs) == 3

            with pytest.raises(ValueError):
                q.push(None, {}, "hh")

            assert q.full
            assert q.free_workers == 0
            assert len(q.queued_job_dirs) == 3

            for worker in q.workers:
                worker.process._finish()

            assert q.full
            assert q.free_workers == 0
            assert len(q.queued_job_dirs) == 3

            q.tick()

            assert not q.full
            assert q.free_workers == 0
            assert len(q.queued_job_dirs) == 1

            for worker in q.workers:
                worker.process._finish()

            q.tick()

            assert not q.full
            assert q.free_workers == 1
            assert len(q.queued_job_dirs) == 0

            for worker in q.workers:
                worker.process._finish()

            q.tick()

            assert not q.full
            assert q.free_workers == 2
            assert len(q.queued_job_dirs) == 0

            q.push(None, {}, "ii")
            q.push(None, {}, "jj")
            q.push(None, {}, "kk")
            q.push(None, {}, "ll")
            q.push(None, {}, "mm")
            with pytest.raises(ValueError):
                q.push(None, {}, "nn")

            q.tick()

            assert q.full
            assert q.free_workers == 0
            assert len(q.queued_job_dirs) == 3

    def test_worker_queues_together(self, tmpdir):
        with self.configure_worker_queue(
            parent_dir=tmpdir,
            name="start",
            task_class=Sleep,
            make_task_options=lambda *args, **kwargs: {"seconds": 0},
            queue_size=3,
            num_workers=2,
        ) as q1, self.configure_worker_queue(
            parent_dir=tmpdir,
            name="next",
            task_class=Sleep,
            make_task_options=lambda *args, **kwargs: {"seconds": 0},
            queue_size=3,
            num_workers=2,
        ) as q2:
            q1.feeds(q2)
            q1.push(None, {}, "a")
            assert not q1.full
            assert q1.free_workers == 1
            assert len(q1.queued_job_dirs) == 0
            q1.tick()
            q1.tick()
            assert not q1.full
            assert q1.free_workers == 1
            assert len(q1.queued_job_dirs) == 0

            for worker in q1.workers:
                worker.process._finish()
            q1.tick()
            q2.tick()
            assert not q2.full
            assert q1.free_workers == 2
            assert q2.free_workers == 1
            assert len(q2.queued_job_dirs) == 0

            q1.push(None, {}, "b")
            q1.push(None, {}, "c")
            q1.push(None, {}, "d")
            q1.push(None, {}, "e")

            for worker in q1.workers:
                worker.process._finish()
            q1.tick()
            q2.tick()

    def test_worker_queue_from_path(self, tmpdir):
        parentdirs = [
            "start_inprogress",
            "next_inprogress",
        ]

        def make_task_options(path: Path, *args, **kwargs):
            assert path.name == "foo"
            assert path.parent.name == parentdirs.pop(0), path.parent.name
            return {"seconds": 0}

        with self.configure_worker_queue(
            parent_dir=tmpdir,
            name="start",
            task_class=Sleep,
            make_task_options=make_task_options,
            queue_size=3,
            num_workers=2,
        ) as q1, self.configure_worker_queue(
            parent_dir=tmpdir,
            name="next",
            task_class=Sleep,
            make_task_options=make_task_options,
            queue_size=3,
            num_workers=2,
        ) as q2:
            q1.feeds(q2)
            foo = tmpdir / "foo"
            foo.mkdir()
            assert not q1.full
            assert q1.free_workers == 2
            assert q1.queued_job_dirs == []
            q1.push(foo, {})
            assert not q1.full
            assert q1.free_workers == 1
            assert len(q1.queued_job_dirs) == 0
            q1.tick()

            for worker in q1.workers:
                worker.process._finish()

            q1.tick()
            q2.tick()
            assert q2.inprogress_jobs == ["foo"]
            q2.tick()

            for worker in q2.workers:
                worker.process._finish()
            q2.tick()
            assert q2.outbox_jobs == ["foo"]
