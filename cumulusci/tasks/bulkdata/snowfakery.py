import shutil
import time
import typing as T
from collections import defaultdict
from contextlib import contextmanager
from datetime import timedelta
from math import ceil
from pathlib import Path
from queue import Empty
from tempfile import TemporaryDirectory, mkdtemp

import psutil
from snowfakery.api import COUNT_REPS, infer_load_file_path
from snowfakery.cci_mapping_files.declaration_parser import (
    ChannelDeclaration,
    SObjectRuleDeclarationFile,
)

import cumulusci.core.exceptions as exc
from cumulusci.core.config import OrgConfig, TaskConfig
from cumulusci.core.debug import get_debug_mode
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.utils import (
    format_duration,
    process_bool_arg,
    process_list_arg,
    process_list_of_pairs_dict_arg,
)
from cumulusci.tasks.bulkdata.generate_and_load_data_from_yaml import (
    GenerateAndLoadDataFromYaml,
)
from cumulusci.tasks.salesforce import BaseSalesforceApiTask

from .snowfakery_utils.queue_manager import (
    SnowfakeryChannelManager,
    data_loader_new_directory_name,
)
from .snowfakery_utils.snowfakery_run_until import PortionGenerator, determine_run_until
from .snowfakery_utils.snowfakery_working_directory import SnowfakeryWorkingDirectory
from .snowfakery_utils.subtask_configurator import SubtaskConfigurator

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
        "recipe_options": {
            "required": False,
            "description": """Pass values to override options in the format VAR1:foo,VAR2:bar

             Example: --recipe_options weight:10,color:purple""",
        },
        "bulk_mode": {
            "description": "Set to Serial to serialize everything: data generation, data loading, data ingestion through bulk API. Parallel is the default."
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
        "Validate options before executing the task or before freezing it"
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
        self.drop_missing_schema = process_bool_arg(
            self.options.get("drop_missing_schema", False)
        )

        loading_rules = process_list_arg(self.options.get("loading_rules")) or []
        self.loading_rules = [Path(path) for path in loading_rules if path]
        self.recipe_options = process_list_of_pairs_dict_arg(
            self.options.get("recipe_options") or {}
        )
        self.bulk_mode = self.options.get("bulk_mode", "Parallel").title()
        if self.bulk_mode and self.bulk_mode not in ["Serial", "Parallel"]:
            raise TaskOptionsError("bulk_mode must be either Serial or Parallel")

    def _init_channel_configs(self, recipe):
        """The channels describe the 'shape' of the communication

        The normal case is a single, parallelized, bulk channel,
        multi-threaded on client and server, using a single user
        account.

        Using .load.yml you can add more channels, utilizing
        more user accounts which can speed up throughput in
        a few cases.

        This method reads files and options to determine
        what channels should be created later.
        """
        channel_decls = read_channel_declarations(recipe, self.loading_rules)

        if channel_decls:
            self.channel_configs = channel_configs_from_decls(
                channel_decls, self.project_config.keychain
            )
        elif self.bulk_mode == "Serial":
            self.channel_configs = [
                standard_channel_config(
                    self.org_config,
                    self.recipe_options,
                    1,
                    1,
                )
            ]
        else:
            self.channel_configs = [
                standard_channel_config(
                    self.org_config,
                    self.recipe_options,
                    self.num_generator_workers,
                    None,
                )
            ]

    def setup(self):
        """Setup for loading."""
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
        self.sobject_counts = defaultdict(RunningTotals)
        self._init_channel_configs(self.recipe)

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
            self._setup_channels_and_queues(working_directory)
            self.logger.info(f"Working directory is {working_directory}")

            if self.run_until.nothing_to_do:
                self.logger.info(
                    f"Dataload is finished before it started! {self.run_until.nothing_to_do_because}"
                )
                return

            template_path, relevant_sobjects = self._generate_and_load_initial_batch(
                working_directory
            )

            # disable OrgReordCounts for now until it's reliability can be better
            # tested and documented.

            # Retrieve OrgRecordCounts code from
            # https://github.com/SFDO-Tooling/CumulusCI/commit/7d703c44b94e8b21f165e5538c2249a65da0a9eb#diff-54676811961455410c30d9c9405a8f3b9d12a6222a58db9d55580a2da3cfb870R147

            self._loop(
                template_path,
                working_directory,
                None,
                portions,
            )
            self.finish()

    def _setup_channels_and_queues(self, working_directory):
        """Set up all of the channels and queues.

        In particular their directories and the in-memory
        runtime datastructures.

        Each channel can hold multiple queues.
        """
        additional_load_options = {
            "ignore_row_errors": self.ignore_row_errors,
            "drop_missing_schema": self.drop_missing_schema,
        }
        subtask_configurator = SubtaskConfigurator(
            self.recipe, self.run_until, self.bulk_mode, additional_load_options
        )
        self.queue_manager = SnowfakeryChannelManager(
            project_config=self.project_config,
            logger=self.logger,
            subtask_configurator=subtask_configurator,
        )
        if len(self.channel_configs) == 1:
            channel = self.channel_configs[0]
            self.queue_manager.add_channel(
                org_config=channel.org_config,
                num_generator_workers=channel.declaration.num_generators,
                num_loader_workers=channel.declaration.num_loaders,
                working_directory=working_directory,
                recipe_options=channel.declaration.recipe_options,
            )
        else:
            self.configure_multiple_channels(working_directory)

    def configure_multiple_channels(self, working_directory):
        """If there is more than one channel (=user account),
        pre-allocate work among them.
        """
        allocated_generator_workers = sum(
            (channel.declaration.num_generators or 0)
            for channel in self.channel_configs
        )
        channels_without_workers = len(
            [
                channel.declaration.num_generators
                for channel in self.channel_configs
                if not channel.declaration.num_generators
            ]
        )
        remaining_generator_workers = (
            self.num_generator_workers - allocated_generator_workers
        )
        num_generators_per_channel = ceil(
            remaining_generator_workers / channels_without_workers
        )
        for idx, channel in enumerate(self.channel_configs):
            if self.debug_mode:
                self.logger.info("Initializing %s", channel)
            channel_wd = working_directory / f"channel_{idx}"
            channel_wd.mkdir()
            recipe_options = channel.merge_recipe_options(self.recipe_options)
            generator_workers = (
                channel.declaration.num_generators or num_generators_per_channel
            )

            self.queue_manager.add_channel(
                org_config=channel.org_config,
                num_generator_workers=generator_workers,
                num_loader_workers=channel.declaration.num_loaders,
                working_directory=channel_wd,
                recipe_options=recipe_options,
            )

    def _loop(
        self,
        template_path,
        tempdir,
        org_record_counts_thread,
        portions: PortionGenerator,
    ):
        """The inner loop that controls when data is generated and when we are done."""
        upload_status = self.get_upload_status(
            portions.next_batch_size,
        )

        while not portions.done(upload_status.total_sets_working_on_or_uploaded):
            if self.debug_mode:
                self.logger.info(f"Working Directory: {tempdir}")

            self.queue_manager.tick(
                upload_status,
                template_path,
                tempdir,
                portions,
                self.get_upload_status,
            )
            self.update_running_totals()
            self.print_running_totals()

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

        upload_status = self.get_upload_status(
            batch_size or 0,
        )

        self.logger.info(upload_status._display(detailed=self.debug_mode))

        if upload_status.sets_failed:
            # TODO: this is not sufficiently tested.
            #       commenting it out doesn't break tests
            self.log_failures()

        if upload_status.sets_failed > ERROR_THRESHOLD:
            raise exc.BulkDataException(
                f"Errors exceeded threshold: {upload_status.sets_failed} vs {ERROR_THRESHOLD}"
            )

        # TODO: Retrieve OrgRecordCounts code from
        # https://github.com/SFDO-Tooling/CumulusCI/commit/7d703c44b94e8b21f165e5538c2249a65da0a9eb#diff-54676811961455410c30d9c9405a8f3b9d12a6222a58db9d55580a2da3cfb870R147

        return upload_status

    def update_running_totals(self) -> None:
        """Read and collate result reports from sub-processes/sub-threads

        This is a realtime reporting channel which could, in theory, be updated
        before sub-tasks finish. Currently no sub-tasks are coded to do that.

        The logical next step is to allow LoadData to monitor steps one by
        one or even batches one by one.

        Note that until we implement that, we are paying the complexity
        cost of a real-time channel but not getting the benefits of it.
        """
        while True:
            try:
                results = self.queue_manager.get_results_report()
            except Empty:
                break
            if "results" in results and "step_results" in results["results"]:
                self.update_running_totals_from_load_step_results(results["results"])
            elif "error" in results:
                self.logger.warning(f"Error in load: {results}")
            else:  # pragma: no cover
                self.logger.warning(f"Unexpected message from subtask: {results}")

    def update_running_totals_from_load_step_results(self, results: dict) -> None:
        """'Parse' the results from a load step, to keep track of row errors."""
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

    def finish(self):
        """Wait for jobs to finish"""
        old_message = None
        cooldown = 5
        while not self.queue_manager.check_finished():
            status = self.get_upload_status(0)
            datagen_workers = f"{status.sets_being_generated} data generators, "
            msg = f"Waiting for {datagen_workers}{status.sets_being_loaded} uploads to finish"
            if old_message != msg or cooldown < 1:
                old_message = msg
                self.logger.info(msg)
                self.update_running_totals()
                self.print_running_totals()
                cooldown = 5
            else:
                cooldown -= 1
            time.sleep(WAIT_TIME)

        self.log_failures()

        self.logger.info("")
        self.logger.info(" == Results == ")
        self.update_running_totals()
        self.print_running_totals()
        elapsed = format_duration(timedelta(seconds=time.time() - self.start_time))

        if self.run_until.sobject_name:
            result_msg = f"{self.sobject_counts[self.run_until.sobject_name].successes} {self.run_until.sobject_name} records and associated records"
        else:
            result_msg = f"{self.run_until.target:,} iterations"

        self.logger.info(f"☃ Snowfakery created {result_msg} in {elapsed}.")

    def log_failures(self):
        """Log failures from sub-processes to main process"""
        for exception in self.queue_manager.failure_descriptions():
            self.logger.info(exception)

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

    def get_upload_status(
        self,
        batch_size,
    ):
        """Combine information from the different data sources into a single "report".

        Useful for debugging but also for making decisions about what to do next."""

        return self.queue_manager.get_upload_status(
            batch_size, self.sets_finished_while_generating_template
        )

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

    def _generate_and_load_initial_batch(self, working_directory: Path):
        """Generate a single batch to set up all just_once (singleton) objects"""

        template_dir = Path(working_directory) / "template_1"
        template_dir.mkdir()
        # changes here should often be reflected in
        # data_generator_opts and data_loader_opts

        channel_decl = self.channel_configs[0]

        plugin_options = {
            "pid": "0",
            "big_ids": "True",
        }
        # if it's efficient to do the whole load in one go, let's just do that.
        if self.run_until.gap < MIN_PORTION_SIZE:
            num_records = self.run_until.gap
        else:
            num_records = 1  # smallest possible batch to get to parallelizing fast
        results = self._generate_and_load_batch(
            template_dir,
            channel_decl.org_config,
            {
                "generator_yaml": self.options.get("recipe"),
                "num_records": num_records,
                "num_records_tablename": self.run_until.sobject_name or COUNT_REPS,
                "loading_rules": self.loading_rules,
                "vars": channel_decl.merge_recipe_options(self.recipe_options),
                "plugin_options": plugin_options,
                "bulk_mode": self.bulk_mode,
            },
        )
        self.update_running_totals_from_load_step_results(results)

        # rename directory to reflect real number of sets created.
        wd = SnowfakeryWorkingDirectory(template_dir)
        if self.run_until.sobject_name:
            self.sets_finished_while_generating_template = wd.get_record_counts()[
                self.run_until.sobject_name
            ]
        else:
            self.sets_finished_while_generating_template = num_records

        new_template_dir = data_loader_new_directory_name(template_dir, self.run_until)
        shutil.move(template_dir, new_template_dir)
        template_dir = new_template_dir

        # don't send data tables to child processes. All they
        # care about are ID->OID mappings
        wd = SnowfakeryWorkingDirectory(template_dir)
        self._cleanup_object_tables(*wd.setup_engine())

        return template_dir, wd.relevant_sobjects()

    def _generate_and_load_batch(self, tempdir, org_config, options) -> dict:
        """Before the "full" dataload starts we do a single batch to
        load singletons.
        """
        options = {
            **options,
            "working_directory": tempdir,
            "set_recently_viewed": False,
            "ignore_row_errors": self.ignore_row_errors,
            "drop_missing_schema": self.drop_missing_schema,
        }
        subtask_config = TaskConfig({"options": options})
        subtask = GenerateAndLoadDataFromYaml(
            project_config=self.project_config,
            task_config=subtask_config,
            org_config=org_config,
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


class RunningTotals:
    """Keep track of # of row errors and successess"""

    errors: int = 0
    successes: int = 0

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.__dict__}>"


class RulesFileAndRules(T.NamedTuple):
    file: Path
    rules: T.List[ChannelDeclaration]


def _read_channel_declarations_from_file(
    loading_rules_file: Path,
) -> RulesFileAndRules:
    """Look in a .load.yml file for the channel declarations"""
    with loading_rules_file.open() as f:
        decls = SObjectRuleDeclarationFile.parse_from_yaml(f)
        channel_decls = decls.channel_declarations or []
        assert isinstance(channel_decls, list)
        return RulesFileAndRules(loading_rules_file, channel_decls)


def read_channel_declarations(
    recipe: Path, loading_rules_files: T.List[Path]
) -> T.List[ChannelDeclaration]:
    """Find all appropriate channel declarations.

    Some discovered through naming conventions, others
    through command lines options or YML config."""
    implicit_rules_file = infer_load_file_path(recipe)
    if implicit_rules_file and implicit_rules_file.exists():
        loading_rules_files = loading_rules_files + [implicit_rules_file]
    # uniqify without losing order
    loading_rules_files = list(dict.fromkeys(loading_rules_files))

    rules_lists = [
        _read_channel_declarations_from_file(file) for file in loading_rules_files
    ]
    rules_lists = [rules_list for rules_list in rules_lists if rules_list.rules]

    if len(rules_lists) > 1:
        files = ", ".join(
            [f"{rules_list.file}: {rules_list.rules}" for rules_list in rules_lists]
        )
        msg = f"Multiple channel declarations: {files}"
        raise TaskOptionsError(msg)
    elif len(rules_lists) == 1:
        return rules_lists[0].rules
    else:
        return []


class ChannelConfig(T.NamedTuple):
    """A channel represents a connection to Salesforce via a username.

    It can also have recipe options and other documented properties.
    https://github.com/SFDO-Tooling/Snowfakery/search?q=ChannelDeclaration
    """

    org_config: OrgConfig
    declaration: ChannelDeclaration = None

    def merge_recipe_options(self, task_recipe_options):
        """Merge the recipe options from the channel declaration with those from the task config"""
        channel_options = self.declaration.recipe_options or {}
        task_recipe_options = task_recipe_options or {}
        self.check_conflicting_options(channel_options, task_recipe_options)
        recipe_options = {
            **task_recipe_options,
            **channel_options,
        }
        return recipe_options

    @staticmethod
    def check_conflicting_options(channel_options, task_recipe_options):
        """Check that options do not conflict"""
        double_specified_options = set(task_recipe_options.keys()).intersection(
            set(channel_options.keys())
        )
        conflicting_options = [
            optname
            for optname in double_specified_options
            if task_recipe_options[optname] != channel_options[optname]
        ]
        if conflicting_options:
            raise TaskOptionsError(
                f"Recipe options cannot conflict: {conflicting_options}"
            )


def standard_channel_config(
    org_config: OrgConfig,
    recipe_options: dict,
    num_generators: int,
    num_loaders: int = None,
):
    """Default configuration for a single-channel data-load"""
    channel = ChannelDeclaration(
        user="Username not used in this context",
        recipe_options=recipe_options,
        num_generators=num_generators,
        num_loaders=num_loaders,
    )

    return ChannelConfig(org_config, channel)


def channel_configs_from_decls(
    channel_decls: T.List[ChannelDeclaration],
    keychain: BaseProjectKeychain,
):
    """Reify channel configs and look up orgconfig"""

    def config_from_decl(decl):
        return ChannelConfig(keychain.get_org(decl.user), decl)

    return [config_from_decl(decl) for decl in channel_decls]
