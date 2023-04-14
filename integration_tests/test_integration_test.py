from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from cumulusci.tasks.preflight.packages import GetInstalledPackages
from cumulusci.tasks.salesforce import SOQLQuery


class TestFoo:
    def test_sf(self, sf):
        assert sf.query("select Id from Contact")

    @pytest.mark.xfail()
    def test_create_query(self, create_task):
        with TemporaryDirectory() as t:
            tempfile = Path(t) / "tempfile.csv"
            task = create_task(
                SOQLQuery,
                {
                    "object": "Contact",
                    "result_file": str(tempfile),
                    "query": "Select Id from Contact limit 10",
                },
            )
            task()

    def test_get_installed_packages(self, create_task):
        task = create_task(GetInstalledPackages, {})
        task()
        installed_packages = task.return_values
        assert isinstance(installed_packages, dict)
