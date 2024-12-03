import pytest

from cumulusci.tasks.bulkdata import LoadData


class TestSelect:
    @pytest.mark.vcr()
    def test_select_similarity_strategy(
        self, create_task, cumulusci_test_repo_root, sf
    ):
        self._test_select_similarity_strategy(
            "rest", create_task, cumulusci_test_repo_root, sf
        )

    @pytest.mark.vcr()
    def test_select_similarity_select_and_insert_strategy(
        self, create_task, cumulusci_test_repo_root, sf
    ):
        self._test_select_similarity_select_and_insert_strategy(
            "rest", create_task, cumulusci_test_repo_root, sf
        )

    @pytest.mark.vcr(allow_playback_repeats=True)
    def test_select_similarity_select_and_insert_strategy_bulk(
        self, create_task, cumulusci_test_repo_root, sf
    ):
        self._test_select_similarity_select_and_insert_strategy_bulk(
            "bulk", create_task, cumulusci_test_repo_root, sf
        )

    @pytest.mark.vcr()
    def test_select_random_strategy(self, create_task, cumulusci_test_repo_root, sf):
        self._test_select_random_strategy(
            "rest", create_task, cumulusci_test_repo_root, sf
        )

    @pytest.mark.vcr()
    def test_select_standard_strategy(self, create_task, cumulusci_test_repo_root, sf):
        self._test_select_standard_strategy(
            "rest", create_task, cumulusci_test_repo_root, sf
        )

    def _test_select_similarity_strategy(
        self, api, create_task, cumulusci_test_repo_root, sf
    ):
        # seed sample data, using a mixture of inserts and
        # upserts-into-empty (which should behave as inserts)
        task = create_task(
            LoadData,
            {
                "sql_path": cumulusci_test_repo_root
                / "datasets/select/similarity_sample.sql",
                "mapping": cumulusci_test_repo_root
                / "datasets/select/similarity_mapping.yml",
                "set_recently_viewed": False,
                "enable_rollback": False,
            },
        )

        task()

        result = task.return_values

        assert (
            str(result)
            == "{'step_results': {'Account': {'sobject': 'Account', 'record_type': None, 'status': <DataOperationStatus.SUCCESS: 'Success'>, 'job_errors': [], 'records_processed': 5, 'total_row_errors': 0}, 'Contact': {'sobject': 'Contact', 'record_type': None, 'status': <DataOperationStatus.SUCCESS: 'Success'>, 'job_errors': [], 'records_processed': 3, 'total_row_errors': 0}}}"
        )

    def _test_select_similarity_select_and_insert_strategy(
        self, api, create_task, cumulusci_test_repo_root, sf
    ):
        # seed sample data, using a mixture of inserts and
        # upserts-into-empty (which should behave as inserts)
        task = create_task(
            LoadData,
            {
                "sql_path": cumulusci_test_repo_root
                / "datasets/select/similarity_select_insert_sample.sql",
                "mapping": cumulusci_test_repo_root
                / "datasets/select/similarity_select_insert_mapping.yml",
                "set_recently_viewed": False,
                "enable_rollback": False,
            },
        )

        task()

        result = task.return_values

        assert (
            str(result)
            == "{'step_results': {'Account': {'sobject': 'Account', 'record_type': None, 'status': <DataOperationStatus.SUCCESS: 'Success'>, 'job_errors': [], 'records_processed': 1, 'total_row_errors': 0}, 'Contact': {'sobject': 'Contact', 'record_type': None, 'status': <DataOperationStatus.SUCCESS: 'Success'>, 'job_errors': [], 'records_processed': 3, 'total_row_errors': 0}, 'Lead': {'sobject': 'Lead', 'record_type': None, 'status': <DataOperationStatus.SUCCESS: 'Success'>, 'job_errors': [], 'records_processed': 2, 'total_row_errors': 0}, 'Event': {'sobject': 'Event', 'record_type': None, 'status': <DataOperationStatus.SUCCESS: 'Success'>, 'job_errors': [], 'records_processed': 3, 'total_row_errors': 0}}}"
        )

    def _test_select_similarity_select_and_insert_strategy_bulk(
        self, api, create_task, cumulusci_test_repo_root, sf
    ):
        # seed sample data, using a mixture of inserts and
        # upserts-into-empty (which should behave as inserts)
        task = create_task(
            LoadData,
            {
                "sql_path": cumulusci_test_repo_root
                / "datasets/select/similarity_select_insert_sample.sql",
                "mapping": cumulusci_test_repo_root
                / "datasets/select/similarity_select_insert_mapping.yml",
                "set_recently_viewed": False,
                "enable_rollback": False,
            },
        )

        task()

        result = task.return_values

        assert (
            str(result)
            == "{'step_results': {'Account': {'sobject': 'Account', 'record_type': None, 'status': <DataOperationStatus.SUCCESS: 'Success'>, 'job_errors': [], 'records_processed': 1, 'total_row_errors': 0}, 'Contact': {'sobject': 'Contact', 'record_type': None, 'status': <DataOperationStatus.SUCCESS: 'Success'>, 'job_errors': [], 'records_processed': 3, 'total_row_errors': 0}, 'Lead': {'sobject': 'Lead', 'record_type': None, 'status': <DataOperationStatus.SUCCESS: 'Success'>, 'job_errors': [], 'records_processed': 2, 'total_row_errors': 0}, 'Event': {'sobject': 'Event', 'record_type': None, 'status': <DataOperationStatus.SUCCESS: 'Success'>, 'job_errors': [], 'records_processed': 3, 'total_row_errors': 0}}}"
        )

    def _test_select_random_strategy(
        self, api, create_task, cumulusci_test_repo_root, sf
    ):
        # seed sample data, using a mixture of inserts and
        # upserts-into-empty (which should behave as inserts)
        task = create_task(
            LoadData,
            {
                "sql_path": cumulusci_test_repo_root
                / "datasets/select/random_sample.sql",
                "mapping": cumulusci_test_repo_root
                / "datasets/select/random_mapping.yml",
                "set_recently_viewed": False,
                "enable_rollback": False,
            },
        )

        task()

        result = task.return_values

        assert (
            str(result)
            == "{'step_results': {'Account': {'sobject': 'Account', 'record_type': None, 'status': <DataOperationStatus.SUCCESS: 'Success'>, 'job_errors': [], 'records_processed': 5, 'total_row_errors': 0}, 'Contact': {'sobject': 'Contact', 'record_type': None, 'status': <DataOperationStatus.SUCCESS: 'Success'>, 'job_errors': [], 'records_processed': 3, 'total_row_errors': 0}}}"
        )

    def _test_select_standard_strategy(
        self, api, create_task, cumulusci_test_repo_root, sf
    ):
        # seed sample data, using a mixture of inserts and
        # upserts-into-empty (which should behave as inserts)
        task = create_task(
            LoadData,
            {
                "sql_path": cumulusci_test_repo_root
                / "datasets/select/random_sample.sql",
                "mapping": cumulusci_test_repo_root
                / "datasets/select/standard_mapping.yml",
                "set_recently_viewed": False,
                "enable_rollback": False,
            },
        )

        task()

        result = task.return_values

        assert (
            str(result)
            == "{'step_results': {'Account': {'sobject': 'Account', 'record_type': None, 'status': <DataOperationStatus.SUCCESS: 'Success'>, 'job_errors': [], 'records_processed': 5, 'total_row_errors': 0}, 'Contact': {'sobject': 'Contact', 'record_type': None, 'status': <DataOperationStatus.SUCCESS: 'Success'>, 'job_errors': [], 'records_processed': 3, 'total_row_errors': 0}}}"
        )
