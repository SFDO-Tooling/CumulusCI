from contextlib import contextmanager
from itertools import cycle
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from unittest import mock

import pytest
from sqlalchemy import create_engine

from cumulusci.core import exceptions as exc
from cumulusci.core.config import OrgConfig
from cumulusci.tasks.bulkdata.delete import DeleteData
from cumulusci.tasks.bulkdata.snowfakery import RunningTotals, Snowfakery
from cumulusci.tasks.bulkdata.tests.utils import _make_task
from cumulusci.utils.parallel.task_worker_queues.tests.test_parallel_worker import (
    DelaySpawner,
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


def call_closure():
    """Simulate a cycle of load results without doing a real load."""
    return_values = cycle(iter(FAKE_LOAD_RESULTS))

    def __call__(self, *args, **kwargs):
        """Like the __call__ of _run_task, but also capture calls
        in a normal mock_values structure."""

        # Manipulating "self" from a mock side-effect is a challenge.
        # So we need a "real function"
        self.return_values = {"step_results": next(return_values)}
        return __call__.mock(*args, **kwargs)

    __call__.mock = mock.Mock()

    return __call__


@pytest.fixture
def mock_load_data(request):
    with mock.patch(
        "cumulusci.tasks.bulkdata.load.LoadData.__call__", call_closure()
    ) as __call__:
        yield __call__.mock


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


@pytest.fixture()
def ensure_accounts(create_task, run_code_without_recording, sf):
    """Delete all accounts and create a certain number of new ones"""

    @contextmanager
    def _ensure_accounts(number_of_accounts):
        def setup(number):
            task = create_task(DeleteData, {"objects": "Entitlement, Account"})
            task()
            for i in range(0, number):
                sf.Account.create({"Name": f"Account {i}"})

        run_code_without_recording(lambda: setup(number_of_accounts))
        yield
        run_code_without_recording(lambda: setup(0))

    return _ensure_accounts


class TestSnowfakery:
    def assertRowsCreated(self, database_url):
        engine = create_engine(database_url)
        connection = engine.connect()
        accounts = connection.execute("select * from Account")
        accounts = list(accounts)
        assert accounts and accounts[0] and accounts[0][1]
        return accounts

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
        assert mock_load_data.mock_calls
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
            {"recipe": sample_yaml, "run_until_recipe_repeated": "7"},
        )
        task()
        # Batch size was 3, so 7 records takes
        # one initial batch plus two parallel batches
        assert len(mock_load_data.mock_calls) == 3, mock_load_data.mock_calls
        # One should be in a sub-process/thread
        assert len(threads_instead_of_processes.mock_calls) == 2

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
            # That will be one "initial" batch plus one "parallel" batch
            task = create_task(
                Snowfakery,
                {"recipe": sample_yaml, "run_until_records_in_org": "Account:16"},
            )
            task.logger = mock.Mock()
            task()
        print(task.logger.mock_calls)
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
        create_task,
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

    def test_record_count(self, snowfakery, mock_load_data):
        task = snowfakery(recipe="datasets/recipe.yml", run_until_recipe_repeated="4")
        with mock.patch.object(task, "logger") as logger:
            task()
        mock_calls_as_string = str(logger.mock_calls)
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

    def test_run_until_conflcting_params(self, snowfakery):
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
    def test_failures_in_subprocesses__last_batch(
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

            def __call__(self):
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

    ## TODO: Test First batch
    ## TODO: Test Intermediate batch

    # def test_vars(self):
    #     with temp_sqlite_database_url() as database_url:
    #         with self.assertWarns(UserWarning):
    #             task = _make_task(
    #                 GenerateDataFromYaml,
    #                 {
    #                     "options": {
    #                         "generator_yaml": sample_yaml,
    #                         "vars": "xyzzy:foo",
    #                         "database_url": database_url,
    #                     }
    #                 },
    #             )
    #             task()
    #             self.assertRowsCreated(database_url)

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
    #     assert "without num_records_tablename" in str(e.exception)

    # def generate_continuation_data(self, fileobj):
    #     g = data_generator_runtime.Globals()
    #     o = data_generator_runtime.ObjectRow(
    #         "Account", {"Name": "Johnston incorporated", "id": 5}
    #     )
    #     g.register_object(o, "The Company", False)
    #     for i in range(0, 5):
    #         # burn through 5 imaginary accounts
    #         g.id_manager.generate_id("Account")
    #     data_generator.save_continuation_yaml(g, fileobj)

    # def test_with_continuation_file(self):
    #     with temp_sqlite_database_url() as database_url:
    #         with temporary_file_path("cont.yml") as continuation_file_path:
    #             with open(continuation_file_path, "w") as continuation_file:
    #                 self.generate_continuation_data(continuation_file)

    #             task = _make_task(
    #                 GenerateDataFromYaml,
    #                 {
    #                     "options": {
    #                         "generator_yaml": sample_yaml,
    #                         "database_url": database_url,
    #                         "mapping": vanilla_mapping_file,
    #                         "continuation_file": continuation_file_path,
    #                     }
    #                 },
    #             )
    #             task()
    #             rows = self.assertRowsCreated(database_url)
    #             assert dict(rows[0])["id"] == 6

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

    #     assert "jazz" in str(e.exception)
    #     assert "does not exist" in str(e.exception)

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

    # def _get_mapping_file(self, **options):
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

    # def test_generate_mapping_file__loadfile__inferred(self):
    #     mapping = self._get_mapping_file(generator_yaml=simple_snowfakery_yaml)

    #     assert mapping["Insert Account"]["api"] == "bulk"
    #     assert mapping["Insert Contact"].get("bulk_mode") is None
    #     assert list(mapping.keys()) == ["Insert Account", "Insert Contact"]

    # def test_generate_mapping_file__loadfile__overridden(self):
    #     loading_rules = str(simple_snowfakery_yaml).replace(
    #         ".recipe.yml", "_2.load.yml"
    #     )
    #     mapping = self._get_mapping_file(
    #         generator_yaml=simple_snowfakery_yaml, loading_rules=str(loading_rules)
    #     )

    #     assert mapping["Insert Account"].get("api") is None
    #     assert mapping["Insert Contact"]["bulk_mode"].lower() == "parallel"
    #     assert list(mapping.keys()) == ["Insert Contact", "Insert Account"]

    # def test_generate_mapping_file__loadfile_multiple_files(self):
    #     loading_rules = (
    #         str(simple_snowfakery_yaml).replace(".recipe.yml", "_2.load.yml")
    #         + ","
    #         + str(simple_snowfakery_yaml).replace(".recipe.yml", ".load.yml")
    #     )
    #     mapping = self._get_mapping_file(
    #         generator_yaml=simple_snowfakery_yaml, loading_rules=str(loading_rules)
    #     )

    #     assert mapping["Insert Account"]["api"] == "bulk"
    #     assert mapping["Insert Contact"]["bulk_mode"].lower() == "parallel"
    #     assert list(mapping.keys()) == ["Insert Contact", "Insert Account"]

    # def test_generate_mapping_file__loadfile_missing(self):
    #     loading_rules = str(simple_snowfakery_yaml).replace(
    #         ".recipe.yml", "_3.load.yml"
    #     )
    #     with pytest.raises(FileNotFoundError):
    #         self._get_mapping_file(
    #             generator_yaml=simple_snowfakery_yaml, loading_rules=str(loading_rules)
    #         )
