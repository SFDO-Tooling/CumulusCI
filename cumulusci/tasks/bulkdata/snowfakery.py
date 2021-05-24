import time
import shutil
from datetime import timedelta
from cumulusci.core.utils import format_duration
import cumulusci.core.exceptions as exc
import typing as T

from pathlib import Path  # test this on Windows
from tempfile import mkdtemp
from contextlib import contextmanager
from dataclasses import dataclass
import threading

from sqlalchemy import MetaData, create_engine

from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.tasks.bulkdata.generate_and_load_data_from_yaml import (
    GenerateAndLoadDataFromYaml,
)
from cumulusci.core.config import TaskConfig

from cumulusci.tasks.bulkdata.load import LoadData
from cumulusci.tasks.bulkdata.generate_from_yaml import GenerateDataFromYaml

from .parallel_worker_queue import WorkerQueueConfig, WorkerQueue


BASE_BATCH_SIZE = 500  # FIXME
ERROR_THRESHOLD = 3  # FIXME


def clip(value, min_=None, max_=None):
    if min_ is not None:
        value = max(value, min_)
    if max_ is not None:
        value = min(value, max_)
    return value


def generate_batches(target: int, min_batch_size, max_batch_size):
    count = 0
    batch_size = min_batch_size
    max_batch_size = min(max_batch_size, int(target // 20))
    while count < target:
        batch_size = int(min(batch_size * 1.1, max_batch_size, target - count))
        count += batch_size
        yield batch_size, count


class OrgRecordCounts(threading.Thread):
    # Getting record count can be slow in big orgs
    main_sobject_count = 0
    other_inaccurate_record_counts = {}

    # TODO: is self.sf mutable? I should probably get a copy of it instead.
    def __init__(self, options, sf):
        self.options = options
        self.sf = sf
        super().__init__(daemon=True)

    # TODO: WHAT if main_sobject_count can't be retrieved?
    #       Should get it from other_inaccurate_record_counts
    #       If both fail we'll have a problem. :(
    def run(self):
        while 1:
            print("BEFORE")
            self.main_sobject_count = self.get_org_record_count_for_sobject()
            print("MIDDLE")
            self.other_inaccurate_record_counts = self.get_org_record_counts()
            print("AFTER")
            time.sleep(17)

    def get_org_record_count_for_sobject(self):
        "This lags quite a bit behind the real numbers."
        sobject = self.options.get("num_records_tablename")
        query = f"select count(Id) from {sobject}"
        count = self.sf.query(query)["records"][0]["expr0"]
        return int(count)

    def get_org_record_counts(self):
        data = self.sf.restful("limits/recordCount")
        blockwords = ["Permission", "History", "ListView", "Feed", "Setup", "Event"]
        rc = {
            sobject["name"]: sobject["count"]
            for sobject in data["sObjects"]
            if sobject["count"] > 100
            and not any(blockword in sobject["name"] for blockword in blockwords)
        }
        total = sum(rc.values())
        rc["TOTAL"] = total
        return rc


@dataclass()
class UploadStatus:
    confirmed_count_in_org: int
    batch_size: int
    sets_being_generated: int
    sets_queued: int
    sets_being_loaded: int
    sets_finished: int
    target_count: int
    base_batch_size: int
    upload_queue_free_space: int
    user_max_num_uploader_workers: int
    user_max_num_generator_workers: int
    max_batch_size: int
    elapsed_seconds: int
    sets_failed: int
    inprogress_generator_jobs: int
    inprogress_loader_jobs: int
    queue_full: int
    data_gen_free_workers: int

    @property
    def max_needed_generators_to_fill_queue(self):
        return max(
            self.user_max_num_generator_workers,
            self.upload_queue_free_space - self.sets_being_generated,
        )

    @property
    def total_needed_generators(self):
        if self.done:
            return 0
        else:
            return 4

    @property
    def total_in_flight(self):
        return self.sets_being_generated + self.sets_queued + self.sets_being_loaded

    @property
    def done(self):
        return self.confirmed_count_in_org >= self.target_count

    def _display(self, detailed=False):
        most_important_stats = [
            "target_count",
            "confirmed_count_in_org",
            "sets_finished",
            "sets_being_generated",
            "sets_queued",
            "sets_being_loaded",
            "sets_failed",
        ]

        queue_stats = [
            "inprogress_generator_jobs",
            "upload_queue_free_space",
            "inprogress_loader_jobs",
        ]

        def format(val: object) -> str:
            if isinstance(val, int):
                return f"{val:,}"
            else:
                return str(val)

        def display_stats(keys):
            return (
                "\n"
                + "\n".join(
                    f"{a.replace('_', ' ').title()}: {format(getattr(self, a))}"
                    for a in keys
                    if not a[0] == "_"
                )
                + "\n"
            )

        rc = "**** Progress ****\n"
        rc += display_stats(most_important_stats)
        if detailed:
            rc += "\n   ** Queues **\n"
            rc += display_stats(queue_stats)
            rc += "\n   ** Internals **\n"
            rc += display_stats(
                set(dir(self)) - (set(most_important_stats) & set(queue_stats))
            )
        return rc


class Snowfakery(BaseSalesforceApiTask):
    """ """

    task_docs = """
    """
    task_options = {
        "recipe": {"required": True},
        "num_generator_workers": {},
        "num_uploader_workers": {},
        "loading_rules": {},  # TODO: Impl, Docs
        "working_directory": {},  # TODO: Impl, Docs
        "recipe_options": {},  # TODO: Impl, Docs
        "num_records": {},  # TODO: Docs
        "num_records_tablename": {},  # TODO : Better name
        "max_batch_size": {},  # TODO Impl, Docs
        "unified_logging": {},  # TODO RETHINK
        "subtask_type": {},  # TODO: RETHINK
        "infinite_buffer": {},  # ONLY FOR BENCHMARKS
    }

    def _validate_options(self):
        super()._validate_options()
        # long-term solution: psutil.cpu_count(logical=False)
        self.num_generator_workers = int(self.options.get("num_generator_workers", 4))
        self.num_uploader_workers = int(self.options.get("num_uploader_workers", 15))
        # Do not store recipe due to MetaDeploy options freezing
        recipe = Path(self.options.get("recipe"))
        assert recipe.exists()
        assert isinstance(self.options.get("num_records_tablename"), str)
        self.num_records_tablename = self.options.get("num_records_tablename")
        self.num_records = int(self.options.get("num_records"))
        self.unified_logging = self.options.get("unified_logging")
        subtask_type_name = (self.options.get("subtask_type") or "process").lower()

        if subtask_type_name == "thread":
            self.subtask_type = WorkerQueue.Thread
            self.logger.info("Snowfakery is using threads")
        elif subtask_type_name == "process":
            self.subtask_type = WorkerQueue.Process
        else:
            raise exc.TaskOptionsError(f"No task type named {subtask_type_name}")

        self.infinite_buffer = self.options.get("infinite_buffer")

    def _run_task(self):
        self.start_time = time.time()
        self.max_batch_size = self.options.get("max_batch_size", 250_000)
        self.recipe = Path(self.options.get("recipe"))
        self.job_counter = 0
        org_record_counts_thread = OrgRecordCounts(self.options, self.sf)
        org_record_counts_thread.start()

        working_directory = self.options.get("working_directory")
        if working_directory:
            working_directory = Path(working_directory)
        with self._generate_and_load_initial_batch(working_directory) as (
            tempdir,
            template_path,
        ):
            self.logger.info(f"Working directory is {tempdir}")
            # os.system(f"code {tempdir}")  # FIXME
            assert tempdir.exists()

            try:
                connected_app = self.project_config.keychain.get_service(
                    "connected_app"
                )
            except exc.ServiceNotConfigured:
                connected_app = None

            config = WorkerQueueConfig(
                project_config=self.project_config,
                org_config=self.org_config,
                connected_app=connected_app,
                redirect_logging=True,
                spawn_class=self.subtask_type,
                parent_dir=tempdir,
                name="data_gen",
                task_class=GenerateDataFromYaml,
                make_task_options=self.data_generator_opts,
                queue_size=1,
                num_workers=4,
            )
            data_gen_q = WorkerQueue(config)

            config = WorkerQueueConfig(
                project_config=self.project_config,
                org_config=self.org_config,
                connected_app=connected_app,
                redirect_logging=True,
                spawn_class=self.subtask_type,
                parent_dir=tempdir,
                name="data_load",
                task_class=LoadData,
                make_task_options=self.data_loader_opts,
                queue_size=15,
                num_workers=15,
            )
            load_data_q = WorkerQueue(config)

            data_gen_q.feeds(load_data_q)

            print("Working directory", tempdir)

            upload_status = self._loop(
                template_path,
                tempdir,
                data_gen_q,
                load_data_q,
                org_record_counts_thread,
            )

            data_gen_q.terminate_all()

            # TODO: clean up data generators so they don't keep pushing things to
            #       the loaders
            while load_data_q.workers:
                plural = "" if len(load_data_q.workers) == 1 else "s"
                self.logger.info(
                    f"Waiting for {len(load_data_q.workers)} worker{plural} to finish"
                )
                load_data_q.tick()
                time.sleep(2)

            elapsed = format_duration(timedelta(seconds=time.time() - self.start_time))

            upload_status = self._report_status(
                data_gen_q, load_data_q, 0, org_record_counts_thread
            )
            for (
                char
            ) in f"☃  D ❄ O ❆ N ❉ E ☃     :  {elapsed}, {upload_status.confirmed_count_in_org:,} sets":
                print(char, end="", flush=True)
                time.sleep(0.10)
            print()

    def _loop(
        self, template_path, tempdir, data_gen_q, load_data_q, org_record_counts_thread
    ):
        batch_size = BASE_BATCH_SIZE

        record_count = False

        while org_record_counts_thread.is_alive() and not record_count:
            self.logger.info("Waiting for org record report")
            record_count = org_record_counts_thread.main_sobject_count
            time.sleep(1)

        goal_records = self.num_records - record_count

        self.logger.info(f"Org has {record_count:,}. Generating {goal_records:,}.")

        batches = generate_batches(goal_records, BASE_BATCH_SIZE, self.max_batch_size)
        for i in range(10 ** 10):
            upload_status = self._report_status(
                data_gen_q, load_data_q, batch_size, org_record_counts_thread
            )
            self.logger.info(f"Working Directory: {tempdir}")

            if upload_status.done:
                break

            data_gen_q.tick()

            batch_size = self.tick(
                upload_status, data_gen_q, batches, template_path, tempdir, batch_size
            )

            time.sleep(3)
        return upload_status

    def _report_status(
        self, data_gen_q, load_data_q, batch_size, org_record_counts_thread
    ):
        self.logger.info(
            "\n********** PROGRESS *********",
        )

        upload_status = self.generate_upload_status(
            data_gen_q, load_data_q, batch_size, org_record_counts_thread
        )

        self.logger.info(upload_status._display(detailed=True))

        if upload_status.sets_failed:
            self.log_failures()

        if upload_status.sets_failed > ERROR_THRESHOLD:
            breakpoint()
            raise exc.BulkDataException(
                f"Errors exceeded threshold: `{upload_status.sets_failed}` vs `{ERROR_THRESHOLD}`"
            )

        for (
            k,
            v,
        ) in org_record_counts_thread.other_inaccurate_record_counts.items():
            self.logger.info(f"      COUNT: {k}: {v:,}")

        return upload_status

    def tick(
        self, upload_status, data_gen_q, batches, template_path, tempdir, batch_size
    ):
        if (
            upload_status.max_needed_generators_to_fill_queue == 0
            and not self.infinite_buffer
        ):
            self.logger.info("WAITING FOR UPLOAD QUEUE TO CATCH UP")
        elif data_gen_q.full:
            self.logger.info("DATA GEN QUEUE IS FULL")
        elif data_gen_q.free_workers <= 0:
            self.logger.info("NO FREE DATA GEN QUEUE WORKERS")
        else:
            for i in range(data_gen_q.free_workers):
                self.job_counter += 1
                batch_size, total = next(batches, (None, None))
                if not batch_size:
                    self.logger.info(
                        "All scheduled batches generated and being uploaded"
                    )
                    break
                job_dir = self.generator_data_dir(
                    self.job_counter, template_path, batch_size, tempdir
                )
                data_gen_q.push(job_dir)
        return batch_size

    def log_failures(self):
        return
        # FIXME!!!!
        failures = self.failures_dir.glob("*/exception.txt")
        for failure in failures:
            text = failure.read_text()
            self.logger.info(f"Failure from worker: {failure}")
            self.logger.info(text)

    def data_loader_opts(self, working_dir: Path):
        mapping_file = working_dir / "temp_mapping.yml"
        database_file = working_dir / "generated_data.db"
        assert mapping_file.exists(), mapping_file
        assert database_file.exists(), database_file
        database_url = f"sqlite:///{database_file}"

        options = {
            "mapping": mapping_file,
            "reset_oids": False,
            "database_url": database_url,
        }
        return options

    def generator_data_dir(self, idx, template_path, batch_size, parent_dir):
        data_dir = parent_dir / (str(idx) + "_" + str(batch_size))
        shutil.copytree(template_path, data_dir)
        return data_dir

    def data_generator_opts(self, working_dir, *args, **kwargs):
        name = Path(working_dir).name
        parts = name.rsplit("_", 1)
        batch_size = int(parts[-1])
        assert working_dir.exists()
        database_file = working_dir / "generated_data.db"
        assert database_file.exists()
        assert isinstance(batch_size, int)
        mapping_file = working_dir / "temp_mapping.yml"
        assert mapping_file.exists()

        return {
            "generator_yaml": str(self.recipe),
            "database_url": f"sqlite:///{database_file}",
            "num_records": batch_size,
            "reset_oids": False,
            "continuation_file": f"{working_dir}/continuation.yml",
            "num_records_tablename": self.num_records_tablename,
        }

    def _invoke_subtask(
        self,
        task_class: type,
        subtask_options: T.Mapping[str, T.Any],
        working_dir: Path,
        redirect_logging: bool,
    ):
        subtask_config = TaskConfig({"options": subtask_options})
        subtask = task_class(
            project_config=self.project_config,
            task_config=subtask_config,
            org_config=self.org_config,
            flow=self.flow,
            name=self.name,
            stepnum=self.stepnum,
        )
        subtask()

    def sets_in_dir(self, dir):
        idx_and_counts = (subdir.name.split("_") for subdir in dir.glob("*_*"))
        return sum(int(count) for (idx, count) in idx_and_counts)

    def generate_upload_status(
        self, generator_q, loader_q, batch_size, org_record_counts_thread
    ):
        def set_count_from_names(names):
            return sum(int(name.split("_")[1]) for name in names)

        for worker in generator_q.workers:
            print(worker)

        rc = UploadStatus(
            confirmed_count_in_org=org_record_counts_thread.main_sobject_count,
            target_count=self.num_records,
            sets_being_generated=set_count_from_names(generator_q.inprogress_jobs)
            + set_count_from_names(generator_q.queued_jobs),
            sets_queued=set_count_from_names(loader_q.queued_jobs),
            # note that these may count as already imported in the org
            sets_being_loaded=set_count_from_names(loader_q.inprogress_jobs),
            upload_queue_free_space=loader_q.free_space,
            # TODO
            sets_finished=set_count_from_names(loader_q.outbox_jobs),
            base_batch_size=BASE_BATCH_SIZE,  # FIXME
            user_max_num_uploader_workers=self.num_uploader_workers,
            user_max_num_generator_workers=self.num_generator_workers,
            max_batch_size=self.max_batch_size,
            elapsed_seconds=int(time.time() - self.start_time),
            # TODO
            sets_failed=len(loader_q.failed_jobs),
            batch_size=batch_size,
            inprogress_generator_jobs=len(generator_q.inprogress_jobs),
            inprogress_loader_jobs=len(loader_q.inprogress_jobs),
            queue_full=generator_q.full,
            data_gen_free_workers=generator_q.free_workers,
        )
        return rc

    @contextmanager
    def workingdir_or_tempdir(self, working_directory: T.Optional[Path]):
        if working_directory:
            working_directory.mkdir()
            self.logger.info(f"Working Directory {working_directory}")
            yield working_directory
        else:
            # with TemporaryDirectory() as tempdir:
            # yield tempdir

            # do not clean up tempdirs for now
            tempdir = mkdtemp()
            self.logger.info(f"Working Directory {tempdir}")
            yield tempdir

    @contextmanager
    def _generate_and_load_initial_batch(
        self, working_directory: T.Optional[Path]
    ) -> Path:
        with self.workingdir_or_tempdir(working_directory) as tempdir:
            template_dir = Path(tempdir) / "template"
            template_dir.mkdir()
            self._generate_and_load_batch(
                template_dir, {"generator_yaml": self.options.get("recipe")}
            )

            yield Path(tempdir), template_dir

    def _generate_and_load_batch(self, tempdir, options) -> Path:
        options = {**options, "working_directory": tempdir}
        self._invoke_subtask(GenerateAndLoadDataFromYaml, options, tempdir, False)
        generated_data = tempdir / "generated_data.db"
        assert generated_data.exists(), generated_data
        database_url = f"sqlite:///{generated_data}"
        self._cleanup_object_tables(*self._setup_engine(database_url))

    def _setup_engine(self, database_url):
        """Set up the database engine"""
        engine = create_engine(database_url)

        metadata = MetaData(engine)
        metadata.reflect()
        return engine, metadata

    def _cleanup_object_tables(self, engine, metadata):
        """Delete all tables that do not relate to id->OID mapping"""
        tables = metadata.tables
        tables_to_drop = [
            table
            for tablename, table in tables.items()
            if not tablename.endswith("sf_ids")
        ]
        if tables_to_drop:
            metadata.drop_all(tables=tables_to_drop)


def test():
    u = UploadStatus(
        base_batch_size=5000,
        confirmed_count_in_org=20000,
        sets_being_generated=5000,
        sets_being_loaded=20000,
        sets_queued=0,
        target_count=30000,
        upload_queue_backlog=1,
        user_max_num_generator_workers=4,
        user_max_num_uploader_workers=15,
    )
    assert u.total_needed_generators == 1, u.total_needed_generators

    u = UploadStatus(
        base_batch_size=5000,
        confirmed_count_in_org=0,
        sets_being_generated=5000,
        sets_being_loaded=20000,
        sets_queued=0,
        target_count=30000,
        upload_queue_backlog=1,
        user_max_num_generator_workers=4,
        user_max_num_uploader_workers=15,
    )
    assert u.total_needed_generators == 1, u.total_needed_generators

    u = UploadStatus(
        base_batch_size=5000,
        confirmed_count_in_org=0,
        sets_being_generated=5000,
        sets_being_loaded=15000,
        sets_queued=0,
        target_count=30000,
        upload_queue_backlog=1,
        user_max_num_generator_workers=4,
        user_max_num_uploader_workers=15,
    )
    assert u.total_needed_generators == 2, u.total_needed_generators

    u = UploadStatus(
        base_batch_size=5000,
        confirmed_count_in_org=29000,
        sets_being_generated=0,
        sets_being_loaded=0,
        sets_queued=0,
        target_count=30000,
        upload_queue_backlog=0,
        user_max_num_generator_workers=4,
        user_max_num_uploader_workers=15,
    )
    assert u.total_needed_generators == 1, u.total_needed_generators

    u = UploadStatus(
        base_batch_size=5000,
        confirmed_count_in_org=4603,
        sets_being_generated=5000,
        sets_being_loaded=20000,
        sets_queued=0,
        target_count=30000,
        upload_queue_backlog=0,
        user_max_num_generator_workers=4,
        user_max_num_uploader_workers=15,
    )
    assert u.total_needed_generators == 1, u.total_needed_generators

    # TODO: In a situation like this, it is sometimes the case
    #       that there are not enough records generated to upload.
    #
    #       Due to internal striping, the confirmed_count_in_org
    #       could be correct and yet the org pauses while uploading
    #       other sobjects for several minutes.
    #
    #       Need to get rid of the assumption that every record
    #       that is created must be uploaded and instead make a
    #       backlog that can be either uploaded or discarded.

    #       Perhaps the upload queue should always be full and
    #       throttling should always happen in the uploaders, not
    #       the generators.
    u = UploadStatus(
        base_batch_size=500,
        confirmed_count_in_org=39800,
        sets_being_generated=0,
        sets_being_loaded=5000,
        sets_queued=0,
        target_count=30000,
        upload_queue_backlog=0,
        user_max_num_generator_workers=4,
        user_max_num_uploader_workers=15,
    )
    assert u.total_needed_generators == 1, u.total_needed_generators


if __name__ == "__main__":
    test()


## IDEA:
#
# --finish_when "Accounts in org=10_000"
# --finish_when "Accounts uploaded=10_000"#
# --finish_when "Copies=10_000"
#
