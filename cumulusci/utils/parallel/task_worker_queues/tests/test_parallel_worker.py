from contextlib import contextmanager
from logging import getLogger
from multiprocessing import Lock
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import pytest

from cumulusci.core import exceptions as exc
from cumulusci.core.config import BaseProjectConfig, OrgConfig, UniversalConfig
from cumulusci.tasks.util import Sleep
from cumulusci.utils.parallel.task_worker_queues.parallel_worker import (
    ParallelWorker,
    SubprocessKeychain,
    TaskWorker,
    WorkerConfig,
)
from cumulusci.utils.parallel.task_worker_queues.parallel_worker_queue import (
    WorkerQueue,
    WorkerQueueConfig,
)

logger = getLogger(__name__)
dummy_project_config = BaseProjectConfig(
    UniversalConfig(),
    config={"project": {"package": "packageA"}},
)
dummy_org_config = OrgConfig({}, "dummy_config")


class DelaySpawner:
    def __init__(self, target, args, daemon):
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

    def terminate(self):
        self._is_alive = False


class TestWorkerQueue:
    @contextmanager
    def configure_worker_queue(self, parent_dir, **kwargs):
        config = WorkerQueueConfig(
            project_config=dummy_project_config,
            org_config=dummy_org_config,
            connected_app=None,
            redirect_logging=True,
            spawn_class=DelaySpawner,
            parent_dir=Path(parent_dir),
            **kwargs,
        )
        q = WorkerQueue(config, filesystem_lock=Lock())

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
            assert q.empty
            assert q.num_free_workers == 2
            assert q.queued_job_dirs == []
            q.push(name="a")
            assert not q.empty
            assert not q.full
            assert q.num_free_workers == 1
            assert len(q.queued_job_dirs) == 0
            q.tick()
            assert not q.full
            assert q.num_free_workers == 1
            assert len(q.queued_job_dirs) == 0
            q.workers[0].process._finish()
            q.tick()
            assert not q.full
            assert q.num_free_workers == 2
            assert len(q.queued_job_dirs) == 0
            q.tick()
            assert not q.full
            assert q.num_free_workers == 2
            assert len(q.queued_job_dirs) == 0
            q.push(name="bb")
            q.tick()
            assert not q.full
            assert q.num_free_workers == 1
            assert len(q.queued_job_dirs) == 0
            q.push(name="cc")
            q.tick()
            assert not q.full
            assert q.num_free_workers == 0
            assert len(q.queued_job_dirs) == 0
            q.push(name="dd")
            q.tick()
            assert not q.full
            assert q.num_free_workers == 0
            assert len(q.queued_job_dirs) == 1
            q.push(name="ee")
            q.tick()
            assert not q.full
            assert q.num_free_workers == 0
            assert len(q.queued_job_dirs) == 2
            q.push(name="ff")
            q.tick()
            assert q.full
            assert q.num_free_workers == 0
            assert len(q.queued_job_dirs) == 3

            with pytest.raises(ValueError):
                q.push(name="hh")

            assert q.full
            assert q.num_free_workers == 0
            assert len(q.queued_job_dirs) == 3

            for worker in q.workers:
                worker.process._finish()

            q.tick()

            assert not q.full
            assert q.num_free_workers == 0
            assert len(q.queued_job_dirs) == 1

            for worker in q.workers:
                worker.process._finish()

            q.tick()

            assert not q.full
            assert q.num_free_workers == 1
            assert len(q.queued_job_dirs) == 0

            for worker in q.workers:
                worker.process._finish()

            q.tick()

            assert not q.full
            assert q.num_free_workers == 2
            assert len(q.queued_job_dirs) == 0

            q.push(name="ii")
            q.push(name="jj")
            q.push(name="kk")
            q.push(name="ll")
            q.push(name="mm")
            with pytest.raises(ValueError):
                q.push(name="nn")

            q.tick()

            assert q.full
            assert q.num_free_workers == 0
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
            q1.feeds_data_to(q2)
            q1.push(name="a")
            assert not q1.full
            assert q1.num_free_workers == 1
            assert len(q1.queued_job_dirs) == 0
            q1.tick()
            q1.tick()
            assert not q1.full
            assert q1.num_free_workers == 1
            assert len(q1.queued_job_dirs) == 0

            for worker in q1.workers:
                worker.process._finish()
            q1.tick()
            q2.tick()
            assert not q2.full
            assert q1.num_free_workers == 2
            assert q2.num_free_workers == 1
            assert len(q2.queued_job_dirs) == 0

            q1.push(name="b")
            q1.push(name="c")
            q1.push(name="d")
            q1.push(name="e")

            for worker in q1.workers:
                worker.process._finish()
            q1.tick()
            q2.tick()

    def test_worker_queues_together__outbox_cannot_be_removed(self, tmpdir):
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
            q1.outbox_dir.rmdir()
            with mock.patch(
                "cumulusci.utils.parallel.task_worker_queues.parallel_worker_queue.logger.info"
            ) as logger_info:
                q1.feeds_data_to(q2)
                assert "Cannot remove outbox dir" in logger_info.mock_calls[0][1][0]

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
            q1.feeds_data_to(q2)
            foo = tmpdir / "foo"
            foo.mkdir()
            assert not q1.full
            assert q1.num_free_workers == 2
            assert q1.queued_job_dirs == []
            q1.push(Path(foo))
            assert not q1.full
            assert q1.num_free_workers == 1
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


class TestParallelWorker:
    def test_terminate_parallel_worker(self):
        with TemporaryDirectory() as failures_dir, TemporaryDirectory() as outbox_dir, TemporaryDirectory() as working_dir:
            config = WorkerConfig(
                project_config=dummy_project_config,
                org_config=dummy_org_config,
                connected_app=None,
                redirect_logging=True,
                task_class=Sleep,
                task_options={"seconds": 0},
                failures_dir=failures_dir,
                outbox_dir=outbox_dir,
                working_dir=working_dir,
            )
            worker = ParallelWorker(DelaySpawner, config, None, Lock())
            worker.start()
            worker.terminate()
            assert "Alive: False" in repr(worker)


class TestTaskWorker:
    def test_worker__cannot_move_to_outdir(self):
        with TemporaryDirectory() as failures_dir, TemporaryDirectory() as outbox_dir, TemporaryDirectory() as working_dir:
            config = WorkerConfig(
                project_config=dummy_project_config,
                org_config=dummy_org_config,
                connected_app=None,
                redirect_logging=True,
                task_class=Sleep,
                task_options={"seconds": 0},
                failures_dir=failures_dir,
                outbox_dir=outbox_dir,
                working_dir=working_dir,
            )
            p = TaskWorker(config.as_dict(), None, Lock())
            with mock.patch("shutil.move", side_effect=AssertionError):
                with pytest.raises(AssertionError):
                    p.run()
            assert Path(working_dir, "exception.txt").exists()


# Frankly these tests are primarily for coverage-counting purposes.
# Meaningful tests of keychain stuff are by definition integration
# tests, and we only use connected apps for persistent orgs, which
# makes this even more messy.

# Also we usually mock refresh_oauth_token which is what would
# invoke this. In other words, using integration tests to cover this
# function is far easier than using unit test.
class TestSubprocessKeychain:
    def test_subprocess_keychain(self):
        skc = SubprocessKeychain("Blah")

        assert skc.get_service("connected_app") == "Blah"
        skc.set_org()
        with pytest.raises(exc.ServiceNotConfigured):
            skc.get_service("xyzzy")
