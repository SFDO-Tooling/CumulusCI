import time
import shutil
from datetime import timedelta
import typing as T

from pathlib import Path
from tempfile import mkdtemp
from contextlib import contextmanager

from sqlalchemy import MetaData, create_engine

from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.tasks.bulkdata.generate_and_load_data_from_yaml import (
    GenerateAndLoadDataFromYaml,
)
from cumulusci.core.config import TaskConfig

from cumulusci.tasks.bulkdata.load import LoadData
from cumulusci.tasks.bulkdata.generate_from_yaml import GenerateDataFromYaml
from cumulusci.core.utils import format_duration, process_bool_arg
import cumulusci.core.exceptions as exc
from cumulusci.utils.salesforce.record_count import OrgRecordCounts
from cumulusci.utils._math import clip

from cumulusci.utils.parallel.task_worker_queues.parallel_worker_queue import (
    WorkerQueueConfig,
    WorkerQueue,
)


BASE_BATCH_SIZE = 500  # FIXME
ERROR_THRESHOLD = 0  # TODO: Allow this to be a percentage of recent records instead


def generate_batches(target: int, min_batch_size, max_batch_size):
    """Generate enough batches to fulfill a target count.

    Batch size starts at min_batch_size and grows toward max_batch_size
    unless the count gets there first.py

    The reason we grow is to try to engage the org's loader queue earlier
    than we would if we waited for the first big batch to be available.
    """
    count = 0
    batch_size = min_batch_size
    while count < target:
        remaining = target - count
        batch_size = int(batch_size * 1.1)  # batch size grows over time
        batch_size = min(batch_size, remaining, max_batch_size)

        count += batch_size
        yield batch_size, count


class Snowfakery(BaseSalesforceApiTask):

    task_docs = """Do a data load with Snowfakery."""

    task_options = {
        "recipe": {
            "required": True,
            "description": "A Snowfakery recipe file determining what data to generate and load.",
        },
        "run-until-records-in-org": {
            "description": """<sobject>,<count>

      Run the recipe repeatedly until the count of <sobject>
      in the org matches the given <count>.

      For example, `--run-until-records-in-org Account,50_000` means:

      Count the Account records in the org. Let’s say the number
      is 20,000. Thus, we must run the recipe over and
      over again until we generate 30,000 new Account records.
      If the recipe also generates e.g.Contacts, Opportunities or whatever
      else, it generates the appropriate number of them to match.

      Underscores are allowed but optional in big numbers: 2000000
      is the same as 2_000_000.
        """
        },
        "run-until-records-loaded": {
            "description": """<sobject>,<count>

      Run the recipe repeatedly until the number of records of
      <sobject> uploaded in this task execution matches <count>.

      For example, `--run-until-records-loaded Account,50_000` means:

      Run the recipe over and over again
      until we generate 50_000 new Account records. If the recipe
      also generates e.g. Contacts, Opportunities or whatever else, it
      generates the appropriate number of them to match.
        """
        },
        "run-until-recipe-repeated": {
            "description": "(coming soon) Run the recipe <count> times, "
            "no matter what data is already in the org."
        },
        "working_directory": {
            "description": "Default path for temporary / working files"
        },
        "loading_rules": {
            "description": "Path to .load.yml file containing rules to use to "
            "load the file. Defaults to `<recipename>.load.yml`. "
            "Multiple files can be comma separated."
        },
        # "recipe_options": {},  # TODO: Snowfakery 2.1
        "bulk_mode": {
            "description": "Set to Serial to force serial mode on all jobs. Parallel is the default."
        },
        "drop_missing_schema": {
            "description": "Set to True to skip any missing objects or fields instead of stopping with an error."
        },
        "num_processes": {
            "description": "Number of data generating processes. Defaults to 1 for small loads "
            "(<20,000 records or reps) and 4 for larger loads"
        },
    }

    def _validate_options(self):
        super()._validate_options()
        # Do not store recipe due to MetaDeploy options freezing
        recipe = self.options.get("recipe")
        if not recipe:
            raise exc.TaskOptionsError("No recipe specified")
        recipe = Path(recipe)
        if not recipe.exists():
            raise exc.TaskOptionsError(f"Cannot find recipe `{recipe}`")

        # long-term solution: psutil.cpu_count(logical=False)
        self.num_generator_workers = int(self.options.get("num_processes", None))

        self.stopping_critera = self.determine_stopping_criteria()

        self.num_records_tablename = self.options.get("num_records_tablename")
        if not isinstance(self.options.get("num_records_tablename"), (str, type(None))):
            raise exc.TaskOptionsError("num_records_tablename should be a string")
        num_records = self.options.get("num_records")

        self.num_records = int(num_records) if num_records is not None else None
        self.unified_logging = process_bool_arg(self.options.get("unified_logging"))
        subtask_type_name = self.options.get("subtask_type") or "process"
        if subtask_type_name.lower() not in ("process", "thread"):
            raise exc.TaskOptionsError("subtask_type should be 'process' or 'thread'")

        if subtask_type_name.lower() == "thread":
            self.subtask_type = WorkerQueue.Thread
            self.logger.info("Snowfakery is using threads")
        elif subtask_type_name.lower() == "process":
            self.subtask_type = WorkerQueue.Process

    def stopping_criteria(self):
        load_strategies = (
            "run-until-recipe-repeated",
            "run-until-records-in-org",
            "run-until-records-loaded",
        )

        selected_strategies = [
            (strategy, self.options.get(strategy))
            for strategy in load_strategies
            if self.options.get(strategy)
        ]

        if len(selected_strategies) > 1:
            raise exc.TaskOptionsError(
                "Please select only one of " + ", ".join(load_strategies)
            )
        elif not selected_strategies:
            load_strategy = ("run-until-recipe-repeated", "1")
        else:
            load_strategy = selected_strategies[0]

        strategy_name, param = load_strategy

        return COUNT_STRATEGIES[strategy_name](param)

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
            raise exc.BulkDataException(
                f"Errors exceeded threshold: {upload_status.sets_failed} vs {ERROR_THRESHOLD}"
            )

        for k, v in org_record_counts_thread.other_inaccurate_record_counts.items():
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
        # Todo, V2.1: Log the failures better
        # failures = self.failures_dir.glob("*/exception.txt")
        # for failure in failures:
        #     text = failure.read_text()
        #     self.logger.info(f"Failure from worker: {failure}")
        #     self.logger.info(text)

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

        # don't send data tables to child processes. All they
        # care about are ID->OID mappings
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


class UploadStatus(T.NamedTuple):
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


class RunUntilRecipeRepeated:
    def __init__(self, param):
        try:
            self.count = int(param)
        except TypeError:
            raise exc.TaskOptionsError(f"{param} is not a number")
        # raise NotImplementedError("--run-until-recipe-repeated is not implemented yet")

    def calculate_target(self, sf):
        from snowfakery.api import COUNT_REPS

        return (COUNT_REPS, self.count)


class RunUntilRecordsLoaded:
    option_name = "--run-until-records-loaded"

    def __init__(self, param):
        self.sobject_name, num = param.split(",")
        try:
            self.count = int(num)
        except TypeError:
            raise exc.TaskOptionsError(f"{param} is not a number in {self.option_name}")

    def calculate_target(self, sf):
        return (self.sobject_name, self.count)


class RunUntilRecordInOrg(RunUntilRecordsLoaded):
    option_name = "--run-until-records-in-org"

    def calculate_target(self, sf):
        query = f"select count(Id) from {self.sobject_name}"
        in_org_count = self.sf.query(query)["records"][0]["expr0"]
        target = self.count - int(in_org_count)
        count = clip(target, min=0)
        return (self.sobject_name, count)


COUNT_STRATEGIES = {
    "run-until-recipe-repeated": RunUntilRecipeRepeated,
    "run-until-records-loaded": RunUntilRecordsLoaded,
    "run-until-records-in-org": RunUntilRecordInOrg,
}
