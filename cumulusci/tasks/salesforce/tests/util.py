import mock
import unittest

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import TaskConfig
from cumulusci.tests.util import get_base_config


class SalesforceTaskTestCase(unittest.TestCase):

    task_class = None

    def create_project_config(self):
        base_config = get_base_config()
        project_config = BaseProjectConfig(BaseGlobalConfig(), base_config)
        return project_config

    def create_task(self, options=None, project_config=None, org_config=None):
        if project_config is None:
            project_config = self.create_project_config()
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
            return self.task_class(project_config, task_config, org_config)
