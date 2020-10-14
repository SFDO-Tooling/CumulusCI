from unittest import mock

from cumulusci.tasks.preflight.packages import GetInstalledPackages
from cumulusci.tasks.salesforce.tests.util import create_task


class TestGetInstalledPackages:
    @mock.patch(
        "cumulusci.salesforce_api.metadata.ApiRetrieveInstalledPackages.__call__"
    )
    def test_run_task(self, api):
        task = create_task(GetInstalledPackages)
        task()
        api.assert_called_once()
