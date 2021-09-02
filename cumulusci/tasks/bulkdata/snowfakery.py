import shutil
import time
import typing as T
from collections import defaultdict
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from queue import Empty
from tempfile import TemporaryDirectory, mkdtemp

import psutil
import yaml
from snowfakery.api import COUNT_REPS
from sqlalchemy import MetaData, Table, create_engine, func, select

import cumulusci.core.exceptions as exc
from cumulusci.core.config import TaskConfig
from cumulusci.core.debug import get_debug_mode
from cumulusci.core.utils import format_duration, process_bool_arg
from cumulusci.tasks.bulkdata.generate_and_load_data_from_yaml import (
    GenerateAndLoadDataFromYaml,
)
from cumulusci.tasks.bulkdata.generate_from_yaml import GenerateDataFromYaml
from cumulusci.tasks.bulkdata.load import LoadData
from cumulusci.tasks.bulkdata.snowfakery_utils.snowfakery_run_until import (
    PortionGenerator,
    determine_run_until,
)
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.utils.parallel.task_worker_queues.parallel_worker_queue import (
    WorkerQueue,
    WorkerQueueConfig,
)

# A portion serves the same process in this system as a "batch" in
# other systems. The term "batch" is not used to avoid confusion with
# Salesforce Bulk API 1.0 batches. For example, a portion of 250_000
# Account records would be broken into roughly 25 Salesforce upload
# batches.

# The system starts at the MIN_PORTION_SIZE and grows towards the
# MAX_PORTION_SIZE. This is to prevent the org wasting time waiting
# for the first portions.
MIN_PORTION_SIZE = 2_000
MAX_PORTION_SIZE = 250_000
ERROR_THRESHOLD = (
    0  # TODO v2.1: Allow this to be a percentage of recent records instead
)

# time between "ticks" where the task re-evaluates its progress
# relatively arbitrary trade-off between busy-waiting and adding latency.
WAIT_TIME = 3

# more loader workers than generators because they spend so much time
# waiting for responses. 4:1 is an experimentally derived ratio
WORKER_TO_LOADER_RATIO = 4

# number of portions we will allow to be on-disk waiting to be loaded
# higher numbers use more disk space.
LOAD_QUEUE_SIZE = 15


class Snowfakery(BaseSalesforceApiTask):

    task_docs = """
    Do a data load with Snowfakery.

    All options are optional.

    The most commonly supplied options are `recipe` and one of the three
    `run_until_...` options.
    """

    task_options = {
        "recipe": {
            "required": True,
            "description": "Path to a Snowfakery recipe file determining what data to generate and load.",
        },
        "run_until_records_in_org": {
            "description": """<sobject>:<count>

      Run the recipe repeatedly until the count of <sobject>
      in the org matches the given <count>.

      For example, `--run_until_records_in_org Account:50_000` means:

      Count the Account records in the org. Let’s say the number
      is 20,000. Thus, we must run the recipe over and
      over again until we generate 30,000 new Account records.
      If the recipe also generates e.g.Contacts, Opportunities or whatever
      else, it generates the appropriate number of them to match.

      Underscores are allowed but optional in big numbers: 2000000
      is the same as 2_000_000.
        """
        },
        "run_until_records_loaded": {
            "description": """<sobject>:<count>

      Run the recipe repeatedly until the number of records of
      <sobject> uploaded in this task execution matches <count>.

      For example, `--run_until_records_loaded Account:50_000` means:

      Run the recipe over and over again
      until we generate 50_000 new Account records. If the recipe
      also generates e.g. Contacts, Opportunities or whatever else, it
      generates the appropriate number of them to match.
        """
        },
        "run_until_recipe_repeated": {
            "description": """Run the recipe <count> times,
            no matter what data is already in the org.

            For example, `--run_until_recipe_repeated 50_000` means
            run the recipe 50_000 times."""
        },
        "working_directory": {"description": "Path for temporary / working files"},
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
            "description": "Number of data generating processes. Defaults to matching the number of CPUs."
        },
        "ignore_row_errors": {
            "description": "Boolean: should we continue loading even after running into row errors? "
            "Defaults to False."
        },
    }

    def _validate_options(self):
        super()._validate_options()
        # Do not store recipe due to MetaDeploy options freezing
        recipe = self.options.get("recipe")
        recipe = Path(recipe)
        if not recipe.exists():
            raise exc.TaskOptionsError(f"Cannot find recipe `{recipe}`")

        self.num_generator_workers = self.options.get("num_processes", None)
        if self.num_generator_workers is not None:
            self.num_generator_workers = int(self.num_generator_workers)
        self.ignore_row_errors = process_bool_arg(
            self.options.get("ignore_row_errors", False)
        )

    @property
    def num_loader_workers(self):
        return self.num_generator_workers * WORKER_TO_LOADER_RATIO

    def setup(self):
        self.debug_mode = get_debug_mode()
        if not self.num_generator_workers:
            # logical CPUs do not really improve performance of CPU-bound
            # code, so we ignore them.
            self.num_generator_workers = psutil.cpu_count(logical=False)
            if self.debug_mode:
                self.logger.info(f"Using {self.num_generator_workers} workers")

        self.run_until = determine_run_until(self.options, self.sf)
        self.start_time = time.time()
        self.recipe = Path(self.options.get("recipe"))
        self.job_counter = 0
        self.cached_counts = {}
        self.sobject_counts = defaultdict(RunningTotals)

    ## Todo: Consider when this process runs longer than 2 Hours,
    # what will happen to my sf connection?
    def _run_task(self):
        self.setup()

        portions = PortionGenerator(
            self.run_until.gap,
            MIN_PORTION_SIZE,
            MAX_PORTION_SIZE,
        )

        working_directory = self.options.get("working_directory")
        with self.workingdir_or_tempdir(working_directory) as working_directory:

            self.data_gen_q, self.load_data_q = self.configure_queues(working_directory)
            self.logger.info(f"Working directory is {working_directory}")

            if self.run_until.nothing_to_do:
                self.logger.info(
                    f"Dataload is finished before it started! {self.run_until.nothing_to_do_because}"
                )
                return

            template_path, relevant_sobjects = self._generate_and_load_initial_batch(
                self.load_data_q.outbox_dir
            )

            # disable OrgReordCounts for now until it's reliability can be better
            # tested and documented.

            # Retrieve OrgRecordCounts code from
            # https://github.com/SFDO-Tooling/CumulusCI/commit/7d703c44b94e8b21f165e5538c2249a65da0a9eb#diff-54676811961455410c30d9c9405a8f3b9d12a6222a58db9d55580a2da3cfb870R147

            upload_status = self._loop(
                template_path,
                working_directory,
                None,
                portions,
            )
            self.finish(upload_status, self.data_gen_q, self.load_data_q)

    def configure_queues(self, working_directory):
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
            parent_dir=working_directory,
            name="data_gen",
            task_class=GenerateDataFromYaml,
            make_task_options=self.data_generator_opts,
            queue_size=0,
            num_workers=self.num_generator_workers,
        )
        data_gen_q = WorkerQueue(data_gen_q_config)

        load_data_q_config = WorkerQueueConfig(
            project_config=self.project_config,
            org_config=self.org_config,
            connected_app=connected_app,
            redirect_logging=True,
            spawn_class=WorkerQueue.Thread,
            parent_dir=working_directory,
            name="data_load",
            task_class=LoadData,
            make_task_options=self.data_loader_opts,
            queue_size=LOAD_QUEUE_SIZE,
            num_workers=self.num_loader_workers,
            rename_directory=self.data_loader_new_directory_name,
        )
        load_data_q = WorkerQueue(load_data_q_config)

        data_gen_q.feeds_data_to(load_data_q)
        return data_gen_q, load_data_q

    def _loop(
        self,
        template_path,
        tempdir,
        org_record_counts_thread,
        portions: PortionGenerator,
    ):
        """The inner loop that controls when data is generated and when we are done."""
        upload_status = self.generate_upload_status(
            portions.next_batch_size,
            template_path,
        )

        while not portions.done(upload_status.total_sets_working_on_or_uploaded):
            if self.debug_mode:
                self.logger.info(f"Working Directory: {tempdir}")

            self.tick(
                upload_status,
                template_path,
                tempdir,
                portions,
            )

            time.sleep(WAIT_TIME)

            upload_status = self._report_status(
                portions.batch_size,
                org_record_counts_thread,
                template_path,
            )

        return upload_status

    def _report_status(
        self,
        batch_size,
        org_record_counts_thread,
        template_path,
    ):
        """Let the user know what is going on."""
        self.logger.info(
            "\n********** PROGRESS *********",
        )

        upload_status = self.generate_upload_status(
            batch_size or 0,
            template_path,
        )

        self.logger.info(upload_status._display(detailed=self.debug_mode))

        if upload_status.sets_failed:
            self.log_failures(
                set(self.load_data_q.failed_job_dirs + self.data_gen_q.failed_job_dirs)
            )

        if upload_status.sets_failed > ERROR_THRESHOLD:
            raise exc.BulkDataException(
                f"Errors exceeded threshold: {upload_status.sets_failed} vs {ERROR_THRESHOLD}"
            )

        # TODO: Retrieve OrgRecordCounts code from
        # https://github.com/SFDO-Tooling/CumulusCI/commit/7d703c44b94e8b21f165e5538c2249a65da0a9eb#diff-54676811961455410c30d9c9405a8f3b9d12a6222a58db9d55580a2da3cfb870R147

        return upload_status

    def update_running_totals(self) -> None:
        while True:
            try:
                results = self.load_data_q.results_reporter.get(block=False)
            except Empty:
                break
            if "results" in results:
                self.update_running_totals_from_load_step_results(results["results"])
            elif "error" in results:
                self.logger.warning(f"Error in load: {results}")
            else:  # pragma: no cover
                self.logger.warning(f"Unexpected message from subtask: {results}")

    def update_running_totals_from_load_step_results(self, results: dict) -> None:
        for result in results["step_results"].values():
            sobject_name = result["sobject"]
            totals = self.sobject_counts[sobject_name]
            totals.errors += result["total_row_errors"]
            totals.successes += result["records_processed"] - result["total_row_errors"]

    def print_running_totals(self):
        for name, result in self.sobject_counts.items():
            self.logger.info(
                f"       {name}: {result.successes:,} successes, {result.errors:,} errors"
            )

    def tick(
        self,
        upload_status,
        template_path,
        tempdir,
        portions: PortionGenerator,
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
                upload_status = self.generate_upload_status(
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
                self.update_running_totals()
                self.print_running_totals()

    def finish(self, upload_status, data_gen_q, load_data_q):
        """Wait for jobs to finish"""
        old_message = None
        cooldown = 5
        while data_gen_q.workers + load_data_q.workers:
            datagen_workers = f"{len(data_gen_q.workers)} datagen, "
            msg = f"Waiting for {datagen_workers}{len(load_data_q.workers)} upload workers to finish"
            if old_message != msg or cooldown < 1:
                old_message = msg
                self.logger.info(msg)
                self.update_running_totals()
                self.print_running_totals()
                cooldown = 5
            else:
                cooldown -= 1
            data_gen_q.tick()
            time.sleep(WAIT_TIME)

        self.log_failures(set(load_data_q.failed_job_dirs + data_gen_q.failed_job_dirs))

        self.logger.info("")
        self.logger.info(" == Results == ")
        self.update_running_totals()
        self.print_running_totals()
        elapsed = format_duration(timedelta(seconds=time.time() - self.start_time))

        if self.run_until.sobject_name:
            result_msg = f"{self.sobject_counts[self.run_until.sobject_name].successes} {self.run_until.sobject_name} records and associated records"
        else:
            result_msg = f"{upload_status.target_count:,} iterations"

        self.logger.info(f"☃ Snowfakery created {result_msg} in {elapsed}.")

    def log_failures(self, dirs=T.Sequence[Path]):
        """Log failures from sub-processes to main process"""
        for failure_dir in dirs:
            f = Path(failure_dir) / "exception.txt"
            if not f.exists():  # pragma: no cover
                continue
            exception = f.read_text(encoding="utf-8").strip().split("\n")[-1]
            self.logger.info(exception)

    def data_loader_opts(self, working_dir: Path):
        wd = SnowfakeryWorkingDirectory(working_dir)

        options = {
            "mapping": wd.mapping_file,
            "reset_oids": False,
            "database_url": wd.database_url,
            "set_recently_viewed": False,
            "ignore_row_errors": self.ignore_row_errors,
        }
        return options

    # TODO: This method is actually based on the number generated,
    #       because it is called before the load.
    #       If there are row errors, it will drift out of correctness
    #       Code needs to be updated to rename again after load.
    #       Or move away from using directory names for math altogether.
    def data_loader_new_directory_name(self, working_dir: Path):
        """Change the directory name to reflect the true number of sets created."""

        wd = SnowfakeryWorkingDirectory(working_dir)
        key = wd.index
        if key not in self.cached_counts:
            self.cached_counts[key] = wd.get_record_counts()

        if not self.run_until.sobject_name:
            return working_dir

        count = self.cached_counts[key][self.run_until.sobject_name]

        path, _ = str(working_dir).rsplit("_", 1)
        new_working_dir = Path(path + "_" + str(count))
        return new_working_dir

    def generator_data_dir(self, idx, template_path, batch_size, parent_dir):
        """Create a new generator directory with a name based on index and batch_size"""
        assert batch_size > 0
        data_dir = parent_dir / (str(idx) + "_" + str(batch_size))
        shutil.copytree(template_path, data_dir)
        return data_dir

    def data_generator_opts(self, working_dir, *args, **kwargs):
        """Generate task options for a data generator"""
        wd = SnowfakeryWorkingDirectory(working_dir)
        name = Path(working_dir).name
        parts = name.rsplit("_", 1)
        batch_size = int(parts[-1])

        return {
            "generator_yaml": str(self.recipe),
            "database_url": wd.database_url,
            "num_records": batch_size,
            "reset_oids": False,
            "continuation_file": wd.continuation_file,
            "num_records_tablename": self.run_until.sobject_name or COUNT_REPS,
        }

    def generate_upload_status(
        self,
        batch_size,
        template_dir,
    ):
        """Combine information from the different data sources into a single "report".

        Useful for debugging but also for making decisions about what to do next."""

        def set_count_from_names(names):
            return sum(int(name.split("_")[1]) for name in names)

        rc = UploadStatus(
            target_count=self.run_until.gap,
            sets_queued_to_be_generated=set_count_from_names(
                self.data_gen_q.queued_jobs
            ),
            sets_being_generated=set_count_from_names(self.data_gen_q.inprogress_jobs),
            sets_queued_for_loading=set_count_from_names(self.load_data_q.queued_jobs),
            # note that these may count as already imported in the org
            sets_being_loaded=set_count_from_names(self.load_data_q.inprogress_jobs),
            min_portion_size=MIN_PORTION_SIZE,
            max_portion_size=MAX_PORTION_SIZE,
            user_max_num_generator_workers=self.num_generator_workers,
            user_max_num_loader_workers=self.num_loader_workers,
            elapsed_seconds=int(time.time() - self.start_time),
            # todo: use row-level result from org load for better accuracy
            sets_finished=set_count_from_names(self.load_data_q.outbox_jobs),
            sets_failed=len(self.load_data_q.failed_jobs),
            batch_size=batch_size,
            inprogress_generator_jobs=len(self.data_gen_q.inprogress_jobs),
            inprogress_loader_jobs=len(self.load_data_q.inprogress_jobs),
            data_gen_free_workers=self.data_gen_q.num_free_workers,
        )
        return rc

    @contextmanager
    def workingdir_or_tempdir(self, working_directory: T.Optional[T.Union[Path, str]]):
        """Make a working directory or a temporary directory, as needed"""
        if working_directory:
            working_directory = Path(working_directory)
            working_directory.mkdir()
            self.logger.info(f"Working Directory {working_directory}")
            yield working_directory
        elif self.debug_mode:
            working_directory = Path(mkdtemp())
            self.logger.info(
                f"Due to debug mode, Working Directory {working_directory} will not be removed"
            )
            yield working_directory
        else:
            with TemporaryDirectory() as tempdir:
                yield Path(tempdir)

    def _generate_and_load_initial_batch(self, working_directory: T.Optional[Path]):
        """Generate a single batch to set up all just_once (singleton) objects"""

        template_dir = Path(working_directory) / "template_1"
        template_dir.mkdir()
        results = self._generate_and_load_batch(
            template_dir,
            {
                "generator_yaml": self.options.get("recipe"),
                "num_records": 1,  # smallest possible batch to get to parallelizing fast
                "num_records_tablename": self.run_until.sobject_name or COUNT_REPS,
            },
        )
        self.update_running_totals_from_load_step_results(results)

        # rename directory to reflect real number of sets created.
        wd = SnowfakeryWorkingDirectory(template_dir)
        new_template_dir = self.data_loader_new_directory_name(template_dir)
        shutil.move(template_dir, new_template_dir)
        template_dir = new_template_dir

        # don't send data tables to child processes. All they
        # care about are ID->OID mappings
        wd = SnowfakeryWorkingDirectory(template_dir)
        self._cleanup_object_tables(*wd.setup_engine())

        return template_dir, wd.relevant_sobjects()

    def _generate_and_load_batch(self, tempdir, options) -> dict:
        options = {
            **options,
            "working_directory": tempdir,
            "set_recently_viewed": False,
            "ignore_row_errors": self.ignore_row_errors,
        }
        subtask_config = TaskConfig({"options": options})
        subtask = GenerateAndLoadDataFromYaml(
            project_config=self.project_config,
            task_config=subtask_config,
            org_config=self.org_config,
            flow=self.flow,
            name=self.name,
            stepnum=self.stepnum,
        )
        subtask()
        return subtask.return_values["load_results"][0]

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
    """Single "report" of the current status of our processes."""

    batch_size: int
    sets_being_generated: int
    sets_queued_to_be_generated: int
    sets_being_loaded: int
    sets_queued_for_loading: int
    sets_finished: int
    target_count: int
    min_portion_size: int
    max_portion_size: int
    user_max_num_loader_workers: int
    user_max_num_generator_workers: int
    elapsed_seconds: int
    sets_failed: int
    inprogress_generator_jobs: int
    inprogress_loader_jobs: int
    data_gen_free_workers: int

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


class SnowfakeryWorkingDirectory:
    """Helper functions based on well-known filenames in CCI/Snowfakery working directories."""

    def __init__(self, working_dir):
        self.path = working_dir
        self.mapping_file = working_dir / "temp_mapping.yml"
        self.database_file = working_dir / "generated_data.db"
        assert self.mapping_file.exists(), self.mapping_file
        assert self.database_file.exists(), self.database_file
        self.database_url = f"sqlite:///{self.database_file}"
        self.continuation_file = f"{working_dir}/continuation.yml"

    def setup_engine(self):
        """Set up the database engine"""
        engine = create_engine(self.database_url)

        metadata = MetaData(engine)
        metadata.reflect()
        return engine, metadata

    @property
    def index(self) -> str:
        return self.path.name.rsplit("_")[0]

    def get_record_counts(self):
        """Get record counts generated for this portion."""
        engine, metadata = self.setup_engine()

        with engine.connect() as connection:
            record_counts = {
                table_name: self._record_count_from_db(connection, table)
                for table_name, table in metadata.tables.items()
                if table_name[-6:] != "sf_ids"
            }
        # note that the template has its contents deleted so if the cache
        # is ever removed, it will start to return {}
        assert record_counts
        return record_counts

    def _record_count_from_db(self, connection, table: Table):
        """Count rows in a table"""
        stmt = select(func.count()).select_from(table)
        result = connection.execute(stmt)
        return next(result)[0]

    def relevant_sobjects(self):
        with open(self.mapping_file, encoding="utf-8") as f:
            mapping = yaml.safe_load(f)
            return [m.get("sf_object") for m in mapping.values() if m.get("sf_object")]


class RunningTotals:
    errors: int = 0
    successes: int = 0

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.__dict__}>"
