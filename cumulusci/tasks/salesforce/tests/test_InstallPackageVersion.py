import mock
import responses
import unittest

from cumulusci.salesforce_api.exceptions import MetadataApiError
from cumulusci.salesforce_api.tests.metadata_test_strings import deploy_result
from cumulusci.tasks.salesforce import InstallPackageVersion
from cumulusci.tests.util import create_project_config
from .util import create_task


class TestInstallPackageVersion(unittest.TestCase):
    @mock.patch("time.sleep", mock.Mock())
    def test_run_task_with_retry(self):
        project_config = create_project_config()
        project_config.get_latest_version = mock.Mock(return_value="1.0")
        project_config.config["project"]["package"]["namespace"] = "ns"
        task = create_task(InstallPackageVersion, {"version": "latest"}, project_config)
        not_yet = MetadataApiError("This package is not yet available", None)
        api = mock.Mock(side_effect=[not_yet, None])
        task.api_class = mock.Mock(return_value=api)
        task()
        self.assertEqual(2, api.call_count)

    def test_run_task__latest_beta(self):
        project_config = create_project_config()
        project_config.get_latest_version = mock.Mock(return_value="1.0 (Beta 1)")
        project_config.config["project"]["package"]["namespace"] = "ns"
        task = create_task(
            InstallPackageVersion, {"version": "latest_beta"}, project_config
        )
        api = mock.Mock()
        task.api_class = mock.Mock(return_value=api)
        task()
        api.assert_called_once()
