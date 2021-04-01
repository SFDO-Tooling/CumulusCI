import pytest
import tempfile

from pathlib import Path

from cumulusci.core.keychain import EncryptedFileProjectKeychain
from cumulusci.core.config import (
    BaseProjectConfig,
    OrgConfig,
    ServiceConfig,
    UniversalConfig,
)


@pytest.fixture
def org_config():
    return OrgConfig({"foo": "bar"}, "test")


@pytest.fixture()
def project_config():
    universal_config = UniversalConfig()
    project_config = BaseProjectConfig(universal_config, config={"no_yaml": True})
    project_config.config["services"] = {
        "connected_app": {"attributes": {"test": {"required": True}}},
        "github": {"attributes": {"name": {"required": True}, "password": {}}},
        "not_configured": {"attributes": {"foo": {"required": True}}},
        "devhub": {"attributes": {"foo": {"required": True}}},
    }
    project_config.project__name = "TestProject"
    return project_config


@pytest.fixture
def key():
    return "0123456789123456"


@pytest.fixture
def service_config():
    return ServiceConfig({"name": "bar@baz.biz", "password": "test123"})


@pytest.fixture()
def keychain(project_config, key):
    keychain = EncryptedFileProjectKeychain(project_config, key)
    assert keychain.project_config == project_config
    assert keychain.key == key
    return keychain


class TestEncryptedFileProjectKeychain:
    def _mk_temp_home(self):
        self.tempdir_home = tempfile.mkdtemp()
        global_config_dir = Path(f"{self.tempdir_home}/.cumulusci")
        global_config_dir.mkdir()

    def _mk_temp_project(self):
        self.tempdir_project = tempfile.mkdtemp()
        git_dir = Path(f"{self.tempdir_project}/.git")
        git_dir.mkdir()
        self._create_git_config()

    def _create_git_config(self):
        filename = Path(f"{self.tempdir_project}/.git/config")
        content = (
            '[remote "origin"]\n'
            + f"  url = git@github.com:TestOwner/{self.project_name}"
        )
        self._write_file(filename, content)

    def _write_file(self, filename, content):
        with open(filename, "w") as f:
            f.write(content)

    def test_set_service_github_project(self):
        github_services_dir = Path(f"{self.tempdir_home}/.cumulusci/services/github")
        github_services_dir.mkdir(parents=True)
        self.test_set_service_github(project=True)
