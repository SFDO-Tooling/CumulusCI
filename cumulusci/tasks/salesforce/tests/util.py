from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import mock

import pytest

from cumulusci.core.config import OrgConfig
from cumulusci.core.config import TaskConfig
from cumulusci.tests.util import create_project_config, DummyKeychain


def create_task(task_class, options=None, project_config=None, org_config=None):
    "Older create_task helper which does not support orginfo cache."
    if project_config is None:
        project_config = create_project_config("TestRepo", "TestOwner")
    if org_config is None:
        org_config = OrgConfig(
            {
                "instance_url": "https://test.salesforce.com",
                "access_token": "TOKEN",
                "org_id": "ORG_ID",
                "username": "test-cci@example.com",
            },
            "test",
            keychain=DummyKeychain,
        )
        org_config.refresh_oauth_token = mock.Mock()
    if options is None:
        options = {}
    task_config = TaskConfig({"options": options})
    with mock.patch(
        "cumulusci.tasks.salesforce.BaseSalesforceTask._get_client_name",
        return_value="ccitests",
    ):
        return task_class(project_config, task_config, org_config)


def patch_dir(patch_path, file_path):
    directory = Path(file_path)
    directory.mkdir(parents=True, exist_ok=True)
    patch = mock.patch(patch_path, file_path)
    patch.start()
    return patch


@pytest.fixture(scope="function")
def create_task_fixture(request):
    "create_task fixture which does support orginfo cache."
    temp_dirs = TemporaryDirectory()
    temp_root = Path(temp_dirs.name)

    to_patch = {
        "cumulusci.core.config.UniversalConfig.cumulusci_config_dir": temp_root
        / "fixture_userhome/.cumulusci",
        "cumulusci.tests.util.DummyKeychain.config_local_dir": temp_root
        / "fixture_userhome/.cumulusci",
        "cumulusci.core.config.project_config.BaseProjectConfig.project_cache_dir": temp_root
        / "fixture_userhome/project_home/.cci",
        "cumulusci.tests.util.DummyKeychain.project_cache_dir": temp_root
        / "fixture_userhome/project_home/.cci",
    }

    patches = [patch_dir(p, d) for p, d in to_patch.items()]
    for patch in patches:
        patch.start()

    def fin():
        for patch in patches:
            patch.stop()

        temp_dirs.cleanup()

    request.addfinalizer(fin)

    return create_task
