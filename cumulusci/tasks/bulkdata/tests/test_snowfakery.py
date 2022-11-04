import re
import typing as T
from collections import Counter
from contextlib import contextmanager
from itertools import cycle
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock, Thread
from unittest import mock

import pytest
import yaml
from sqlalchemy import MetaData, create_engine

from cumulusci.core import exceptions as exc
from cumulusci.core.config import OrgConfig
from cumulusci.tasks.bulkdata.snowfakery import (
    RunningTotals,
    Snowfakery,
    SnowfakeryWorkingDirectory,
)
from cumulusci.tasks.bulkdata.tests.integration_test_utils import ensure_accounts
from cumulusci.tasks.bulkdata.tests.utils import _make_task
from cumulusci.tasks.salesforce.BaseSalesforceApiTask import BaseSalesforceApiTask
from cumulusci.tests.util import DummyKeychain, DummyOrgConfig
from cumulusci.utils.parallel.task_worker_queues.tests.test_parallel_worker import (
    DelaySpawner,
)

ensure_accounts = ensure_accounts  # fixes 4 lint errors at once. Don't hate the player, hate the game.

simple_salesforce_yaml = (
    Path(__file__).parent / "snowfakery/simple_snowfakery.recipe.yml"
)
sample_yaml = Path(__file__).parent / "snowfakery/gen_npsp_standard_objects.recipe.yml"
query_yaml = Path(__file__).parent / "snowfakery/query_snowfakery.recipe.yml"

original_refresh_token = OrgConfig.refresh_oauth_token

FAKE_LOAD_RESULTS = (
    {
        "Insert Account": {
            "sobject": "Account",
            "record_type": None,
            "status": "Success",
            "records_processed": 2,
            "total_row_errors": 0,
        },
        "Insert Contact": {
            "sobject": "Contact",
            "record_type": None,
            "status": "Success",
            "records_processed": 2,
            "total_row_errors": 0,
        },
    },
    {
        "Insert Account": {
            "sobject": "Account",
            "record_type": None,
            "status": "Success",
            "records_processed": 3,
            "total_row_errors": 0,
        },
        "Insert Contact": {
            "sobject": "Contact",
            "record_type": None,
            "status": "Success",
            "records_processed": 3,
            "total_row_errors": 0,
        },
    },
)


def table_values(connection, table):
    query = f"select * from {table.name}"
    values = [val for val in connection.execute(query)]
    return values


class FakeLoadData(BaseSalesforceApiTask):
    """Simulates load results without doing a real load."""

    # these are all used as mutable class variables
    mock_calls: list  # similar to how a mock.Mock() object works
    fake_return_values: T.Iterator
    fake_exception_on_request = -1
    lock = Lock()

    # Manipulating "self" from a mock side-effect is a challenge.
    # So we need a "real function"
    def __call__(self, *args, **kwargs):
        """Like the __call__ of _run_task, but also capture calls
        in a normal mock_values structure."""

        with self.lock:  # the code below looks thread-safe but better safe than sorry

            # tasks usually aren't called twice after being instantiated
            # that would usually be a bug.
            assert self not in self.mock_calls
            self.__class__.mock_calls.append(self)

            if (
                len(self.__class__.mock_calls)
                == self.__class__.fake_exception_on_request
            ):
                raise AssertionError("You asked me to raise an exception")

            # get the values that the Snowfakery task asked us to load and
            # remember them for later inspection.
            self.values_loaded = db_values_from_db_url(self.options["database_url"])

            # TODO:
            #
            #   Parse the mapping and then count matching objects to return
            #   more realistic values.
            # return a fake return value so Snowfakery loader doesn't get confused
            self.return_values = {"step_results": next(self.fake_return_values)}

    # using mutable class variables is not something I would usually do
    # because it is not thread safe, but the test intrinsically uses
    # threads and therefore is not thread safe in general.
    #
    # Furthermore, attempts to use a closure instead of mutable class
    # variables just doesn't work because of how Snowfakery instantiates
    # tasks in sub-threads.
    @classmethod
    def reset(cls, fake_exception_on_request=-1):
        cls.mock_calls = []
        cls.fake_return_values = cycle(iter(FAKE_LOAD_RESULTS))
        cls.fake_exception_on_request = fake_exception_on_request


def db_values_from_db_url(database_url):
    engine = create_engine(database_url)
    metadata = MetaData(engine)
    metadata.reflect()

    with engine.connect() as connection:
        values = {
            table_name: table_values(connection, table)
            for table_name, table in metadata.tables.items()
            if table_name[-6:] != "sf_ids"
        }
    return values


@pytest.fixture
def mock_load_data(
    request,
    threads_instead_of_processes,  # mock patches wouldn't be inherited by child processs
):

    fake_load_data = FakeLoadData
    with mock.patch(
        "cumulusci.tasks.bulkdata.generate_and_load_data.LoadData", fake_load_data
    ), mock.patch(
        "cumulusci.tasks.bulkdata.snowfakery_utils.queue_manager.LoadData",
        fake_load_data,
    ):
        fake_load_data.reset()

        yield fake_load_data
        fake_load_data.reset()


@pytest.fixture
def threads_instead_of_processes(request):
    with mock.patch(
        "cumulusci.utils.parallel.task_worker_queues.parallel_worker_queue.WorkerQueue.Process",
        wraps=Thread,
    ) as t:
        yield t


@pytest.fixture
def fake_processes_and_threads(request):
    class FakeProcessManager:
        def __init__(self):
            self.processes = []

        def __call__(self, target, args, daemon):
            res = self.process_handler(target, args, daemon, index=len(self.processes))
            self.processes.append(res)
            return res

    process_manager = FakeProcessManager()

    with mock.patch(
        "cumulusci.utils.parallel.task_worker_queues.parallel_worker_queue.WorkerQueue.Thread",
        process_manager,
    ), mock.patch(
        "cumulusci.utils.parallel.task_worker_queues.parallel_worker_queue.WorkerQueue.Process",
        process_manager,
    ):
        yield process_manager


@pytest.fixture
def snowfakery(request, create_task):
    def snowfakery(**kwargs):
        return create_task(Snowfakery, kwargs)

    return snowfakery


@contextmanager
def temporary_file_path(filename):
    with TemporaryDirectory() as tmpdirname:
        path = Path(tmpdirname) / filename
        yield path


class SnowfakeryTaskResults(T.NamedTuple):
    """Results from a Snowfakery data generation process"""

    task: Snowfakery  # The task, so we can inspect its return_values
    working_dir: Path  # The working directory, to look at mapping files, DB files, etc.


@pytest.fixture()
def run_snowfakery_and_inspect_mapping(
    run_snowfakery_and_yield_results,
):
    """Run Snowfakery with some defaulted or overriden options.
    Yield a mapping file for inspection that it was the right file.

    Defaults are same as run_snowfakery_and_yield_results.
    """

    def _run_snowfakery_and_inspect_mapping(**options):
        with run_snowfakery_and_yield_results(**options) as results:
            return get_mapping_from_snowfakery_task_results(results)

    return _run_snowfakery_and_inspect_mapping


def get_mapping_from_snowfakery_task_results(results: SnowfakeryTaskResults):
    """Find the shared mapping file and return it."""
    template_dir = SnowfakeryWorkingDirectory(results.working_dir / "template_1/")
    temp_mapping = template_dir.mapping_file
    with open(temp_mapping) as f:
        mapping = yaml.safe_load(f)

    other_mapping = Path(
        str(temp_mapping).replace("template_1", "data_load_outbox/1_1")
    )
    if other_mapping.exists():
        # check that it's truly shared
        assert temp_mapping.read_text() == other_mapping.read_text()
    return mapping


def get_record_counts_from_snowfakery_results(
    results: SnowfakeryTaskResults,
) -> Counter:
    """Collate the record counts from Snowfakery outbox directories.
    Note that records created by the initial, just_once seeding flow are not
    counted because they are deleted. If you need every single result, you
    should probably use return_values instead. (but you may need to implement it)"""

    rollups = Counter()
    # when there is more than one channel, the directory structure is deeper
    channeled_outboxes = tuple(results.working_dir.glob("*/data_load_outbox/*"))
    regular_outboxes = tuple(results.working_dir.glob("data_load_outbox/*"))

    assert bool(regular_outboxes) ^ bool(
        channeled_outboxes
    ), f"One of regular_outboxes or channeled_outboxes should be available: {channeled_outboxes}, {regular_outboxes}"
    outboxes = tuple(channeled_outboxes) + tuple(regular_outboxes)
    for subdir in outboxes:
        record_counts = SnowfakeryWorkingDirectory(subdir).get_record_counts()
        rollups.update(record_counts)

    return rollups


@pytest.fixture()
def run_snowfakery_and_yield_results(snowfakery, mock_load_data):
    @contextmanager
    def _run_snowfakery_and_inspect_mapping_and_example_records(**options):
        with TemporaryDirectory() as workingdir:
            workingdir = Path(workingdir) / "tempdir"
            task = snowfakery(
                working_directory=workingdir,
                **options,
            )
            task()
            yield SnowfakeryTaskResults(task, workingdir)

    return _run_snowfakery_and_inspect_mapping_and_example_records


class TestSnowfakery:
    def test_no_options(self):
        with pytest.raises(exc.TaskOptionsError, match="recipe"):
            _make_task(Snowfakery, {})

    @mock.patch(
        "cumulusci.utils.parallel.task_worker_queues.parallel_worker_queue.WorkerQueue.Process",
    )
    def test_simple_snowfakery(self, Process, mock_load_data, create_task):
        task = create_task(
            Snowfakery,
            {
                "recipe": sample_yaml,
            },
        )
        task()
        # should not be called for a simple one-rep load
        assert not Process.mock_calls

    @mock.patch(
        "cumulusci.utils.parallel.task_worker_queues.parallel_worker_queue.WorkerQueue.Process",
    )
    @pytest.mark.vcr()
    def test_snowfakery_query_salesforce(self, Process, mock_load_data, create_task):
        task = create_task(
            Snowfakery,
            {
                "recipe": query_yaml,
            },
        )
        task()
        assert mock_load_data.mock_calls
        # should not be called for a simple one-rep load
        assert not Process.mock_calls

    @mock.patch("cumulusci.tasks.bulkdata.snowfakery.MIN_PORTION_SIZE", 3)
    def test_small(
        self, mock_load_data, threads_instead_of_processes, create_task_fixture
    ):
        task = create_task_fixture(
            Snowfakery,
            {
                "recipe": sample_yaml,
                "run_until_recipe_repeated": "7",
                "drop_missing_schema": True,
            },
        )
        task()
        # Batch size was 3, so 7 records takes
        # one initial batch plus two parallel batches
        assert len(mock_load_data.mock_calls) == 3, mock_load_data.mock_calls
        # One should be in a sub-process/thread
        assert len(threads_instead_of_processes.mock_calls) == 2
        for call in mock_load_data.mock_calls:
            assert call.task_config.config["options"]["drop_missing_schema"] is True

    @mock.patch("cumulusci.tasks.bulkdata.snowfakery.MIN_PORTION_SIZE", 3)
    def test_multi_part(
        self, threads_instead_of_processes, mock_load_data, create_task_fixture
    ):
        task = create_task_fixture(
            Snowfakery,
            {"recipe": sample_yaml, "run_until_recipe_repeated": 15},
        )
        task()
        assert (
            len(mock_load_data.mock_calls) > 3
        )  # depends on the details of the tuning
        assert (
            len(threads_instead_of_processes.mock_calls)
            == len(mock_load_data.mock_calls) - 1
        )
        for call in mock_load_data.mock_calls:
            assert call.task_config.config["options"]["drop_missing_schema"] is False

    @mock.patch(
        "cumulusci.utils.parallel.task_worker_queues.parallel_worker_queue.WorkerQueue.Process",
    )
    def test_run_until_loaded(
        self, create_subprocess, mock_load_data, create_task_fixture
    ):
        task = create_task_fixture(
            Snowfakery,
            {"recipe": sample_yaml, "run_until_records_loaded": "Account:1"},
        )
        task()
        assert mock_load_data.mock_calls
        # should not be called for a simple one-rep load
        assert not create_subprocess.mock_calls

    @mock.patch("cumulusci.tasks.bulkdata.snowfakery.MIN_PORTION_SIZE", 3)
    def test_run_until_loaded_2_parts(
        self, threads_instead_of_processes, mock_load_data, create_task_fixture
    ):
        task = create_task_fixture(
            Snowfakery,
            {"recipe": sample_yaml, "run_until_records_loaded": "Account:6"},
        )
        task()
        assert len(mock_load_data.mock_calls) == 2
        assert len(threads_instead_of_processes.mock_calls) == 1

    # There was previously a failed attempt at testing the connected app here.
    # Could try again after Snowfakery 2.0 launch.
    # https://github.com/SFDO-Tooling/CumulusCI/blob/c7e0d7552394b3ac268cb373ffb24b72b5c059f3/cumulusci/tasks/bulkdata/tests/test_snowfakery.py#L165-L197https://github.com/SFDO-Tooling/CumulusCI/blob/c7e0d7552394b3ac268cb373ffb24b72b5c059f3/cumulusci/tasks/bulkdata/tests/test_snowfakery.py#L165-L197

    @pytest.mark.vcr()
    def test_run_until_records_in_org__none_needed(
        self, threads_instead_of_processes, mock_load_data, create_task, ensure_accounts
    ):
        with ensure_accounts(6):
            task = create_task(
                Snowfakery,
                {"recipe": sample_yaml, "run_until_records_in_org": "Account:6"},
            )
            task()
        assert len(mock_load_data.mock_calls) == 0, mock_load_data.mock_calls
        assert (
            len(threads_instead_of_processes.mock_calls) == 0
        ), threads_instead_of_processes.mock_calls

    @pytest.mark.vcr()
    @mock.patch("cumulusci.tasks.bulkdata.snowfakery.MIN_PORTION_SIZE", 5)
    def test_run_until_records_in_org__one_needed(
        self,
        sf,
        threads_instead_of_processes,
        mock_load_data,
        create_task,
        ensure_accounts,
    ):
        with ensure_accounts(10):
            # org reports 10 records in org
            # so we only need 6 more.
            # That will be one "initial" batch of 1 plus one "parallel" batch of 5
            task = create_task(
                Snowfakery,
                {"recipe": sample_yaml, "run_until_records_in_org": "Account:16"},
            )
            task.logger = mock.Mock()
            task()
        assert len(mock_load_data.mock_calls) == 2, mock_load_data.mock_calls
        assert len(threads_instead_of_processes.mock_calls) == 1

    @pytest.mark.vcr()
    @mock.patch("cumulusci.tasks.bulkdata.snowfakery.MIN_PORTION_SIZE", 3)
    def test_run_until_records_in_org__multiple_needed(
        self,
        threads_instead_of_processes,
        mock_load_data,
        snowfakery,
        ensure_accounts,
    ):
        with ensure_accounts(10):
            task = snowfakery(recipe=sample_yaml, run_until_records_in_org="Account:16")
            task()

        assert len(mock_load_data.mock_calls) == 2, mock_load_data.mock_calls
        assert (
            len(threads_instead_of_processes.mock_calls) == 1
        ), threads_instead_of_processes.mock_calls

    def test_inaccessible_generator_yaml(self, snowfakery):
        with pytest.raises(exc.TaskOptionsError, match="recipe"):
            task = snowfakery(
                recipe=sample_yaml / "junk",
            )
            task()

    @mock.patch("cumulusci.tasks.bulkdata.snowfakery.get_debug_mode", lambda: True)
    @mock.patch("psutil.cpu_count", lambda logical: 11)
    def test_snowfakery_debug_mode_and_cpu_count(self, snowfakery, mock_load_data):
        task = snowfakery(recipe=sample_yaml, run_until_recipe_repeated="5")
        with mock.patch.object(task, "logger") as logger:
            task()
        assert "Using 11 workers" in str(logger.mock_calls)

    @mock.patch("cumulusci.tasks.bulkdata.snowfakery.MIN_PORTION_SIZE", 3)
    def test_record_count(self, snowfakery, mock_load_data):
        task = snowfakery(recipe="datasets/recipe.yml", run_until_recipe_repeated="4")
        with mock.patch.object(task, "logger") as logger, mock.patch.object(
            task.project_config, "keychain", DummyKeychain()
        ) as keychain:

            def get_org(username):
                return DummyOrgConfig(
                    config={"keychain": keychain, "username": username}
                )

            keychain.get_org = mock.Mock(wraps=get_org)
            task()
        mock_calls_as_string = str(logger.mock_calls)
        # note that load_data is mocked so these values are based on FAKE_LOAD_RESULTS
        # See also: the TODO in FakeLoadData.__call__
        assert "Account: 5 successes" in mock_calls_as_string, mock_calls_as_string[
            -500:
        ]
        assert "Contact: 5 successes" in mock_calls_as_string, mock_calls_as_string[
            -500:
        ]

    def test_run_until_wrong_format(self, snowfakery):
        with pytest.raises(exc.TaskOptionsError, match="Ten"):
            task = snowfakery(
                recipe=sample_yaml, run_until_records_loaded="Account:Ten"
            )
            task()

    def test_run_until_wrong_format__2(self, snowfakery):
        with pytest.raises(exc.TaskOptionsError, match="Ten"):
            task = snowfakery(
                recipe=sample_yaml, run_until_records_loaded="Account_Ten"
            )
            task()

    def test_run_reps_wrong_format(self, snowfakery):
        with pytest.raises(exc.TaskOptionsError, match="Ten"):
            task = snowfakery(recipe=sample_yaml, run_until_recipe_repeated="Ten")
            task()

    def test_run_until_conflicting_params(self, snowfakery):
        with pytest.raises(exc.TaskOptionsError, match="only one of"):
            task = snowfakery(
                recipe=sample_yaml,
                run_until_records_loaded="Account_Ten",
                run_until_recipe_repeated="1",
            )
            task()

    def test_working_directory(self, snowfakery, mock_load_data):
        with TemporaryDirectory() as t:
            working_directory = Path(t) / "junkdir"
            task = snowfakery(
                recipe=sample_yaml,
                run_until_recipe_repeated="1",
                working_directory=str(working_directory),
            )
            task()
            assert (working_directory / "data_load_outbox").exists()

    @mock.patch("cumulusci.tasks.bulkdata.snowfakery.MIN_PORTION_SIZE", 1)
    def xxx__test_failures_in_subprocesses__last_batch(
        self, snowfakery, mock_load_data, fake_processes_and_threads
    ):
        class FakeProcess(DelaySpawner):
            def __init__(self, target, args, daemon, index):
                super().__init__(target, args, daemon)
                self.counter = 0
                self.task_class = args[0]["task_class"]
                self.index = index
                try:
                    self._finish()
                except AssertionError:
                    pass

            def is_alive(self):
                print("Alive?", self.task_class, self.index, self.counter, self)
                self.counter += 1
                if self.counter > 3:
                    return False
                return True

        fake_processes_and_threads.process_handler = FakeProcess

        class LoadDataSucceedsOnceThenFails:
            count = 0

            def __call__(self, *args, **kwargs):
                self.count += 1
                if self.count > 1:
                    raise AssertionError("XYZZY")

        mock_load_data.side_effect = LoadDataSucceedsOnceThenFails()

        task = snowfakery(
            recipe=sample_yaml,
            run_until_records_loaded="Account:10",
            num_processes=3,  # todo: test this is enforced
        )
        with mock.patch.object(task, "logger") as logger:
            with pytest.raises(exc.BulkDataException):
                task()
        assert "XYZZY" in str(logger.mock_calls)

    def test_running_totals_repr(self):
        r = RunningTotals()
        r.errors = 12
        r.successes = 11
        assert "11" in repr(r)

    def test_generate_mapping_file__loadfile__inferred(
        self, run_snowfakery_and_inspect_mapping
    ):

        mapping = run_snowfakery_and_inspect_mapping(
            recipe=simple_salesforce_yaml,
            run_until_recipe_repeated=2,
        )

        assert mapping["Insert Account"]["api"] == "bulk"
        assert mapping["Insert Contact"].get("bulk_mode") is None
        assert list(mapping.keys()) == ["Insert Account", "Insert Contact"]

    def test_generate_mapping_file__loadfile__overridden(
        self, run_snowfakery_and_inspect_mapping
    ):
        loading_rules = str(simple_salesforce_yaml).replace(
            ".recipe.yml", "_2.load.yml"
        )
        mapping = run_snowfakery_and_inspect_mapping(
            recipe=simple_salesforce_yaml,
            loading_rules=str(loading_rules),
            run_until_recipe_repeated=2,
        )

        assert mapping["Insert Account"].get("api") is None
        assert mapping["Insert Contact"]["bulk_mode"].lower() == "parallel"
        assert list(mapping.keys()) == ["Insert Contact", "Insert Account"]

    def test_generate_mapping_file__loadfile_multiple_files(
        self, run_snowfakery_and_inspect_mapping
    ):
        loading_rules = (
            str(simple_salesforce_yaml).replace(".recipe.yml", "_2.load.yml")
            + ","
            + str(simple_salesforce_yaml).replace(".recipe.yml", ".load.yml")
        )
        mapping = run_snowfakery_and_inspect_mapping(
            recipe=simple_salesforce_yaml,
            loading_rules=str(loading_rules),
            run_until_recipe_repeated=2,
        )

        assert mapping["Insert Account"]["api"] == "bulk"
        assert mapping["Insert Contact"]["bulk_mode"].lower() == "parallel"
        assert list(mapping.keys()) == ["Insert Contact", "Insert Account"]

    @mock.patch(
        "cumulusci.tasks.bulkdata.snowfakery.MIN_PORTION_SIZE", 1
    )  # force multi-step load
    def test_options(
        self,
        mock_load_data,
        run_snowfakery_and_yield_results,
    ):
        options_yaml = str(sample_yaml).replace(
            "gen_npsp_standard_objects.recipe.yml", "options.recipe.yml"
        )
        with run_snowfakery_and_yield_results(
            recipe=options_yaml,
            recipe_options="row_count:7,account_name:aaaaa",
            run_until_recipe_repeated=2,
        ) as results:
            record_counts = get_record_counts_from_snowfakery_results(results)
        assert record_counts["Account"] == 7, record_counts["Account"]

    @mock.patch("cumulusci.tasks.bulkdata.snowfakery.MIN_PORTION_SIZE", 3)
    def test_multi_part_uniqueness(self, mock_load_data, create_task_fixture):
        task = create_task_fixture(
            Snowfakery,
            {
                "recipe": Path(__file__).parent / "snowfakery/unique_values.recipe.yml",
                "run_until_recipe_repeated": 15,
            },
        )
        task()
        all_data_load_inputs = mock_load_data.mock_calls
        all_rows = [
            task_instance.values_loaded["blah"]
            for task_instance in all_data_load_inputs
        ]

        unique_values = [row.value for batchrows in all_rows for row in batchrows]
        assert len(mock_load_data.mock_calls) == 6, len(mock_load_data.mock_calls)
        assert len(unique_values) == 30, len(unique_values)
        assert len(set(unique_values)) == 30, unique_values

    @mock.patch("cumulusci.tasks.bulkdata.snowfakery.MIN_PORTION_SIZE", 2)
    def test_two_channels(self, mock_load_data, create_task):
        task = create_task(
            Snowfakery,
            {
                "recipe": Path(__file__).parent
                / "snowfakery/simple_snowfakery_channels.recipe.yml",
                "run_until_recipe_repeated": 15,
                "recipe_options": {"xyzzy": "Nothing happens", "some_number": 42},
            },
        )
        with mock.patch.object(
            task.project_config, "keychain", DummyKeychain()
        ) as keychain:

            def get_org(username):
                return DummyOrgConfig(
                    config={"keychain": keychain, "username": username}
                )

            keychain.get_org = mock.Mock(wraps=get_org)
            task()
            assert keychain.get_org.mock_calls
            assert keychain.get_org.call_args_list
            assert keychain.get_org.call_args_list == [
                (("channeltest",),),
                (("channeltest-b",),),
                (("channeltest-c",),),
                (("Account",),),
            ], keychain.get_org.call_args_list

        all_data_load_inputs = mock_load_data.mock_calls
        all_data_load_inputs = sorted(
            all_data_load_inputs,
            key=lambda task_instance: task_instance.org_config.username,
        )
        usernames_values = [
            (task_instance.org_config.username, task_instance.values_loaded)
            for task_instance in all_data_load_inputs
        ]
        count_loads = Counter(username for username, _ in usernames_values)
        assert count_loads.keys() == {
            "channeltest",
            "channeltest-b",
            "channeltest-c",
            "Account",
        }

        # depends on threading. :(
        for value in count_loads.values():
            assert 1 <= value <= 4, value
        assert sum(count_loads.values()) == 8

        first_row_values = next(
            value["Account"]
            for username, value in usernames_values
            if username == "channeltest"
        )
        assert len(first_row_values) == 1, len(first_row_values)
        for username, values in usernames_values:
            accounts = values["Account"]
            if values["Account"] != first_row_values:
                assert len(accounts) == 2, (values, first_row_values)
            for account in accounts:
                assert int(account.some_number) == 42
                assert username in account.name, (username, account.name)

        assert sum(len(v["Account"]) for _, v in usernames_values) == 15, sum(
            len(v) for _, v in usernames_values
        )

    def test_channels_cli_options_conflict(self, create_task):
        task = create_task(
            Snowfakery,
            {
                "recipe": Path(__file__).parent
                / "snowfakery/simple_snowfakery_channels.recipe.yml",
                "run_until_recipe_repeated": 15,
                "recipe_options": {"xyzzy": "Nothing happens", "some_number": 37},
            },
        )
        with pytest.raises(exc.TaskOptionsError) as e, mock.patch.object(
            task.project_config, "keychain", DummyKeychain()
        ) as keychain:

            def get_org(username):
                return DummyOrgConfig(
                    config={"keychain": keychain, "username": username}
                )

            keychain.get_org = mock.Mock(wraps=get_org)
            task()
        assert "conflict" in str(e.value)
        assert "some_number" in str(e.value)

    @mock.patch(
        "cumulusci.tasks.bulkdata.snowfakery.get_debug_mode", lambda: True
    )  # for coverage
    @mock.patch("cumulusci.tasks.bulkdata.snowfakery.MIN_PORTION_SIZE", 2)
    def test_explicit_channel_declarations(self, mock_load_data, create_task):
        task = create_task(
            Snowfakery,
            {
                "recipe": Path(__file__).parent
                / "snowfakery/simple_snowfakery.recipe.yml",
                "run_until_recipe_repeated": 15,
                "recipe_options": {"xyzzy": "Nothing happens", "some_number": 42},
                "loading_rules": Path(__file__).parent
                / "snowfakery/simple_snowfakery_channels.load.yml",
            },
        )
        with mock.patch.object(
            task.project_config, "keychain", DummyKeychain()
        ) as keychain:

            def get_org(username):
                return DummyOrgConfig(
                    config={"keychain": keychain, "username": username}
                )

            keychain.get_org = mock.Mock(wraps=get_org)
            task()
            assert keychain.get_org.mock_calls
            assert keychain.get_org.call_args_list
            assert keychain.get_org.call_args_list == [
                (("channeltest",),),
                (("channeltest-b",),),
                (("channeltest-c",),),
                (("Account",),),
            ], keychain.get_org.call_args_list

            all_data_load_inputs = mock_load_data.mock_calls
            all_data_load_inputs = sorted(
                all_data_load_inputs,
                key=lambda task_instance: task_instance.org_config.username,
            )
            usernames_values = [
                (task_instance.org_config.username, task_instance.values_loaded)
                for task_instance in all_data_load_inputs
            ]
            count_loads = Counter(username for username, _ in usernames_values)
            assert count_loads.keys() == {
                "channeltest",
                "channeltest-b",
                "channeltest-c",
                "Account",
            }

    @mock.patch("cumulusci.tasks.bulkdata.snowfakery.MIN_PORTION_SIZE", 2)
    def test_serial_mode(self, mock_load_data, create_task):
        task = create_task(
            Snowfakery,
            {
                "recipe": Path(__file__).parent
                / "snowfakery/simple_snowfakery.recipe.yml",
                "run_until_recipe_repeated": 15,
                "recipe_options": {"xyzzy": "Nothing happens", "some_number": 42},
                "bulk_mode": "Serial",
            },
        )
        with mock.patch.object(
            task.project_config, "keychain", DummyKeychain()
        ) as keychain:

            def get_org(username):
                return DummyOrgConfig(
                    config={"keychain": keychain, "username": username}
                )

            keychain.get_org = mock.Mock(wraps=get_org)
            task.logger = mock.Mock()
            task()
            for data_load_fake in mock_load_data.mock_calls:
                assert data_load_fake.options["bulk_mode"] == "Serial"
            pattern = r"Inprogress Loader Jobs: (\d+)"
            loader_counts = re.findall(pattern, str(task.logger.mock_calls))
            assert loader_counts, loader_counts
            assert 0 <= all(int(count) <= 1 for count in loader_counts), loader_counts

    @mock.patch("cumulusci.tasks.bulkdata.snowfakery.MIN_PORTION_SIZE", 2)
    def test_bulk_mode_error(self, create_task, mock_load_data):
        with pytest.raises(exc.TaskOptionsError):
            task = create_task(
                Snowfakery,
                {
                    "recipe": Path(__file__).parent
                    / "snowfakery/simple_snowfakery.recipe.yml",
                    "bulk_mode": "XYZZY",
                },
            )
            task()

    @mock.patch("cumulusci.tasks.bulkdata.snowfakery.MIN_PORTION_SIZE", 2)
    def test_too_many_channel_declarations(self, mock_load_data, create_task):
        task = create_task(
            Snowfakery,
            {
                "recipe": Path(__file__).parent
                / "snowfakery/simple_snowfakery_channels.recipe.yml",
                "run_until_recipe_repeated": 15,
                "recipe_options": {"xyzzy": "Nothing happens", "some_number": 42},
                "loading_rules": Path(__file__).parent
                / "snowfakery/simple_snowfakery_channels_2.load.yml",
            },
        )
        with pytest.raises(exc.TaskOptionsError), mock.patch.object(
            task.project_config, "keychain", DummyKeychain()
        ) as keychain:

            def get_org(username):
                return DummyOrgConfig(
                    config={"keychain": keychain, "username": username}
                )

            keychain.get_org = mock.Mock(wraps=get_org)
            task()

    @pytest.mark.skip()  # TODO: make handling of errors more predictable and re-enable
    @mock.patch("cumulusci.tasks.bulkdata.snowfakery.MIN_PORTION_SIZE", 2)
    def test_error_handling_in_channels(self, mock_load_data, create_task):
        task = create_task(
            Snowfakery,
            {
                "recipe": Path(__file__).parent
                / "snowfakery/simple_snowfakery.recipe.yml",
                "run_until_recipe_repeated": 15,
                "loading_rules": Path(__file__).parent
                / "snowfakery/simple_snowfakery_channels.load.yml",
            },
        )
        with mock.patch.object(
            task.project_config, "keychain", DummyKeychain()
        ) as keychain:

            def get_org(username):
                return DummyOrgConfig(
                    config={"keychain": keychain, "username": username}
                )

            keychain.get_org = mock.Mock(wraps=get_org)
            with pytest.raises(exc.BulkDataException):
                mock_load_data.reset(fake_exception_on_request=3)
                task()

    @pytest.mark.vcr()
    @pytest.mark.skip()
    def test_snowfakery_upsert(self, create_task, sf, run_code_without_recording):
        task = create_task(
            Snowfakery,
            {
                "recipe": Path(__file__).parent / "snowfakery/upsert.recipe.yml",
            },
        )

        def assert_bluth_name(name):
            data = sf.query(
                "select FirstName from Contact where email='michael@bluth.com'"
            )
            assert data["records"][0]["FirstName"] == name

        task()
        run_code_without_recording(lambda: assert_bluth_name("Michael"))

        task = create_task(
            Snowfakery,
            {
                "recipe": Path(__file__).parent / "snowfakery/upsert_2.recipe.yml",
            },
        )

        task()
        run_code_without_recording(lambda: assert_bluth_name("Nichael"))

    # def test_generate_mapping_file(self):
    #     with temporary_file_path("mapping.yml") as temp_mapping:
    #         with temp_sqlite_database_url() as database_url:
    #             task = _make_task(
    #                 GenerateDataFromYaml,
    #                 {
    #                     "options": {
    #                         "generator_yaml": sample_yaml,
    #                         "database_url": database_url,
    #                         "generate_mapping_file": temp_mapping,
    #                     }
    #                 },
    #             )
    #             task()
    #         mapping = yaml.safe_load(open(temp_mapping))
    #         assert mapping["Insert Account"]["fields"]

    # def test_use_mapping_file(self):
    #     assert vanilla_mapping_file.exists()
    #     with temp_sqlite_database_url() as database_url:
    #         task = _make_task(
    #             GenerateDataFromYaml,
    #             {
    #                 "options": {
    #                     "generator_yaml": sample_yaml,
    #                     "database_url": database_url,
    #                     "mapping": vanilla_mapping_file,
    #                 }
    #             },
    #         )
    #         task()
    #         self.assertRowsCreated(database_url)

    # def test_num_records(self):
    #     with temp_sqlite_database_url() as database_url:
    #         task = _make_task(
    #             GenerateDataFromYaml,
    #             {
    #                 "options": {
    #                     "generator_yaml": simple_yaml,
    #                     "database_url": database_url,
    #                 }
    #             },
    #         )
    #         task()
    #         assert len(self.assertRowsCreated(database_url)) == 1, len(
    #             self.assertRowsCreated(database_url)
    #         )

    # @mock.patch(
    #     "cumulusci.tasks.bulkdata.generate_and_load_data_from_yaml.GenerateAndLoadDataFromYaml._dataload"
    # )
    # def test_simple_generate_and_load_with_numrecords(self, _dataload):
    #     task = _make_task(s
    #         GenerateAndLoadDataFromYaml,
    #         {
    #             "options": {
    #                 "generator_yaml": simple_yaml,
    #                 "num_records": 11,
    #                 "num_records_tablename": "Account",
    #             }
    #         },
    #     )
    #     task()
    #     assert len(_dataload.mock_calls) == 1

    # @mock.patch(
    #     "cumulusci.tasks.bulkdata.generate_and_load_data_from_yaml.GenerateAndLoadDataFromYaml._dataload"
    # )
    # def test_simple_generate_and_load(self, _dataload):
    #     task = _make_task(
    #         GenerateAndLoadDataFromYaml,
    #         {
    #             "options": {
    #                 "generator_yaml": simple_yaml,
    #                 "num_records": 11,
    #                 "num_records_tablename": "Account",
    #             }
    #         },
    #     )
    #     task()
    #     assert len(_dataload.mock_calls) == 1

    # @mock.patch("cumulusci.tasks.bulkdata.generate_from_yaml.generate_data")
    # def test_exception_handled_cleanly(self, generate_data):
    #     generate_data.side_effect = AssertionError("Foo")
    #     with pytest.raises(AssertionError) as e:
    #         task = _make_task(
    #             GenerateAndLoadDataFromYaml,
    #             {
    #                 "options": {
    #                     "generator_yaml": simple_yaml,
    #                     "num_records": 11,
    #                     "num_records_tablename": "Account",
    #                 }
    #             },
    #         )
    #         task()
    #         assert "Foo" in str(e.value)
    #     assert len(generate_data.mock_calls) == 1

    # @mock.patch(
    #     "cumulusci.tasks.bulkdata.generate_and_load_data_from_yaml.GenerateAndLoadDataFromYaml._dataload"
    # )
    # def test_batching(self, _dataload):
    #     with temp_sqlite_database_url() as database_url:
    #         task = _make_task(
    #             GenerateAndLoadDataFromYaml,
    #             {
    #                 "options": {
    #                     "generator_yaml": simple_yaml,
    #                     "num_records": 14,
    #                     "batch_size": 6,
    #                     "database_url": database_url,
    #                     "num_records_tablename": "Account",
    #                     "data_generation_task": "cumulusci.tasks.bulkdata.generate_from_yaml.GenerateDataFromYaml",
    #                     "reset_oids": False,
    #                 }
    #             },
    #         )
    #         task()
    #         assert len(_dataload.mock_calls) == 3
    #         task = None  # clean up db?

    #         engine = create_engine(database_url)
    #         connection = engine.connect()
    #         records = list(connection.execute("select * from Account"))
    #         connection.close()
    #         assert len(records) == 14 % 6  # leftovers

    # def test_mismatched_options(self):
    #     with pytest.raises(exc.exc.TaskOptionsError) as e:
    #         task = _make_task(
    #             GenerateDataFromYaml,
    #             {"options": {"generator_yaml": sample_yaml, "num_records": 10}},
    #         )
    #         task()
    #     assert "without num_records_tablename" in str(e.value)

    # def test_with_nonexistent_continuation_file(self):
    #     with pytest.raises(exc.TaskOptionsError) as e:
    #         with temp_sqlite_database_url() as database_url:
    #             task = _make_task(
    #                 GenerateDataFromYaml,
    #                 {
    #                     "options": {
    #                         "generator_yaml": sample_yaml,
    #                         "database_url": database_url,
    #                         "mapping": vanilla_mapping_file,
    #                         "continuation_file": "/tmp/foobar/baz/jazz/continuation.yml",
    #                     }
    #                 },
    #             )
    #             task()
    #             rows = self.assertRowsCreated(database_url)
    #             assert dict(rows[0])["id"] == 6

    #     assert "jazz" in str(e.value)
    #     assert "does not exist" in str(e.value)

    # def test_generate_continuation_file(self):
    #     with temporary_file_path("cont.yml") as temp_continuation_file:
    #         with temp_sqlite_database_url() as database_url:
    #             task = _make_task(
    #                 GenerateDataFromYaml,
    #                 {
    #                     "options": {
    #                         "generator_yaml": sample_yaml,
    #                         "database_url": database_url,
    #                         "generate_continuation_file": temp_continuation_file,
    #                     }
    #                 },
    #             )
    #             task()
    #         continuation_file = yaml.safe_load(open(temp_continuation_file))
    #         assert continuation_file  # internals of this file are not important to CumulusCI

    # def _run_snowfakery_and_inspect_mapping(self, **options):
    #     with temporary_file_path("mapping.yml") as temp_mapping:
    #         with temp_sqlite_database_url() as database_url:
    #             task = _make_task(
    #                 GenerateDataFromYaml,
    #                 {
    #                     "options": {
    #                         "database_url": database_url,
    #                         "generate_mapping_file": temp_mapping,
    #                         **options,
    #                     }
    #                 },
    #             )
    #             task()
    #         with open(temp_mapping) as f:
    #             mapping = yaml.safe_load(f)
    #     return mapping

    # def test_generate_mapping_file__loadfile_missing(self):
    #     loading_rules = str(simple_snowfakery_yaml).replace(
    #         ".recipe.yml", "_3.load.yml"
    #     )
    #     with pytest.raises(FileNotFoundError):
    #         self._run_snowfakery_and_inspect_mapping(
    #             generator_yaml=simple_snowfakery_yaml, loading_rules=str(loading_rules)
    #         )
