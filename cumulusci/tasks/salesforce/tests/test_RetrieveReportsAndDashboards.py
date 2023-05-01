from unittest import mock

import pytest
import responses

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.salesforce import RetrieveReportsAndDashboards
from cumulusci.utils import temporary_dir

from .util import create_task


class TestRetrievePackaged:
    @responses.activate
    def test_get_api(self):
        with temporary_dir() as path:
            task = create_task(
                RetrieveReportsAndDashboards,
                {
                    "path": path,
                    "report_folders": ["Default"],
                    "dashboard_folders": ["Default"],
                    "api_version": "43.0",
                },
            )
            api = mock.Mock(
                return_value={
                    "Report": [{"fullName": "Report1"}],
                    "Dashboard": [{"fullName": "Dashboard1"}],
                }
            )
            task.list_metadata_api_class = mock.Mock(return_value=api)
            task.api_class = mock.Mock()
            task._get_api()
            package_xml = task.api_class.call_args[0][1]
            assert (
                """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>Dashboard1</members>
        <members>Default</members>
        <name>Dashboard</name>
    </types>
    <types>
        <members>Default</members>
        <members>Report1</members>
        <name>Report</name>
    </types>
    <version>43.0</version>
</Package>"""
                == package_xml
            )

    def test_init__missing_options(self):
        with pytest.raises(TaskOptionsError):
            create_task(RetrieveReportsAndDashboards, {"path": None})
