import mock
import unittest

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import TaskConfig
from cumulusci.tests.util import create_project_config


def create_task(task_class, options=None, project_config=None, org_config=None):
    if project_config is None:
        project_config = create_project_config("TestRepo", "TestOwner")
    if org_config is None:
        org_config = OrgConfig(
            {
                "instance_url": "https://test.salesforce.com",
                "access_token": "TOKEN",
                "org_id": "ORG_ID",
            },
            "test",
        )
    if options is None:
        options = {}
    task_config = TaskConfig({"options": options})
    with mock.patch(
        "cumulusci.tasks.salesforce.BaseSalesforceTask._update_credentials"
    ), mock.patch(
        "cumulusci.tasks.salesforce.BaseSalesforceTask._get_client_name",
        return_value="ccitests",
    ):
        return task_class(project_config, task_config, org_config)
