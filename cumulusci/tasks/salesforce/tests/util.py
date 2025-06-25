from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from cumulusci.core.config import TaskConfig
from cumulusci.core.config.org_config import OrgConfig
from cumulusci.tests.util import DummyKeychain, create_project_config


def create_task(task_class, options=None, project_config=None, org_config=None):
    "Older create_task helper which does not support orginfo cache."
    if project_config is None:
        project_config = create_project_config("TestRepo", "TestOwner")
    if org_config is None:
        org_config = OrgConfig(
            {
                "instance_url": "https://test.salesforce.com",
                "id": "https://test.salesforce.com/ORG_ID/USER_ID",
                "access_token": "TOKEN",
                "org_id": "ORG_ID",
                "username": "test-cci@example.com",
            },
            "test",
            keychain=DummyKeychain(),
        )
        org_config.refresh_oauth_token = mock.Mock()
    if options is None:
        options = {}
    task_config = TaskConfig({"options": options})
    with mock.patch(
        "cumulusci.core.tasks.BaseSalesforceTask._get_client_name",
        return_value="ccitests",
    ):
        with mock.patch(
            "cumulusci.core.config.org_config.OrgConfig.installed_packages",
            return_value=[],
        ):
            return task_class(project_config, task_config, org_config)


def patch_dir(patch_path, file_path):
    def return_file_path(*args, **kwargs):
        """
        Python 3.11 removed pathlib._Accessor. This replaced a call to
        os.getcwd() with Path.cwd() in Path.absolute(). This means we can have 0
        or 1 arguments.
        """
        return file_path

    directory = Path(file_path)
    directory.mkdir(parents=True, exist_ok=True)
    patch = mock.patch(patch_path, return_file_path)
    patch.start()
    return patch


def create_task_fixture(request):
    "create_task fixture which does support orginfo cache."
    temp_dirs = TemporaryDirectory()
    temp_root = Path(temp_dirs.name)

    to_patch = {
        "pathlib.Path.home": temp_root / "fixture_user_home",
        "pathlib.Path.cwd": temp_root / "fixture_user_home/project",
    }

    pretend_git = temp_root / "fixture_user_home/project/.git"
    pretend_git.mkdir(parents=True)
    patches = [patch_dir(p, d) for p, d in to_patch.items()]

    def fin():
        for patch in patches:
            patch.stop()

        temp_dirs.cleanup()

    request.addfinalizer(fin)

    return create_task
