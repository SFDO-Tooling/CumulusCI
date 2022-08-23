import io
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import pytest
import yaml

from cumulusci.core.config import (
    BaseProjectConfig,
    ScratchOrgConfig,
    ServiceConfig,
    SfdxOrgConfig,
    UniversalConfig,
)
from cumulusci.core.exceptions import (
    NotInProject,
    ProjectConfigNotFound,
    ScratchOrgException,
    ServiceNotConfigured,
    SfdxOrgException,
)
from cumulusci.utils import cd, temporary_dir

__location__ = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture
def scratch_def_file():
    with temporary_dir():
        with open("tmp.json", "w") as f:
            f.write("{}")
        yield


@mock.patch("pathlib.Path.home")
class TestUniversalConfig:
    def setup_method(self):
        self.tempdir_home = Path(tempfile.mkdtemp())

    def teardown_method(self):
        shutil.rmtree(self.tempdir_home)

    def _create_universal_config_local(self, content):
        global_config_dir = os.path.join(self.tempdir_home, ".cumulusci")
        os.makedirs(global_config_dir)
        filename = os.path.join(global_config_dir, UniversalConfig.config_filename)
        self._write_file(filename, content)

    def _write_file(self, filename, content):
        with open(filename, "w") as f:
            f.write(content)

    def test_load_universal_config_no_local(self, mock_class):
        mock_class.return_value = self.tempdir_home
        # clear cache
        UniversalConfig.config = None
        config = UniversalConfig()
        with open(__location__ + "/../../../cumulusci.yml", "r") as f_expected_config:
            expected_config = yaml.safe_load(f_expected_config)
        assert config.config == expected_config

    def test_load_universal_config_empty_local(self, mock_class):
        self._create_universal_config_local("")
        # clear cache
        UniversalConfig.config = None
        mock_class.return_value = self.tempdir_home
        config = UniversalConfig()
        with open(__location__ + "/../../../cumulusci.yml", "r") as f_expected_config:
            expected_config = yaml.safe_load(f_expected_config)
        assert config.config == expected_config

    def test_load_universal_config_with_local(self, mock_class):
        local_yaml = "tasks:\n    newtesttask:\n        description: test description"
        self._create_universal_config_local(local_yaml)
        mock_class.return_value = self.tempdir_home

        # clear cache
        UniversalConfig.config = None

        config = UniversalConfig()
        with open(__location__ + "/../../../cumulusci.yml", "r") as f_expected_config:
            expected_config = yaml.safe_load(f_expected_config)
        expected_config["tasks"]["newtesttask"] = {}
        expected_config["tasks"]["newtesttask"]["description"] = "test description"
        assert config.config == expected_config


@mock.patch("pathlib.Path.home")
class TestBaseProjectConfig:
    def setup_method(self):
        self.tempdir_home = Path(tempfile.mkdtemp())
        self.tempdir_project = tempfile.mkdtemp()
        self.project_name = "TestRepo"
        self.current_commit = "abcdefg1234567890"
        self.current_branch = "main"

    def teardown_method(self):
        shutil.rmtree(self.tempdir_home)
        shutil.rmtree(self.tempdir_project)

    def _create_git_config(self):

        filename = os.path.join(self.tempdir_project, ".git", "config")
        content = '[remote "origin"]\n' + "  url = git@github.com:TestOwner/{}".format(
            self.project_name
        )
        self._write_file(filename, content)

        filename = os.path.join(self.tempdir_project, ".git", "HEAD")
        content = "ref: refs/heads/{}".format(self.current_branch)
        self._write_file(filename, content)

        dirname = os.path.join(self.tempdir_project, ".git", "refs", "heads")
        os.makedirs(dirname)
        filename = os.path.join(dirname, "main")
        content = self.current_commit
        self._write_file(filename, content)

    def _create_universal_config_local(self, content):
        global_config_dir = os.path.join(self.tempdir_home, ".cumulusci")
        os.makedirs(global_config_dir)
        filename = os.path.join(global_config_dir, UniversalConfig.config_filename)
        self._write_file(filename, content)

    def _create_project_config(self):
        filename = os.path.join(self.tempdir_project, BaseProjectConfig.config_filename)
        content = (
            "project:\n"
            + "    name: TestRepo\n"
            + "    package:\n"
            + "        name: TestProject\n"
            + "        namespace: testproject\n"
        )
        self._write_file(filename, content)

    def _create_project_config_local(self, content):
        project_local_dir = os.path.join(
            self.tempdir_home, ".cumulusci", self.project_name
        )
        os.makedirs(project_local_dir)
        filename = os.path.join(project_local_dir, BaseProjectConfig.config_filename)
        self._write_file(filename, content)

    def _write_file(self, filename, content):
        with open(filename, "w") as f:
            f.write(content)

    def test_load_project_config_not_repo(self, mock_class):
        mock_class.return_value = self.tempdir_home
        with cd(self.tempdir_project):
            universal_config = UniversalConfig()
            with pytest.raises(NotInProject):
                BaseProjectConfig(universal_config)

    def test_load_project_config_no_config(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, ".git"))
        with cd(self.tempdir_project):
            universal_config = UniversalConfig()
            with pytest.raises(ProjectConfigNotFound):
                BaseProjectConfig(universal_config)

    def test_load_project_config_empty_config(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, ".git"))
        self._create_git_config()
        # create empty project config file
        filename = os.path.join(self.tempdir_project, BaseProjectConfig.config_filename)
        content = ""
        self._write_file(filename, content)

        with cd(self.tempdir_project):
            universal_config = UniversalConfig()
            config = BaseProjectConfig(universal_config)
            assert config.config_project == {}

    def test_load_project_config_valid_config(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, ".git"))
        self._create_git_config()
        local_yaml = "tasks:\n    newtesttask:\n        description: test description"
        self._create_universal_config_local(local_yaml)

        # create valid project config file
        self._create_project_config()

        with cd(self.tempdir_project):
            universal_config = UniversalConfig()
            config = BaseProjectConfig(universal_config)
            assert config.project__package__name == "TestProject"
            assert config.project__package__namespace == "testproject"

    def test_repo_owner(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, ".git"))
        self._create_git_config()

        # create valid project config file
        self._create_project_config()

        with cd(self.tempdir_project):
            universal_config = UniversalConfig()
            config = BaseProjectConfig(universal_config)
            assert config.repo_owner == "TestOwner"

    def test_repo_branch(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, ".git"))
        self._create_git_config()

        # create valid project config file
        self._create_project_config()

        with cd(self.tempdir_project):
            universal_config = UniversalConfig()
            config = BaseProjectConfig(universal_config)
            assert config.repo_branch == self.current_branch

    def test_repo_commit(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, ".git"))
        self._create_git_config()

        # create valid project config file
        self._create_project_config()

        with cd(self.tempdir_project):
            universal_config = UniversalConfig()
            config = BaseProjectConfig(universal_config)
            assert config.repo_commit == self.current_commit

    def test_load_project_config_local(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, ".git"))
        self._create_git_config()

        # create valid project config file
        self._create_project_config()

        # create local project config file
        content = "project:\n" + "    package:\n" + "        api_version: 45.0\n"
        self._create_project_config_local(content)

        with cd(self.tempdir_project):
            universal_config = UniversalConfig()
            config = BaseProjectConfig(universal_config)
            assert config.config_project_local != {}
            assert config.project__package__api_version == 45.0

    def test_load_additional_yaml(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, ".git"))
        self._create_git_config()

        # create valid project config file
        self._create_project_config()

        # create local project config file
        content = "project:\n" + "    package:\n" + "        api_version: 45.0\n"

        with cd(self.tempdir_project):
            universal_config = UniversalConfig()
            config = BaseProjectConfig(universal_config, additional_yaml=content)
            assert config.config_additional_yaml != {}
            assert config.project__package__api_version == 45.0


@mock.patch("sarge.Command")
class TestScratchOrgConfig:
    def test_scratch_info(self, Command):
        result = b"""{
    "result": {
        "instanceUrl": "url",
        "accessToken": "access!token",
        "username": "username",
        "password": "password",
        "createdDate": "1970-01-01T00:00:00Z",
        "expirationDate": "1970-01-08"
    }
}"""
        Command.return_value = mock.Mock(
            stderr=io.BytesIO(b""), stdout=io.BytesIO(result), returncode=0
        )

        config = ScratchOrgConfig({"username": "test", "created": True}, "test")
        info = config.scratch_info

        assert info == {
            "access_token": "access!token",
            "instance_url": "url",
            "org_id": "access",
            "password": "password",
            "username": "username",
            "created_date": "1970-01-01T00:00:00Z",
            "expiration_date": "1970-01-08",
        }
        assert info is config._sfdx_info
        for key in (
            "access_token",
            "instance_url",
            "org_id",
            "password",
            "username",
        ):
            assert key in config.config
        assert config._sfdx_info_date

    def test_scratch_info_memoized(self, Command):
        config = ScratchOrgConfig({"username": "test", "created": True}, "test")
        config._sfdx_info = _marker = object()
        info = config.scratch_info
        assert info is _marker

    def test_sfdx_info_non_json_response(self, Command):
        Command.return_value = mock.Mock(
            stderr=io.BytesIO(b""), stdout=io.BytesIO(b"<html></html>"), returncode=0
        )

        config = SfdxOrgConfig({"username": "test", "created": True}, "test")
        with pytest.raises(SfdxOrgException):
            config.sfdx_info

    def test_scratch_info_command_error(self, Command):
        Command.return_value = mock.Mock(
            stderr=io.BytesIO(b"error"), stdout=io.BytesIO(b"out"), returncode=1
        )

        config = ScratchOrgConfig(
            {"username": "test", "email_address": "test@example.com", "created": True},
            "test",
        )

        with pytest.raises(SfdxOrgException, match="error"):
            config.scratch_info

    def test_scratch_info_username_not_found(self, Command):
        Command.return_value = mock.Mock(
            stderr=io.BytesIO(b"error"), stdout=io.BytesIO(b"out"), returncode=0
        )

        config = ScratchOrgConfig(
            {"config_file": "tmp.json", "email_address": "test@example.com"}, "test"
        )

        with temporary_dir():
            with open("tmp.json", "w") as f:
                f.write("{}")
            with pytest.raises(ScratchOrgException):
                config.scratch_info

    def test_access_token(self, Command):
        config = ScratchOrgConfig({}, "test")
        _marker = object()
        config._sfdx_info = {"access_token": _marker}
        assert config.access_token is _marker

    def test_get_access_token(self, Command):
        """Verify that get_access_token calls out to sfdx"""
        sf = mock.Mock()
        sf.query_all.return_value = {"records": [{"Username": "whatever@example.com"}]}

        sfdx_response = mock.Mock(returncode=0)
        sfdx_response.stdout_text.read.return_value = (
            '{"result": {"accessToken": "the-token"}}'
        )
        sfdx = mock.Mock(return_value=sfdx_response)

        config = ScratchOrgConfig({}, "test")
        with mock.patch("cumulusci.core.config.OrgConfig.salesforce_client", sf):
            with mock.patch("cumulusci.core.config.sfdx_org_config.sfdx", sfdx):
                access_token = config.get_access_token(alias="dadvisor")
                sfdx.assert_called_once_with(
                    "force:org:display --targetusername=whatever@example.com --json"
                )
                assert access_token == "the-token"

    def test_get_access_token__default(self, Command):
        """Verify that with no args, get_access_token returns the default token"""
        config = ScratchOrgConfig({}, "test")
        _marker = object()
        config._sfdx_info = {"access_token": _marker}
        access_token = config.get_access_token()
        assert access_token is _marker

    def test_get_access_token__unknown_user(self, Command):
        sf = mock.Mock()
        sf.query_all.return_value = {"records": []}

        config = ScratchOrgConfig({}, "test")

        with mock.patch("cumulusci.core.config.OrgConfig.salesforce_client", sf):
            with pytest.raises(
                SfdxOrgException,
                match="Couldn't find a username for the specified user",
            ):
                config.get_access_token(alias="dadvisor")

    def test_get_access_token__multiple_users(self, Command):
        sf = mock.Mock()
        sf.query_all.return_value = {
            "records": [
                {"Username": "test1@example.com"},
                {"Username": "test2@example.com"},
            ]
        }

        config = ScratchOrgConfig({}, "test")

        with mock.patch("cumulusci.core.config.OrgConfig.salesforce_client", sf):
            with pytest.raises(
                SfdxOrgException,
                match="More than one user matched the search critiera.",
            ):
                config.get_access_token(alias="dadvisor")

    def test_get_access_token__no_access_token(self, Command):
        sf = mock.Mock()
        sf.query_all.return_value = {"records": [{"Username": "whatever@example.com"}]}

        sfdx_response = mock.Mock(returncode=1)
        sfdx_response.stdout_text.read.return_value = '{"message": "blah blah..."}'
        sfdx = mock.Mock(return_value=sfdx_response)

        config = ScratchOrgConfig({}, "test")
        with mock.patch("cumulusci.core.config.OrgConfig.salesforce_client", sf):
            with mock.patch("cumulusci.core.config.sfdx_org_config.sfdx", sfdx):
                exception = (
                    "Unable to find access token for whatever@example.com\nblah blah..."
                )
                with pytest.raises(SfdxOrgException, match=exception):
                    config.get_access_token(alias="dadvisor")

    def test_instance_url(self, Command):
        config = ScratchOrgConfig({}, "test")
        _marker = object()
        config._sfdx_info = {"instance_url": _marker}
        assert config.instance_url is _marker

    def test_org_id_from_config(self, Command):
        config = ScratchOrgConfig({"org_id": "test"}, "test")
        assert config.org_id == "test"

    def test_org_id_from_sfdx_info(self, Command):
        config = ScratchOrgConfig({}, "test")
        _marker = object()
        config._sfdx_info = {"org_id": _marker}
        assert config.org_id is _marker

    def test_user_id_from_config(self, Command):
        config = ScratchOrgConfig({"user_id": "test"}, "test")
        assert config.user_id == "test"

    def test_user_id_from_org(self, Command):
        sf = mock.Mock()
        sf.query_all.return_value = {"records": [{"Id": "test"}]}

        config = ScratchOrgConfig({"username": "test_username"}, "test")
        config._sfdx_info = {
            "instance_url": "test_instance",
            "access_token": "token",
        }
        with mock.patch("cumulusci.core.config.OrgConfig.salesforce_client", sf):
            assert config.user_id == "test"

    def test_username_from_sfdx_info(self, Command):
        config = ScratchOrgConfig({}, "test")
        _marker = object()
        config._sfdx_info = {"username": _marker}
        assert config.username is _marker

    def test_password_from_config(self, Command):
        config = ScratchOrgConfig({"password": "test"}, "test")
        assert config.password == "test"

    def test_password_from_sfdx_info(self, Command):
        config = ScratchOrgConfig({}, "test")
        _marker = object()
        config._sfdx_info = {"password": _marker}
        assert config.password is _marker

    def test_email_address_from_config(self, Command):
        config = ScratchOrgConfig({"email_address": "test@example.com"}, "test")

        assert config.email_address == "test@example.com"
        Command.return_value.assert_not_called()

    def test_email_address_from_git(self, Command):
        config = ScratchOrgConfig({}, "test")
        Command.return_value = p = mock.Mock(
            stdout=io.BytesIO(b"test@example.com"), stderr=io.BytesIO(b""), returncode=0
        )

        assert config.email_address == "test@example.com"
        config.email_address  # Make sure value is cached
        p.run.assert_called_once()

    def test_email_address_not_present(self, Command):
        config = ScratchOrgConfig({}, "test")
        Command.return_value = p = mock.Mock(
            stdout=io.BytesIO(b""), stderr=io.BytesIO(b""), returncode=0
        )

        assert config.email_address is None
        p.run.assert_called_once()

    def test_days(self, Command):
        config = ScratchOrgConfig({"days": 2}, "test")
        assert config.days == 2

    def test_days_default(self, Command):
        config = ScratchOrgConfig({}, "test")
        assert config.days == 1

    def test_format_days(self, Command):
        config = ScratchOrgConfig({"days": 2}, "test")
        assert config.format_org_days() == "2"
        now = datetime.now()
        config.date_created = now
        assert config.format_org_days() == "1/2"
        config.date_created = now - timedelta(days=3)
        assert config.format_org_days() == "2"

    def test_expired(self, Command):
        config = ScratchOrgConfig({"days": 1}, "test")
        now = datetime.now()
        config.date_created = now
        assert not config.expired
        config.date_created = now - timedelta(days=2)
        assert config.expired

    def test_expires(self, Command):
        config = ScratchOrgConfig({"days": 1}, "test")
        now = datetime.now()
        config.date_created = now
        assert config.expires == now + timedelta(days=1)

        config = ScratchOrgConfig({"days": 1}, "test")
        config.date_created = None
        assert config.expires is None

    def test_days_alive(self, Command):
        config = ScratchOrgConfig({}, "test")
        config.date_created = datetime.now()
        assert config.days_alive == 1

    def test_active(self, Command):
        config = ScratchOrgConfig({}, "test")
        config.date_created = None
        assert not config.active

        config = ScratchOrgConfig({}, "test")
        config.date_created = datetime.now()
        assert config.active

        config = ScratchOrgConfig({}, "test")
        config.date_created = datetime.now() - timedelta(days=10)
        assert not config.active

    def test_create_org(self, Command):
        out = b"""{
                "status": 0,
                "result": {
                    "orgId": "ORG_ID",
                    "username": "USERNAME"
                }
                }
                """
        Command.return_value = p = mock.Mock(
            stdout=io.BytesIO(out), stderr=io.BytesIO(b""), returncode=0
        )

        config = ScratchOrgConfig(
            {
                "config_file": "tmp.json",
                "set_password": True,
                "email_address": "test@example.com",
            },
            "test",
        )
        config.generate_password = mock.Mock()
        with temporary_dir():
            with open("tmp.json", "w") as f:
                f.write("{}")

            config.create_org()

        p.run.assert_called_once()
        assert config.config["org_id"] == "ORG_ID"
        assert config.config["username"] == "USERNAME"
        assert "date_created" in config.config
        config.generate_password.assert_called_once()
        assert config.config["created"]
        assert config.scratch_org_type == "workspace"

    def test_create_org_no_config_file(self, Command):
        config = ScratchOrgConfig({}, "test")
        with pytest.raises(ScratchOrgException, match="missing a config_file"):
            config.create_org()
        Command.assert_not_called()

    def test_create_org_command_error(self, Command):
        Command.return_value = mock.Mock(
            stdout=io.BytesIO(b""), stderr=io.BytesIO(b"scratcherror"), returncode=1
        )

        config = ScratchOrgConfig(
            {"config_file": "tmp.json", "email_address": "test@example.com"}, "test"
        )
        with temporary_dir():
            with open("tmp.json", "w") as f:
                f.write("{}")

            with pytest.raises(ScratchOrgException) as e:
                config.create_org()
            assert "scratcherror" in str(e.value)

    def test_generate_password(self, Command):
        p = mock.Mock(
            stderr=io.BytesIO(b"error"), stdout=io.BytesIO(b"out"), returncode=0
        )
        Command.return_value = p

        config = ScratchOrgConfig({"username": "test"}, "test")
        config.generate_password()

        p.run.assert_called_once()

    def test_generate_password_failed(self, Command):
        p = mock.Mock()
        p.stderr = io.BytesIO(b"error")
        p.stdout = io.BytesIO(b"out")
        p.returncode = 1
        Command.return_value = p

        config = ScratchOrgConfig({"username": "test"}, "test")
        config.logger = mock.Mock()
        config.generate_password()

        config.logger.warning.assert_called_once()

    def test_generate_password_skips_if_failed(self, Command):
        config = ScratchOrgConfig({"username": "test"}, "test")
        config.password_failed = True
        config.generate_password()
        Command.assert_not_called()

    def test_can_delete(self, Command):
        config = ScratchOrgConfig({"date_created": datetime.now()}, "test")
        assert config.can_delete()

    def test_delete_org(self, Command):
        Command.return_value = mock.Mock(
            stdout=io.BytesIO(b"info"), stderr=io.BytesIO(b""), returncode=0
        )

        config = ScratchOrgConfig(
            {"username": "test", "created": True, "instance_url": "https://blah"},
            "test",
        )
        config.keychain = mock.Mock()
        config.delete_org()

        assert not config.config.get("instance_url")
        assert not config.config["created"]
        assert config.config["username"] is None

    def test_delete_org_not_created(self, Command):
        config = ScratchOrgConfig({"created": False}, "test")
        config.delete_org()
        Command.assert_not_called()

    def test_delete_org_error(self, Command):
        Command.return_value = mock.Mock(
            stdout=io.BytesIO(b"An error occurred deleting this org"),
            stderr=io.BytesIO(b""),
            returncode=1,
        )

        config = ScratchOrgConfig({"username": "test", "created": True}, "test")
        with pytest.raises(ScratchOrgException):
            config.delete_org()

    def test_force_refresh_oauth_token(self, Command):
        Command.return_value = p = mock.Mock(
            stdout=io.BytesIO(b""), stderr=io.BytesIO(b""), returncode=0
        )

        config = ScratchOrgConfig({"username": "test"}, "test")
        config.force_refresh_oauth_token()

        p.run.assert_called_once()

    def test_force_refresh_oauth_token_error(self, Command):
        Command.return_value = mock.Mock(
            stdout=io.BytesIO(b"error"), stderr=io.BytesIO(b""), returncode=1
        )

        config = ScratchOrgConfig({"username": "test"}, "test")
        with pytest.raises(SfdxOrgException):
            config.force_refresh_oauth_token()

    def test_refresh_oauth_token(self, Command):
        result = b"""{
    "result": {
        "instanceUrl": "url",
        "accessToken": "access!token",
        "username": "username",
        "password": "password",
        "createdDate": "1970-01-01T:00:00:00Z",
        "expirationDate": "1970-01-08"
    }
}"""
        Command.return_value = mock.Mock(
            stdout=io.BytesIO(result), stderr=io.BytesIO(b""), returncode=0
        )

        config = ScratchOrgConfig({"username": "test", "created": True}, "test")
        config._sfdx_info = {}
        config._sfdx_info_date = datetime.now() - timedelta(days=1)
        config.force_refresh_oauth_token = mock.Mock()
        config._load_orginfo = mock.Mock()

        config.refresh_oauth_token(keychain=None)

        config.force_refresh_oauth_token.assert_called_once()
        assert config._sfdx_info

    def test_choose_devhub(self, Command):
        mock_keychain = mock.Mock()
        mock_keychain.get_service.return_value = ServiceConfig(
            {"username": "fake@fake.devhub"}
        )
        config = ScratchOrgConfig({}, "test", mock_keychain)

        assert config._choose_devhub() == "fake@fake.devhub"

    def test_choose_devhub__service_not_configured(self, Command):
        mock_keychain = mock.Mock()
        mock_keychain.get_service.side_effect = ServiceNotConfigured
        config = ScratchOrgConfig({}, "test", mock_keychain)

        assert config._choose_devhub() is None


class TestScratchOrgConfigPytest:
    def test_build_org_create_args(self, scratch_def_file):
        mock_keychain = mock.Mock()
        mock_keychain.get_service.return_value = ServiceConfig(
            {"username": "fake@fake.devhub"}
        )
        config = ScratchOrgConfig(
            {
                "config_file": "tmp.json",
                "email_address": "test@example.com",
                "noancestors": True,
                "sfdx_alias": "project__org",
                "default": True,
                "instance": "NA01",
            },
            "test",
            mock_keychain,
        )
        args = config._build_org_create_args()
        assert args == [
            "-f",
            "tmp.json",
            "-w",
            "120",
            "--targetdevhubusername",
            "fake@fake.devhub",
            "-n",
            "--noancestors",
            "--durationdays",
            "1",
            "-a",
            "project__org",
            "adminEmail=test@example.com",
            "-s",
            "instance=NA01",
        ]

    def test_build_org_create_args__email_in_scratch_def(self):
        config = ScratchOrgConfig(
            {
                "config_file": "tmp.json",
                "set_password": True,
                "email_address": "test@example.com",
            },
            "test",
        )
        with temporary_dir():
            with open("tmp.json", "w") as f:
                f.write('{"adminEmail": "other_test@example.com"}')
            args = config._build_org_create_args()

        assert "adminEmail=test@example.com" not in args

    def test_temporary_backwards_compatiblity_hacks(self):
        filename = Path(__file__).parent / "_test_config_backwards_compatibility.py"
        # run this in a separate process to not confuse
        # the module table
        assert os.system(f"pytest {filename}") == 0
