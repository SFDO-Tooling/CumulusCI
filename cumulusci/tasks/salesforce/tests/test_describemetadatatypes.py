from unittest import mock

from cumulusci.tasks.salesforce import DescribeMetadataTypes

from .util import create_task


class TestRetrieveMetadataTypes:
    def test_run_task(self):
        task = create_task(DescribeMetadataTypes)
        task._get_api = mock.Mock()
        task()
        task._get_api.assert_called_once()

    def test_run_task_with_apiversion(self):
        task = create_task(DescribeMetadataTypes, {"api_version": 8.0})
        assert task.options.get("api_version") == 8.0
        task._get_api()
