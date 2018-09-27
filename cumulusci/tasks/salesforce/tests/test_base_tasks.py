import io
import mock
import unittest
import zipfile

from cumulusci.core.config import OrgConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci.tasks.salesforce import BaseRetrieveMetadata
from cumulusci.tasks.salesforce import BaseSalesforceTask
from cumulusci.tasks.salesforce import BaseSalesforceMetadataApiTask
from cumulusci.tasks.salesforce import BaseUninstallMetadata
from cumulusci.tests.util import create_project_config
from cumulusci.utils import temporary_dir
from . import create_task


class TestBaseSalesforceTask(unittest.TestCase):
    def setUp(self):
        self.project_config = create_project_config()
        self.project_config.keychain = mock.Mock()
        self.project_config.keychain.get_service.side_effect = ServiceNotConfigured
        self.task_config = TaskConfig()
        self.org_config = OrgConfig({}, "test")

    def test_run_task(self):
        with mock.patch(
            "cumulusci.tasks.salesforce.BaseSalesforceTask._update_credentials"
        ):
            task = BaseSalesforceTask(
                self.project_config, self.task_config, self.org_config
            )
            with self.assertRaises(NotImplementedError):
                task()

    def test_update_credentials(self):
        def update_config(keychain):
            self.org_config.config["new"] = "new"

        self.org_config.refresh_oauth_token = update_config
        task = BaseSalesforceTask(
            self.project_config, self.task_config, self.org_config
        )
        self.project_config.keychain.set_org.assert_called_once()


class TestBaseSalesforceMetadataApiTask(unittest.TestCase):
    def test_run_task(self):
        task = create_task(BaseSalesforceMetadataApiTask)
        api = mock.Mock()
        task.api_class = mock.Mock(return_value=api)
        task()
        api.assert_called_once()


class TestBaseRetrieveMetadata(unittest.TestCase):
    def test_process_namespace(self):
        with temporary_dir() as path:
            task = create_task(
                BaseRetrieveMetadata,
                {
                    "path": path,
                    "namespace_inject": "ns",
                    "namespace_tokenize": "ns",
                    "namespace_strip": "ns",
                },
            )
            zf = zipfile.ZipFile(io.BytesIO(), "w")
            result = task._process_namespace(zf)
            self.assertIsInstance(result, zipfile.ZipFile)


class TestBaseUninstallMetadata(unittest.TestCase):
    def test_get_api(self):
        with temporary_dir() as path:
            task = create_task(BaseUninstallMetadata, {"path": path})
            api = mock.Mock()
            task._get_destructive_changes = mock.Mock(return_value="asdf")
            task.api_class = mock.Mock(return_value=api)
            task()
            api.assert_called_once()

    def test_get_api_no_changes(self):
        with temporary_dir() as path:
            task = create_task(BaseUninstallMetadata, {"path": path})
            api = mock.Mock()
            task._get_destructive_changes = mock.Mock(return_value=None)
            task.api_class = mock.Mock(return_value=api)
            task()
            api.assert_not_called()
