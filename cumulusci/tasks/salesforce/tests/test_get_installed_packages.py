from cumulusci.tasks.bulkdata.tests.utils import _make_task
from cumulusci.tasks.salesforce.GetInstalledPackages import GetInstalledPackages


class TestGetInstalledPackages:
    def test_run_task(self, caplog):
        task = _make_task(GetInstalledPackages, {})
        task.__class__.__bases__[0]._run_task = lambda *args: "RESULT"
        task()
