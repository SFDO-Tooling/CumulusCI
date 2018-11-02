from __future__ import absolute_import
import json
import os
import tempfile
import unittest

import mock

from cumulusci.core.tests.utils import EnvironmentVarGuard

from cumulusci.core.config import BaseConfig
from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import ConnectedAppOAuthConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import ScratchOrgConfig
from cumulusci.core.config import ServiceConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.keychain import BaseEncryptedProjectKeychain
from cumulusci.core.keychain import EncryptedFileProjectKeychain
from cumulusci.core.keychain import EnvironmentProjectKeychain
from cumulusci.core.exceptions import ConfigError
from cumulusci.core.exceptions import KeychainKeyNotFound
from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci.core.exceptions import ServiceNotValid
from cumulusci.core.exceptions import OrgNotFound
from cumulusci.core.exceptions import ProjectConfigNotFound

__location__ = os.path.dirname(os.path.realpath(__file__))


class ProjectKeychainTestMixin(unittest.TestCase):

    keychain_class = BaseProjectKeychain

    def setUp(self):
        self.global_config = BaseGlobalConfig()
        self.project_config = BaseProjectConfig(
            self.global_config, config={"no_yaml": True}
        )
        self.project_config.config["services"] = {
            "connected_app": {"attributes": {"test": {"required": True}}},
            "github": {"attributes": {"name": {"required": True}, "password": {}}},
            "mrbelvedere": {"attributes": {"mr": {"required": True}}},
            "not_configured": {"attributes": {"foo": {"required": True}}},
        }
        self.project_config.project__name = "TestProject"
        self.services = {
            "connected_app": ServiceConfig({"test": "value"}),
            "github": ServiceConfig({"name": "hub"}),
            "mrbelvedere": ServiceConfig({"mr": "belvedere"}),
        }
        self.org_config = OrgConfig({"foo": "bar"}, "test")
        self.scratch_org_config = ScratchOrgConfig(
            {"foo": "bar", "scratch": True}, "test_scratch"
        )
        self.key = "0123456789123456"

    def test_init(self):
        keychain = self.keychain_class(self.project_config, self.key)
        self.assertEqual(keychain.project_config, self.project_config)
        self.assertEqual(keychain.key, self.key)

    def test_set_non_existant_service(self, project=False):
        keychain = self.keychain_class(self.project_config, self.key)
        with self.assertRaises(ServiceNotValid) as context:
            keychain.set_service("doesnotexist", ServiceConfig({"name": ""}), project)

    def test_set_invalid_service(self, project=False):
        keychain = self.keychain_class(self.project_config, self.key)
        with self.assertRaises(ServiceNotValid) as context:
            keychain.set_service("github", ServiceConfig({"name": ""}), project)

    def test_get_service_not_configured(self):
        keychain = self.keychain_class(self.project_config, self.key)
        with self.assertRaises(ServiceNotConfigured) as context:
            keychain.get_service("not_configured")

    def test_change_key(self):
        new_key = "9876543210987654"
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_org(self.org_config)
        keychain.set_service("connected_app", self.services["connected_app"])
        keychain.set_service("github", self.services["github"])
        keychain.set_service("mrbelvedere", self.services["mrbelvedere"])
        keychain.change_key(new_key)
        self.assertEqual(keychain.key, new_key)
        self.assertEqual(
            keychain.get_service("connected_app").config,
            self.services["connected_app"].config,
        )
        self.assertEqual(
            keychain.get_service("github").config, self.services["github"].config
        )
        self.assertEqual(
            keychain.get_service("mrbelvedere").config,
            self.services["mrbelvedere"].config,
        )
        self.assertEqual(keychain.get_org("test").config, self.org_config.config)

    def test_set_service_github(self, project=False):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_service("github", self.services["github"], project)
        self.assertEqual(
            keychain.get_service("github").config, self.services["github"].config
        )

    def test_set_service_mrbelvedere(self, project=False):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_service("mrbelvedere", self.services["mrbelvedere"], project)
        self.assertEqual(
            keychain.get_service("mrbelvedere").config,
            self.services["mrbelvedere"].config,
        )

    def test_set_and_get_org(self, global_org=False):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_org(self.org_config, global_org)
        self.assertEqual(list(keychain.orgs.keys()), ["test"])
        self.assertEqual(keychain.get_org("test").config, self.org_config.config)

    def test_set_and_get_scratch_org(self, global_org=False):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_org(self.scratch_org_config, global_org)
        self.assertEqual(list(keychain.orgs.keys()), ["test_scratch"])
        org = keychain.get_org("test_scratch")
        self.assertEqual(org.config, self.scratch_org_config.config)
        self.assertEqual(org.__class__, ScratchOrgConfig)

    def test_load_scratch_orgs_none(self):
        keychain = self.keychain_class(self.project_config, self.key)
        self.assertEqual(list(keychain.orgs), [])

    def test_load_scratch_orgs_create_one(self):
        self.project_config.config["orgs"] = {}
        self.project_config.config["orgs"]["scratch"] = {}
        self.project_config.config["orgs"]["scratch"]["test_scratch_auto"] = {}
        keychain = self.keychain_class(self.project_config, self.key)
        self.assertEqual(list(keychain.orgs), ["test_scratch_auto"])

    def test_load_scratch_orgs_existing_org(self):
        self.project_config.config["orgs"] = {}
        self.project_config.config["orgs"]["scratch"] = {}
        self.project_config.config["orgs"]["scratch"]["test"] = {}
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_org(OrgConfig({}, "test"))
        self.assertEqual(list(keychain.orgs), ["test"])
        org = keychain.get_org("test")
        self.assertEqual(org.scratch, None)

    def test_get_org_not_found(self):
        keychain = self.keychain_class(self.project_config, self.key)
        with self.assertRaises(OrgNotFound):
            keychain.get_org("test")

    def test_get_default_org(self):
        keychain = self.keychain_class(self.project_config, self.key)
        org_config = self.org_config.config.copy()
        org_config = OrgConfig(org_config, "test")
        org_config.config["default"] = True
        keychain.set_org(org_config)
        self.assertEqual(keychain.get_default_org()[1].config, org_config.config)

    def test_get_default_org_no_default(self):
        keychain = self.keychain_class(self.project_config, self.key)
        self.assertEqual(keychain.get_default_org()[1], None)

    def test_set_default_org(self):
        keychain = self.keychain_class(self.project_config, self.key)
        org_config = self.org_config.config.copy()
        org_config = OrgConfig(org_config, "test")
        keychain.set_org(org_config)
        keychain.set_default_org("test")
        expected_org_config = org_config.config.copy()
        expected_org_config["default"] = True

        self.assertEqual(expected_org_config, keychain.get_default_org()[1].config)

    def test_unset_default_org(self):
        keychain = self.keychain_class(self.project_config, self.key)
        org_config = self.org_config.config.copy()
        org_config = OrgConfig(org_config, "test")
        org_config.config["default"] = True
        keychain.set_org(org_config)
        keychain.unset_default_org()
        self.assertEqual(keychain.get_default_org()[1], None)

    def test_list_orgs(self):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_org(self.org_config)
        self.assertEqual(keychain.list_orgs(), ["test"])

    def test_list_orgs_empty(self):
        keychain = self.keychain_class(self.project_config, self.key)
        self.assertEqual(keychain.list_orgs(), [])


class TestBaseProjectKeychain(ProjectKeychainTestMixin):
    def test_convert_connected_app(self):
        project_config = BaseProjectConfig(
            self.global_config,
            {
                "services": {
                    "connected_app": {
                        "attributes": {
                            "callback_url": {},
                            "client_id": {},
                            "client_secret": {},
                        }
                    }
                }
            },
        )
        keychain = self.keychain_class(project_config, self.key)
        app_config = {
            "callback_url": "http://localhost:8080/callback",
            "client_id": "CLIENT",
            "client_secret": "SECRET",
        }
        keychain.config["app"] = BaseConfig(app_config)
        keychain._convert_connected_app()
        self.assertEqual(app_config, keychain.get_service("connected_app").config)

    def test_create_scratch_org(self):
        project_config = BaseProjectConfig(
            self.global_config, {"orgs": {"scratch": {"dev": {}}}}
        )
        keychain = self.keychain_class(project_config, self.key)
        keychain.set_org = mock.Mock()
        keychain.create_scratch_org("test", "dev", days=3)
        org_config = keychain.set_org.call_args[0][0]
        self.assertEqual(3, org_config.days)

    def test_remove_org(self):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_org(self.org_config)
        keychain.remove_org("test")
        self.assertNotIn("test", keychain.orgs)


class TestEnvironmentProjectKeychain(ProjectKeychainTestMixin):
    keychain_class = EnvironmentProjectKeychain

    def setUp(self):
        super(TestEnvironmentProjectKeychain, self).setUp()
        self.env = EnvironmentVarGuard().__enter__()
        self._clean_env(self.env)
        self.env.set(
            "{}test".format(self.keychain_class.org_var_prefix),
            json.dumps(self.org_config.config),
        )
        self.env.set(
            "{}connected_app".format(self.keychain_class.service_var_prefix),
            json.dumps(self.services["connected_app"].config),
        )
        self.env.set(
            "{}github".format(self.keychain_class.service_var_prefix),
            json.dumps(self.services["github"].config),
        )
        self.env.set(
            "{}mrbelvedere".format(self.keychain_class.service_var_prefix),
            json.dumps(self.services["mrbelvedere"].config),
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
            "{}connected_app".format(self.keychain_class.service_var_prefix),
            json.dumps(self.services["connected_app"].config),
        )
        super(TestEnvironmentProjectKeychain, self).test_list_orgs_empty()

    def test_load_scratch_org_config(self):
        self._clean_env(self.env)
        self.env.set(
            "{}test".format(self.keychain_class.org_var_prefix),
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
            "{}test".format(self.keychain_class.org_var_prefix), json.dumps(org_config)
        )
        super(TestEnvironmentProjectKeychain, self).test_get_default_org()

    def test_set_default_org(self):
        """ The EnvironmentProjectKeychain does not persist default org settings """
        org_config = self.org_config.config.copy()
        self.env.set(
            "{}test".format(self.keychain_class.org_var_prefix), json.dumps(org_config)
        )
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_default_org("test")
        expected_org_config = self.org_config.config.copy()
        expected_org_config["default"] = True

        self.assertEqual(None, keychain.get_default_org()[1])

    def test_set_and_get_scratch_org(self):
        self._clean_env(self.env)
        super(TestEnvironmentProjectKeychain, self).test_set_and_get_scratch_org()


class TestBaseEncryptedProjectKeychain(ProjectKeychainTestMixin):
    keychain_class = BaseEncryptedProjectKeychain

    def test_get_connected_app(self):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.app = keychain._encrypt_config(BaseConfig({}))
        app = keychain.get_connected_app()
        self.assertIsInstance(app, ConnectedAppOAuthConfig)

    def test_decrypt_config__no_config(self):
        keychain = self.keychain_class(self.project_config, self.key)
        config = keychain._decrypt_config(OrgConfig, None, extra=["test"])
        self.assertEqual(config.__class__, OrgConfig)
        self.assertEqual(config.config, {})

    def test_decrypt_config__no_config_2(self):
        keychain = self.keychain_class(self.project_config, self.key)
        config = keychain._decrypt_config(BaseConfig, None)
        self.assertEqual(config.__class__, BaseConfig)
        self.assertEqual(config.config, {})

    def test_validate_key__not_set(self):
        with self.assertRaises(KeychainKeyNotFound):
            self.keychain_class(self.project_config, None)

    def test_validate_key__wrong_length(self):
        with self.assertRaises(ConfigError):
            self.keychain_class(self.project_config, "1")


class TestEncryptedFileProjectKeychain(ProjectKeychainTestMixin):
    keychain_class = EncryptedFileProjectKeychain

    def setUp(self):
        self.global_config = BaseGlobalConfig()
        self.project_config = BaseProjectConfig(
            self.global_config, config={"noyaml": True}
        )
        self.project_config.config["services"] = {
            "connected_app": {"attributes": {"test": {"required": True}}},
            "github": {"attributes": {"git": {"required": True}, "password": {}}},
            "mrbelvedere": {"attributes": {"mr": {"required": True}}},
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
            "mrbelvedere": ServiceConfig({"mr": "belvedere"}),
        }
        self.key = "0123456789123456"

        self._mk_temp_home()
        self._expanduser_patch = mock.patch(
            "os.path.expanduser", return_value=self.tempdir_home
        )
        self._expanduser_patch.__enter__()
        self._mk_temp_project()
        os.chdir(self.tempdir_project)

    def tearDown(self):
        self._expanduser_patch.__exit__(None, None, None)

    def _mk_temp_home(self):
        self.tempdir_home = tempfile.mkdtemp()
        global_local_dir = os.path.join(self.tempdir_home, ".cumulusci")
        os.makedirs(global_local_dir)

    def _mk_temp_project(self):
        self.tempdir_project = tempfile.mkdtemp()
        git_dir = os.path.join(self.tempdir_project, ".git")
        os.makedirs(git_dir)
        self._create_git_config()

    def _create_git_config(self):
        filename = os.path.join(self.tempdir_project, ".git", "config")
        content = '[remote "origin"]\n' + "  url = git@github.com:TestOwner/{}".format(
            self.project_name
        )
        self._write_file(filename, content)

    def _write_file(self, filename, content):
        with open(filename, "w") as f:
            f.write(content)

    def test_set_service_github_project(self):
        self.test_set_service_github(True)

    def test_set_service_mrbelvedere_project(self):
        self.test_set_service_mrbelvedere(True)

    def test_set_and_get_org_global(self):
        self.test_set_and_get_org(True)

    def test_load_files__empty(self):
        dummy_keychain = BaseEncryptedProjectKeychain(self.project_config, self.key)
        os.makedirs(os.path.join(self.tempdir_home, ".cumulusci", self.project_name))
        self._write_file(
            os.path.join(self.tempdir_home, "test.org"),
            dummy_keychain._encrypt_config(BaseConfig({"foo": "bar"})).decode("utf-8"),
        )
        keychain = self.keychain_class(self.project_config, self.key)
        del keychain.config["orgs"]
        keychain._load_files(self.tempdir_home, ".org", "orgs")
        self.assertIn("foo", keychain.get_org("test").config)

    def test_load_file(self):
        dummy_keychain = BaseEncryptedProjectKeychain(self.project_config, self.key)
        self._write_file(os.path.join(self.tempdir_home, "config"), "foo")
        keychain = self.keychain_class(self.project_config, self.key)
        keychain._load_file(self.tempdir_home, "config", "from_file")
        self.assertEqual("foo", keychain.config["from_file"])

    def test_remove_org(self):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_org(self.org_config)
        keychain.remove_org("test")
        self.assertNotIn("test", keychain.orgs)

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
