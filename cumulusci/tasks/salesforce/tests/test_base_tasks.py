import io
import zipfile
from unittest import mock

import pytest

from cumulusci.core.config import OrgConfig, TaskConfig
from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci.tasks.salesforce import (
    BaseRetrieveMetadata,
    BaseSalesforceApiTask,
    BaseSalesforceMetadataApiTask,
    BaseSalesforceTask,
    BaseUninstallMetadata,
)
from cumulusci.tests.util import create_project_config
from cumulusci.utils import temporary_dir

from . import create_task


class TestBaseSalesforceTask:
    def setup_method(self):
        self.project_config = create_project_config()
        self.project_config.keychain = mock.Mock()
        self.project_config.keychain.get_service.side_effect = ServiceNotConfigured
        self.task_config = TaskConfig()
        self.org_config = OrgConfig({}, "test", keychain=self.project_config.keychain)

    def test_run_task(self):
        with mock.patch(
            "cumulusci.tasks.salesforce.BaseSalesforceTask._update_credentials"
        ):
            task = BaseSalesforceTask(
                self.project_config, self.task_config, self.org_config
            )
            with pytest.raises(NotImplementedError):
                task()

    def test_update_credentials(self):
        update_config_called = False

        def update_config(keychain, save=False):
            nonlocal update_config_called
            update_config_called = True
            self.org_config.config["new"] = "new"

        self.org_config.refresh_oauth_token = update_config
        task = BaseSalesforceTask(
            self.project_config, self.task_config, self.org_config
        )
        task._run_task = mock.Mock()
        task()
        assert update_config_called
        self.project_config.keychain.set_org.assert_called_once()


class TestBaseSalesforceApiTask:
    def test_sf_instance(self):
        org_config = OrgConfig(
            {"instance_url": "https://foo/", "access_token": "TOKEN"}, "test"
        )
        task = create_task(BaseSalesforceApiTask, org_config=org_config)
        task._init_task()
        assert not task.sf.sf_instance.endswith("/")


class TestBaseSalesforceMetadataApiTask:
    def test_run_task(self):
        task = create_task(BaseSalesforceMetadataApiTask)
        api = mock.Mock()
        task.api_class = mock.Mock(return_value=api)
        task()
        api.assert_called_once()


class TestBaseRetrieveMetadata:
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
            assert isinstance(result, zipfile.ZipFile)


class TestBaseUninstallMetadata:
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
