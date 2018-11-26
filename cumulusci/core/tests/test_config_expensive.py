from __future__ import absolute_import
from datetime import datetime
from datetime import timedelta

import io
import os
import tempfile
import unittest

import mock

from cumulusci.core.utils import ordered_yaml_load
from cumulusci.core.config import ScratchOrgConfig
from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.exceptions import NotInProject
from cumulusci.core.exceptions import ProjectConfigNotFound
from cumulusci.core.exceptions import ScratchOrgException

__location__ = os.path.dirname(os.path.realpath(__file__))


@mock.patch("os.path.expanduser")
class TestBaseGlobalConfig(unittest.TestCase):
    def setUp(self):
        self.tempdir_home = tempfile.mkdtemp()

    def _create_global_config_local(self, content):
        self.tempdir_home = tempfile.mkdtemp()
        global_local_dir = os.path.join(self.tempdir_home, ".cumulusci")
        os.makedirs(global_local_dir)
        filename = os.path.join(global_local_dir, BaseGlobalConfig.config_filename)
        self._write_file(filename, content)

    def _write_file(self, filename, content):
        with open(filename, "w") as f:
            f.write(content)

    def test_load_global_config_no_local(self, mock_class):
        mock_class.return_value = self.tempdir_home
        config = BaseGlobalConfig()
        with open(__location__ + "/../../cumulusci.yml", "r") as f_expected_config:
            expected_config = ordered_yaml_load(f_expected_config)
        self.assertEqual(config.config, expected_config)

    def test_load_global_config_empty_local(self, mock_class):
        self._create_global_config_local("")
        mock_class.return_value = self.tempdir_home

        config = BaseGlobalConfig()
        with open(__location__ + "/../../cumulusci.yml", "r") as f_expected_config:
            expected_config = ordered_yaml_load(f_expected_config)
        self.assertEqual(config.config, expected_config)

    def test_load_global_config_with_local(self, mock_class):
        local_yaml = "tasks:\n    newtesttask:\n        description: test description"
        self._create_global_config_local(local_yaml)
        mock_class.return_value = self.tempdir_home

        config = BaseGlobalConfig()
        with open(__location__ + "/../../cumulusci.yml", "r") as f_expected_config:
            expected_config = ordered_yaml_load(f_expected_config)
        expected_config["tasks"]["newtesttask"] = {}
        expected_config["tasks"]["newtesttask"]["description"] = "test description"
        self.assertEqual(config.config, expected_config)


@mock.patch("os.path.expanduser")
class TestBaseProjectConfig(unittest.TestCase):
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
        filename = os.path.join(dirname, "master")
        content = self.current_commit
        self._write_file(filename, content)

    def _create_global_config_local(self, content):
        global_local_dir = os.path.join(self.tempdir_home, ".cumulusci")
        os.makedirs(global_local_dir)
        filename = os.path.join(global_local_dir, BaseGlobalConfig.config_filename)
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

    def setUp(self):
        self.tempdir_home = tempfile.mkdtemp()
        self.tempdir_project = tempfile.mkdtemp()
        self.project_name = "TestRepo"
        self.current_commit = "abcdefg1234567890"
        self.current_branch = "master"

    def tearDown(self):
        pass

    def test_load_project_config_not_repo(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.chdir(self.tempdir_project)
        global_config = BaseGlobalConfig()
        with self.assertRaises(NotInProject):
            config = BaseProjectConfig(global_config)

    def test_load_project_config_no_config(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, ".git"))
        os.chdir(self.tempdir_project)
        global_config = BaseGlobalConfig()
        with self.assertRaises(ProjectConfigNotFound):
            config = BaseProjectConfig(global_config)

    def test_load_project_config_empty_config(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, ".git"))
        self._create_git_config()
        # create empty project config file
        filename = os.path.join(self.tempdir_project, BaseProjectConfig.config_filename)
        content = ""
        self._write_file(filename, content)

        os.chdir(self.tempdir_project)
        global_config = BaseGlobalConfig()
        config = BaseProjectConfig(global_config)
        self.assertEqual(config.config_project, {})

    def test_load_project_config_valid_config(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, ".git"))
        self._create_git_config()
        local_yaml = "tasks:\n    newtesttask:\n        description: test description"
        self._create_global_config_local(local_yaml)

        # create valid project config file
        self._create_project_config()

        os.chdir(self.tempdir_project)
        global_config = BaseGlobalConfig()
        config = BaseProjectConfig(global_config)
        self.assertEqual(config.project__package__name, "TestProject")
        self.assertEqual(config.project__package__namespace, "testproject")

    def test_repo_owner(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, ".git"))
        self._create_git_config()

        # create valid project config file
        self._create_project_config()

        os.chdir(self.tempdir_project)
        global_config = BaseGlobalConfig()
        config = BaseProjectConfig(global_config)
        self.assertEqual(config.repo_owner, "TestOwner")

    def test_repo_branch(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, ".git"))
        self._create_git_config()

        # create valid project config file
        self._create_project_config()

        os.chdir(self.tempdir_project)
        global_config = BaseGlobalConfig()
        config = BaseProjectConfig(global_config)
        self.assertEqual(config.repo_branch, self.current_branch)

    def test_repo_commit(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, ".git"))
        self._create_git_config()

        # create valid project config file
        self._create_project_config()

        os.chdir(self.tempdir_project)
        global_config = BaseGlobalConfig()
        config = BaseProjectConfig(global_config)
        self.assertEqual(config.repo_commit, self.current_commit)

    def test_load_project_config_local(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, ".git"))
        self._create_git_config()

        # create valid project config file
        self._create_project_config()

        # create local project config file
        content = "project:\n" + "    package:\n" + "        api_version: 10\n"
        self._create_project_config_local(content)

        os.chdir(self.tempdir_project)
        global_config = BaseGlobalConfig()
        config = BaseProjectConfig(global_config)
        self.assertNotEqual(config.config_project_local, {})
        self.assertEqual(config.project__package__api_version, 10)

    def test_load_additional_yaml(self, mock_class):
        mock_class.return_value = self.tempdir_home
        os.mkdir(os.path.join(self.tempdir_project, ".git"))
        self._create_git_config()

        # create valid project config file
        self._create_project_config()

        # create local project config file
        content = "project:\n" + "    package:\n" + "        api_version: 10\n"

        os.chdir(self.tempdir_project)
        global_config = BaseGlobalConfig()
        config = BaseProjectConfig(global_config, additional_yaml=content)
        self.assertNotEqual(config.config_additional_yaml, {})
        self.assertEqual(config.project__package__api_version, 10)


@mock.patch("sarge.Command")
class TestScratchOrgConfig(unittest.TestCase):
    def test_scratch_info(self, Command):
        result = b"""{
    "result": {
        "instanceUrl": "url",
        "accessToken": "access!token",
        "username": "username",
        "password": "password"
    }
}"""
        Command.return_value = mock.Mock(
            stderr=io.BytesIO(b""), stdout=io.BytesIO(result), returncode=0
        )

        config = ScratchOrgConfig({"username": "test"}, "test")
        info = config.scratch_info

        self.assertEqual(
            info,
            {
                "access_token": "access!token",
                "instance_url": "url",
                "org_id": "access",
                "password": "password",
                "username": "username",
            },
        )
        self.assertIs(info, config._scratch_info)
        self.assertTrue(set(info.items()).issubset(set(config.config.items())))
        self.assertTrue(config._scratch_info_date)

    def test_scratch_info_memoized(self, Command):
        config = ScratchOrgConfig({"username": "test"}, "test")
        config._scratch_info = _marker = object()
        info = config.scratch_info
        self.assertIs(info, _marker)

    def test_scratch_info_non_json_response(self, Command):
        Command.return_value = mock.Mock(
            stderr=io.BytesIO(b""), stdout=io.BytesIO(b"<html></html>"), returncode=0
        )

        config = ScratchOrgConfig({"username": "test"}, "test")
        with self.assertRaises(ScratchOrgException):
            config.scratch_info

    def test_scratch_info_command_error(self, Command):
        Command.return_value = mock.Mock(
            stderr=io.BytesIO(b"error"), stdout=io.BytesIO(b"out"), returncode=1
        )

        config = ScratchOrgConfig({"username": "test"}, "test")

        try:
            config.scratch_info
        except ScratchOrgException as err:
            self.assertEqual(str(err), "\nstderr:\nerror\nstdout:\nout")
        else:
            self.fail("Expected ScratchOrgException")

    def test_scratch_info_username_not_found(self, Command):
        Command.return_value = mock.Mock(
            stderr=io.BytesIO(b"error"), stdout=io.BytesIO(b"out"), returncode=0
        )

        config = ScratchOrgConfig({"config_file": "tmp"}, "test")

        with self.assertRaises(ScratchOrgException):
            config.scratch_info

    def test_scratch_info_password_from_config(self, Command):
        result = b"""{
    "result": {
        "instanceUrl": "url",
        "accessToken": "access!token",
        "username": "username"
    }
}"""
        Command.return_value = mock.Mock(
            stderr=io.BytesIO(b""), stdout=io.BytesIO(result), returncode=0
        )

        config = ScratchOrgConfig({"username": "test", "password": "password"}, "test")
        info = config.scratch_info

        self.assertEqual(info["password"], "password")

    def test_access_token(self, Command):
        config = ScratchOrgConfig({}, "test")
        _marker = object()
        config._scratch_info = {"access_token": _marker}
        self.assertIs(config.access_token, _marker)

    def test_instance_url(self, Command):
        config = ScratchOrgConfig({}, "test")
        _marker = object()
        config._scratch_info = {"instance_url": _marker}
        self.assertIs(config.instance_url, _marker)

    def test_org_id_from_config(self, Command):
        config = ScratchOrgConfig({"org_id": "test"}, "test")
        self.assertEqual(config.org_id, "test")

    def test_org_id_from_scratch_info(self, Command):
        config = ScratchOrgConfig({}, "test")
        _marker = object()
        config._scratch_info = {"org_id": _marker}
        self.assertIs(config.org_id, _marker)

    def test_user_id_from_config(self, Command):
        config = ScratchOrgConfig({"user_id": "test"}, "test")
        self.assertEqual(config.user_id, "test")

    def test_user_id_from_org(self, Command):
        sf = mock.Mock()
        sf.query_all.return_value = {"records": [{"Id": "test"}]}

        config = ScratchOrgConfig({"username": "test_username"}, "test")
        config._scratch_info = {
            "instance_url": "test_instance",
            "access_token": "token",
        }
        # This is ugly...since ScratchOrgConfig is in a module
        # with the same name that is imported in cumulusci.core.config's
        # __init__.py, we have no way to externally grab the
        # module without going through the function's globals.
        with mock.patch.dict(
            ScratchOrgConfig.user_id.fget.__globals__,
            Salesforce=mock.Mock(return_value=sf),
        ):
            self.assertEqual(config.user_id, "test")

    def test_username_from_scratch_info(self, Command):
        config = ScratchOrgConfig({}, "test")
        _marker = object()
        config._scratch_info = {"username": _marker}
        self.assertIs(config.username, _marker)

    def test_password_from_config(self, Command):
        config = ScratchOrgConfig({"password": "test"}, "test")
        self.assertEqual(config.password, "test")

    def test_pasword_from_scratch_info(self, Command):
        config = ScratchOrgConfig({}, "test")
        _marker = object()
        config._scratch_info = {"password": _marker}
        self.assertIs(config.password, _marker)

    def test_days(self, Command):
        config = ScratchOrgConfig({"days": 2}, "test")
        self.assertEqual(config.days, 2)

    def test_days_default(self, Command):
        config = ScratchOrgConfig({}, "test")
        self.assertEqual(config.days, 1)

    def test_expired(self, Command):
        config = ScratchOrgConfig({"days": 1}, "test")
        now = datetime.now()
        config.date_created = now
        self.assertFalse(config.expired)
        config.date_created = now - timedelta(days=2)
        self.assertTrue(config.expired)

    def test_expires(self, Command):
        config = ScratchOrgConfig({"days": 1}, "test")
        now = datetime.now()
        config.date_created = now
        self.assertEqual(config.expires, now + timedelta(days=1))

    def test_days_alive(self, Command):
        config = ScratchOrgConfig({}, "test")
        config.date_created = datetime.now()
        self.assertEqual(config.days_alive, 1)

    def test_create_org(self, Command):
        out = b"Successfully created scratch org: ORG_ID, username: USERNAME"
        Command.return_value = p = mock.Mock(
            stdout=io.BytesIO(out), stderr=io.BytesIO(b""), returncode=0
        )

        config = ScratchOrgConfig({"config_file": "tmp", "set_password": True}, "test")
        config.generate_password = mock.Mock()
        config.create_org()

        p.run.assert_called_once()
        self.assertEqual(config.config["org_id"], "ORG_ID")
        self.assertEqual(config.config["username"], "USERNAME")
        self.assertIn("date_created", config.config)
        config.generate_password.assert_called_once()
        self.assertTrue(config.config["created"])
        self.assertEqual(config.scratch_org_type, "workspace")

    def test_create_org_no_config_file(self, Command):
        config = ScratchOrgConfig({}, "test")
        self.assertEqual(config.create_org(), None)
        Command.assert_not_called()

    def test_create_org_command_error(self, Command):
        Command.return_value = mock.Mock(
            stdout=io.BytesIO(b""), stderr=io.BytesIO(b"scratcherror"), returncode=1
        )

        config = ScratchOrgConfig({"config_file": "tmp"}, "test")
        with self.assertRaises(ScratchOrgException) as ctx:
            config.create_org()
            self.assertIn("scratcherror", str(ctx.error))

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
        self.assertTrue(config.can_delete())

    def test_delete_org(self, Command):
        Command.return_value = mock.Mock(
            stdout=io.BytesIO(b"info"), stderr=io.BytesIO(b""), returncode=0
        )

        config = ScratchOrgConfig({"username": "test", "created": True}, "test")
        config.delete_org()

        self.assertFalse(config.config["created"])
        self.assertIs(config.config["username"], None)

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
        with self.assertRaises(ScratchOrgException):
            config.delete_org()

    def test_force_refresh_oauth_token(self, Command):
        Command.return_value = p = mock.Mock(
            stdout=io.BytesIO(b""), stderr=io.BytesIO(b""), returncode=0
        )

        config = ScratchOrgConfig({"username": "test"}, "test")
        config.force_refresh_oauth_token()

        p.run.assert_called_once()

    def test_force_refresh_oauth_token_error(self, Command):
        Command.return_value = p = mock.Mock(
            stdout=io.BytesIO(b"error"), stderr=io.BytesIO(b""), returncode=1
        )

        config = ScratchOrgConfig({"username": "test"}, "test")
        with self.assertRaises(ScratchOrgException):
            config.force_refresh_oauth_token()

    def test_refresh_oauth_token(self, Command):
        result = b"""{
    "result": {
        "instanceUrl": "url",
        "accessToken": "access!token",
        "username": "username",
        "password": "password"
    }
}"""
        Command.return_value = mock.Mock(
            stdout=io.BytesIO(result), stderr=io.BytesIO(b""), returncode=0
        )

        config = ScratchOrgConfig({"username": "test"}, "test")
        config._scratch_info = {}
        config._scratch_info_date = datetime.now() - timedelta(days=1)
        config.force_refresh_oauth_token = mock.Mock()

        config.refresh_oauth_token(keychain=None)

        config.force_refresh_oauth_token.assert_called_once()
        self.assertTrue(config._scratch_info)
