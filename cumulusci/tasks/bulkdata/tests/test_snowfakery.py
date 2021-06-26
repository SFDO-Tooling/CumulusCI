from unittest import mock
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import contextmanager
from threading import Thread

import pytest

from sqlalchemy import create_engine

from cumulusci.tasks.bulkdata.snowfakery import UploadStatus, Snowfakery

from cumulusci.tasks.bulkdata.tests.utils import _make_task
from cumulusci.core import exceptions as exc

sample_yaml = Path(__file__).parent / "snowfakery/gen_npsp_standard_objects.yml"


@pytest.fixture
def load_data(request):
    with mock.patch("cumulusci.tasks.bulkdata.load.LoadData.__call__") as y:
        yield y


@pytest.fixture
def threads_instead_of_processes(request):
    with mock.patch(
        "cumulusci.utils.parallel.task_worker_queues.parallel_worker_queue.WorkerQueue.Process",
        wraps=Thread,
    ) as t:
        yield t


@contextmanager
def temporary_file_path(filename):
    with TemporaryDirectory() as tmpdirname:
        path = Path(tmpdirname) / filename
        yield path


class XXXTestUploadStatus:  # FIX THESE TESTS
    def test_upload_status(self):
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


@mock.patch(
    "cumulusci.utils.salesforce.record_count.OrgRecordCounts.start", mock.Mock()
)
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
    def test_simple(self, Process, load_data, create_task_fixture):
        task = create_task_fixture(
            Snowfakery,
            {
                "recipe": sample_yaml,
            },
        )
        task()
        assert load_data.mock_calls
        # should not be called for a simple one-rep load
        assert not Process.mock_calls

    @mock.patch("cumulusci.tasks.bulkdata.snowfakery.BASE_BATCH_SIZE", 3)
    def test_small(self, load_data, threads_instead_of_processes, create_task_fixture):
        task = create_task_fixture(
            Snowfakery,
            {"recipe": sample_yaml, "run_until_recipe_repeated": "6"},
        )
        task()
        # Batch size was 3, so 6 records takes two batches
        assert len(load_data.mock_calls) == 2
        # One should be in a sub-process/thread
        assert len(threads_instead_of_processes.mock_calls) == 1

    @mock.patch("cumulusci.tasks.bulkdata.snowfakery.BASE_BATCH_SIZE", 3)
    def test_multi_part(
        self, threads_instead_of_processes, load_data, create_task_fixture
    ):
        task = create_task_fixture(
            Snowfakery,
            {"recipe": sample_yaml, "run_until_recipe_repeated": 15},
        )
        task()
        assert len(load_data.mock_calls) > 3  # depends on the details of the tuning
        assert (
            len(threads_instead_of_processes.mock_calls)
            == len(load_data.mock_calls) - 1
        )

    @mock.patch(
        "cumulusci.utils.parallel.task_worker_queues.parallel_worker_queue.WorkerQueue.Process",
    )
    def test_run_until_loaded(self, create_subprocess, load_data, create_task_fixture):
        task = create_task_fixture(
            Snowfakery,
            {"recipe": sample_yaml, "run_until_records_loaded": "Account:10"},
        )
        task()
        assert load_data.mock_calls
        # should not be called for a simple one-rep load
        assert not create_subprocess.mock_calls

    @mock.patch("cumulusci.tasks.bulkdata.snowfakery.BASE_BATCH_SIZE", 3)
    def test_run_until_loaded_2_parts(
        self, threads_instead_of_processes, load_data, create_task_fixture
    ):
        task = create_task_fixture(
            Snowfakery,
            {"recipe": sample_yaml, "run_until_records_loaded": "Account:6"},
        )
        task()
        assert len(load_data.mock_calls) == 2
        assert len(threads_instead_of_processes.mock_calls) == 1

    # def test_inaccessible_generator_yaml(self):
    #     with pytest.raises(exc.exc.TaskOptionsError):
    #         task = _make_task(
    #             GenerateDataFromYaml,
    #             {
    #                 "options": {
    #                     "generator_yaml": sample_yaml / "junk",
    #                     "num_records": 10,
    #                     "num_records_tablename": "Account",
    #                 }
    #             },
    #         )
    #         task()

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
