import json
import os
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from cumulusci.core.config import BaseConfig
from cumulusci.core.config import UniversalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import ConnectedAppOAuthConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import ScratchOrgConfig
from cumulusci.core.config import ServiceConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.keychain import BaseEncryptedProjectKeychain
from cumulusci.core.keychain import EncryptedFileProjectKeychain
from cumulusci.core.keychain import EnvironmentProjectKeychain
from cumulusci.core.keychain.encrypted_file_project_keychain import GlobalOrg
from cumulusci.core.exceptions import OrgNotFound
from cumulusci.core.tests.utils import EnvironmentVarGuard

__location__ = os.path.dirname(os.path.realpath(__file__))


class ProjectKeychainTestMixin(unittest.TestCase):

    keychain_class = BaseProjectKeychain

    def setUp(self):
        self.universal_config = UniversalConfig()
        self.project_config = BaseProjectConfig(
            self.universal_config, config={"no_yaml": True}
        )
        self.project_config.config["services"] = {
            "connected_app": {"attributes": {"test": {"required": True}}},
            "github": {"attributes": {"name": {"required": True}, "password": {}}},
            "not_configured": {"attributes": {"foo": {"required": True}}},
        }
        self.project_config.project__name = "TestProject"
        self.services = {
            "connected_app": ServiceConfig({"test": "value"}),
            "github": ServiceConfig({"name": "hub"}),
        }
        self.org_config = OrgConfig({"foo": "bar"}, "test")
        self.scratch_org_config = ScratchOrgConfig(
            {"foo": "bar", "scratch": True}, "test_scratch"
        )
        self.key = "0123456789123456"


class TestEnvironmentProjectKeychain(ProjectKeychainTestMixin):
    keychain_class = EnvironmentProjectKeychain

    def setUp(self):
        super(TestEnvironmentProjectKeychain, self).setUp()
        self.env = EnvironmentVarGuard().__enter__()
        self._clean_env(self.env)
        self.env.set(
            f"{self.keychain_class.org_var_prefix}test",
            json.dumps(self.org_config.config),
        )
        self.env.set(
            f"{self.keychain_class.service_var_prefix}connected_app",
            json.dumps(self.services["connected_app"].config),
        )
        self.env.set(
            f"{self.keychain_class.service_var_prefix}github",
            json.dumps(self.services["github"].config),
        )

    def tearDown(self):
        self.env.__exit__()

    def _clean_env(self, env):
        for key, value in list(env.items()):
            if key.startswith(self.keychain_class.org_var_prefix):
                del env[key]
        for key, value in list(env.items()):
            if key.startswith(self.keychain_class.service_var_prefix):
                del env[key]

    def test_load_app(self):
        self.env["CUMULUSCI_CONNECTED_APP"] = "{}"
        keychain = self.keychain_class(self.project_config, self.key)
        self.assertIsInstance(keychain.app, ConnectedAppOAuthConfig)

    def test_get_org(self):
        keychain = self.keychain_class(self.project_config, self.key)
        self.assertEqual(list(keychain.orgs.keys()), ["test"])
        self.assertEqual(keychain.get_org("test").config, self.org_config.config)

    def test_get_org_not_found(self):
        self._clean_env(self.env)
        super(TestEnvironmentProjectKeychain, self).test_get_org_not_found()

    def test_list_orgs(self):
        keychain = self.keychain_class(self.project_config, self.key)
        self.assertEqual(keychain.list_orgs(), ["test"])

    def test_list_orgs_empty(self):
        self._clean_env(self.env)
        self.env.set(
            f"{self.keychain_class.service_var_prefix}connected_app",
            json.dumps(self.services["connected_app"].config),
        )
        super(TestEnvironmentProjectKeychain, self).test_list_orgs_empty()

    def test_load_scratch_org_config(self):
        self._clean_env(self.env)
        self.env.set(
            f"{self.keychain_class.org_var_prefix}test",
            json.dumps(self.scratch_org_config.config),
        )
        keychain = self.keychain_class(self.project_config, self.key)
        self.assertEqual(keychain.list_orgs(), ["test"])
        self.assertEqual(keychain.orgs["test"].__class__, ScratchOrgConfig)

    def test_load_scratch_orgs_create_one(self):
        self._clean_env(self.env)
        super(TestEnvironmentProjectKeychain, self).test_load_scratch_orgs_create_one()

    def test_load_scratch_orgs_none(self):
        self._clean_env(self.env)
        super(TestEnvironmentProjectKeychain, self).test_load_scratch_orgs_none()

    def test_get_default_org(self):
        org_config = self.org_config.config.copy()
        org_config["default"] = True
        self.env.set(
            f"{self.keychain_class.org_var_prefix}test", json.dumps(org_config)
        )
        super(TestEnvironmentProjectKeychain, self).test_get_default_org()

    def test_set_default_org(self):
        """ The EnvironmentProjectKeychain does not persist default org settings """
        org_config = self.org_config.config.copy()
        self.env.set(
            f"{self.keychain_class.org_var_prefix}test", json.dumps(org_config)
        )
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_default_org("test")
        expected_org_config = self.org_config.config.copy()
        expected_org_config["default"] = True

        self.assertEqual(None, keychain.get_default_org()[1])

    def test_set_and_get_scratch_org(self):
        self._clean_env(self.env)
        super(TestEnvironmentProjectKeychain, self).test_set_and_get_scratch_org()


class TestEncryptedFileProjectKeychain(ProjectKeychainTestMixin):
    keychain_class = EncryptedFileProjectKeychain

    def setUp(self):
        self.universal_config = UniversalConfig()
        self.project_config = BaseProjectConfig(
            self.universal_config, config={"noyaml": True}
        )
        self.project_config.config["services"] = {
            "connected_app": {"attributes": {"test": {"required": True}}},
            "github": {"attributes": {"git": {"required": True}, "password": {}}},
            "not_configured": {"attributes": {"foo": {"required": True}}},
        }
        self.project_config.project__name = "TestProject"
        self.project_name = "TestProject"
        self.org_config = OrgConfig({"foo": "bar"}, "test")
        self.scratch_org_config = ScratchOrgConfig(
            {"foo": "bar", "scratch": True}, "test_scratch"
        )
        self.services = {
            "connected_app": ServiceConfig({"test": "value"}),
            "github": ServiceConfig({"git": "hub"}),
        }
        self.key = "0123456789123456"

        self._mk_temp_home()
        self._home_patch = mock.patch(
            "pathlib.Path.home", return_value=Path(self.tempdir_home)
        )
        self._home_patch.__enter__()
        self._mk_temp_project()
        os.chdir(self.tempdir_project)

    def tearDown(self):
        self._home_patch.__exit__(None, None, None)

    def _mk_temp_home(self):
        self.tempdir_home = tempfile.mkdtemp()
        global_config_dir = os.path.join(self.tempdir_home, ".cumulusci")
        os.makedirs(global_config_dir)

    def _mk_temp_project(self):
        self.tempdir_project = tempfile.mkdtemp()
        git_dir = os.path.join(self.tempdir_project, ".git")
        os.makedirs(git_dir)
        self._create_git_config()

    def _create_git_config(self):
        filename = os.path.join(self.tempdir_project, ".git", "config")
        content = (
            '[remote "origin"]\n'
            + f"  url = git@github.com:TestOwner/{self.project_name}"
        )
        self._write_file(filename, content)

    def _write_file(self, filename, content):
        with open(filename, "w") as f:
            f.write(content)

    def test_set_service_github_project(self):
        self.test_set_service_github(True)

    def test_set_and_get_org_global(self):
        self.test_set_and_get_org(True)

    def test_set_and_get_org__universal_config(self):
        keychain = self.keychain_class(self.universal_config, self.key)
        keychain.set_org(self.org_config, False)
        self.assertEqual(list(keychain.orgs.keys()), [])

    def test_load_files__org_empty(self):
        dummy_keychain = BaseEncryptedProjectKeychain(self.project_config, self.key)
        os.makedirs(os.path.join(self.tempdir_home, ".cumulusci", self.project_name))
        self._write_file(
            os.path.join(self.tempdir_home, "test.org"),
            dummy_keychain._encrypt_config(BaseConfig({"foo": "bar"})).decode("utf-8"),
        )
        keychain = self.keychain_class(self.project_config, self.key)
        del keychain.config["orgs"]
        with mock.patch.object(
            self.keychain_class, "global_config_dir", Path(self.tempdir_home)
        ):
            keychain._load_orgs()
        self.assertIn("foo", keychain.get_org("test").config)
        self.assertEqual(keychain.get_org("test").keychain, keychain)

    def test_load_files__services(self):
        dummy_keychain = BaseEncryptedProjectKeychain(self.project_config, self.key)
        devhub_service_path = Path(f"{self.tempdir_home}/.cumulusci/services/devhub")
        devhub_service_path.mkdir(parents=True)
        self._write_file(
            Path(devhub_service_path / "alias.service"),
            dummy_keychain._encrypt_config(BaseConfig({"foo": "bar"})).decode("utf-8"),
        )

        keychain = self.keychain_class(self.project_config, self.key)
        del keychain.config["services"]

        with mock.patch.object(
            self.keychain_class, "global_config_dir", Path(self.tempdir_home)
        ):
            keychain._load_files(
                f"{self.tempdir_home}/.cumulusci", ".service", "services"
            )

        assert "foo" in keychain.get_service("devhub", "test").config
        assert keychain.get_service("devhub", "test").keychain == keychain

    def test_load_file(self):
        self._write_file(os.path.join(self.tempdir_home, "config"), "foo")
        keychain = self.keychain_class(self.project_config, self.key)
        keychain._load_file(self.tempdir_home, "config", "from_file")
        self.assertEqual("foo", keychain.config["from_file"])

    def test_load_file__universal_config(self):
        self._write_file(os.path.join(self.tempdir_home, "config"), "foo")
        keychain = self.keychain_class(self.project_config, self.key)
        keychain._load_file(self.tempdir_home, "config", "from_file")
        self.assertEqual("foo", keychain.config["from_file"])

    @mock.patch("cumulusci.core.utils.cleanup_org_cache_dirs")
    def test_remove_org(self, cleanup_org_cache_dirs):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_org(self.org_config)
        keychain.remove_org("test")
        self.assertNotIn("test", keychain.orgs)
        assert cleanup_org_cache_dirs.called_once_with(keychain, self.project_config)

    def test_remove_org__not_found(self):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.orgs["test"] = mock.Mock()
        with self.assertRaises(OrgNotFound):
            keychain.remove_org("test")

    def test_remove_org__global__not_found(self):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.orgs["test"] = mock.Mock()
        with self.assertRaises(OrgNotFound):
            keychain.remove_org("test", global_org=True)

    def test_set_and_get_org_local_should_not_shadow_global(self):
        keychain = self.keychain_class(self.project_config, self.key)
        self.org_config.global_org = True
        keychain.set_org(self.org_config, global_org=True)
        assert ["test"] == list(keychain.orgs.keys())
        assert isinstance(keychain.orgs["test"], GlobalOrg), keychain.orgs["test"]
        assert self.org_config.config == keychain.get_org("test").config
        assert Path(self.tempdir_home, ".cumulusci", "test.org").exists()

        # check that it saves to the right place
        with mock.patch(
            "cumulusci.core.keychain.encrypted_file_project_keychain.open"
        ) as o:
            self.org_config.save()
            opened_filename = o.mock_calls[0][1][0]
            assert ".cumulusci/test.org" in opened_filename.replace(
                os.sep, "/"
            ), opened_filename

        # check that it can be loaded in a fresh keychain
        new_keychain = self.keychain_class(self.project_config, self.key)
        org_config = new_keychain.get_org("test")
        assert org_config.global_org

    def test_cache_dir(self):
        keychain = self.keychain_class(self.project_config, self.key)
        assert keychain.cache_dir.name == ".cci"

    def test_get_default_org__with_files(self):
        keychain = self.keychain_class(self.project_config, self.key)
        org_config = OrgConfig(self.org_config.config.copy(), "test", keychain=keychain)
        org_config.save()
        with open(self._default_org_path(), "w") as f:
            f.write("test")
        try:
            self.assertEqual(keychain.get_default_org()[1].config, org_config.config)
        finally:
            self._default_org_path().unlink()

    def test_get_default_org__with_files__missing_org(self):
        keychain = self.keychain_class(self.project_config, self.key)
        with open(self._default_org_path(), "w") as f:
            f.write("should_not_exist")
        assert self._default_org_path().exists()
        assert keychain.get_default_org() == (None, None)
        assert not self._default_org_path().exists()

    @mock.patch("sarge.Command")
    def test_set_default_org__with_files(self, Command):
        keychain = self.keychain_class(self.project_config, self.key)
        org_config = OrgConfig(self.org_config.config.copy(), "test")
        keychain.set_org(org_config)
        keychain.set_default_org("test")
        with open(self._default_org_path()) as f:
            assert f.read() == "test"
        self._default_org_path().unlink()

    @mock.patch("sarge.Command")
    def test_unset_default_org__with_files(self, Command):
        keychain = self.keychain_class(self.project_config, self.key)
        org_config = self.org_config.config.copy()
        org_config = OrgConfig(org_config, "test")
        keychain.set_org(org_config)
        keychain.set_default_org("test")
        keychain.unset_default_org()
        self.assertEqual(keychain.get_default_org()[1], None)
        assert not self._default_org_path().exists()

    def _default_org_path(self):
        return Path(self.tempdir_home) / ".cumulusci/TestProject/DEFAULT_ORG.txt"

    # old way of finding defaults used contents of the files themselves
    # we should preserve backwards compatibiliity for a few months
    def test_get_default_org__file_missing_fallback(self):
        keychain = self.keychain_class(self.project_config, self.key)
        org_config = OrgConfig(self.org_config.config.copy(), "test", keychain=keychain)
        org_config.config["default"] = True
        org_config.save()
        self.assertEqual(keychain.get_default_org()[1].config, org_config.config)

    def test_get_default_org__outside_project(self):
        keychain = self.keychain_class(self.universal_config, self.key)
        assert keychain.get_default_org() == (None, None)

    def test_create_services_dir_structure(self):
        service_types = list(self.universal_config.config["services"].keys())
        num_services = len(service_types)

        # _create_services_dir_structure() is invoked via constructor
        keychain = self.keychain_class(self.universal_config, self.key)

        services_path = Path(f"{self.tempdir_home}/.cumulusci/services")
        for path in Path.iterdir(services_path):
            if path.name in service_types:
                assert Path.is_dir(path)
                service_types.remove(path.name)

        assert len(service_types) == 0

        # explicitly invoke a second time to test idempotency
        keychain._create_services_dir_structure(self.tempdir_home)
        # make sure no new dirs appeared
        assert num_services == len(list(Path.iterdir(services_path)))

    def test_convert_unaliased_services(self):
        file_contents = "devhub"
        devhub_service_path = Path(f"{self.tempdir_home}/.cumulusci/devhub.service")
        self._write_file(devhub_service_path, file_contents)

        keychain = self.keychain_class(self.universal_config, self.key)
        keychain._convert_unaliased_services(self.tempdir_home)

        service_file_path = Path(
            f"{self.tempdir_home}/.cumulusci/services/devhub/devhub_default.service"
        )

        assert Path.is_file(service_file_path)
        with open(service_file_path) as f:
            assert f.read() == file_contents
        assert not Path.is_file(devhub_service_path)

    def test_convert_unaliased_services__warn_duplicate_default_service(self):
        # make unaliased devhub service
        file_contents = "devhub"
        unaliased_devhub_service = Path(
            f"{self.tempdir_home}/.cumulusci/devhub.service"
        )
        self._write_file(unaliased_devhub_service, file_contents)
        # make default aliased devhub service
        aliased_devhub_service = Path(
            f"{self.tempdir_home}/.cumulusci/services/devhub/"
        )
        aliased_devhub_service.mkdir(parents=True)
        self._write_file(
            f"{aliased_devhub_service}/devhub_default.service", file_contents
        )

        keychain = self.keychain_class(self.universal_config, self.key)
        keychain._convert_unaliased_services(self.tempdir_home)

        # ensure we don't remove this service file
        assert Path.is_file(unaliased_devhub_service)
