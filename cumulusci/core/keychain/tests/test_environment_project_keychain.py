import json
import os
import unittest

from cumulusci.core.config import UniversalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import ScratchOrgConfig
from cumulusci.core.config import ServiceConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.keychain import EnvironmentProjectKeychain
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

    def test_get_org_not_found(self):
        keychain = self.keychain_class(self.project_config, self.key)
        with self.assertRaises(OrgNotFound):
            keychain.get_org("test")

    def test_list_orgs_empty(self):
        keychain = self.keychain_class(self.project_config, self.key)
        assert keychain.list_orgs() == []

    def test_set_and_get_org(self, global_org=False):
        keychain = self.keychain_class(self.project_config, self.key)
        self.org_config.global_org = global_org
        keychain.set_org(self.org_config, global_org)
        assert list(keychain.orgs.keys()) == ["test"]
        assert keychain.get_org("test").config == self.org_config.config

    def test_set_service_github(self, project=False):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_service("github", "alias", self.services["github"])
        github_service = keychain.get_service("github", "alias")
        assert github_service.config == self.services["github"].config

    def test_load_scratch_orgs_create_one(self):
        self.project_config.config["orgs"] = {}
        self.project_config.config["orgs"]["scratch"] = {}
        self.project_config.config["orgs"]["scratch"]["test_scratch_auto"] = {}
        keychain = self.keychain_class(self.project_config, self.key)
        assert list(keychain.orgs) == ["test_scratch_auto"]

    def test_load_scratch_orgs_none(self):
        keychain = self.keychain_class(self.project_config, self.key)
        assert list(keychain.orgs) == []

    def test_get_default_org(self):
        keychain = self.keychain_class(self.project_config, self.key)
        org_config = self.org_config.config.copy()
        org_config = OrgConfig(org_config, "test", keychain=keychain)
        org_config.save()
        keychain.set_default_org("test")
        org_config.config["default"] = True
        assert keychain.get_default_org()[1].config == org_config.config

    def test_set_and_get_scratch_org(self, global_org=False):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_org(self.scratch_org_config, global_org)
        self.assertEqual(list(keychain.orgs.keys()), ["test_scratch"])
        org = keychain.get_org("test_scratch")
        assert org.config == self.scratch_org_config.config
        assert org.__class__ == ScratchOrgConfig


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

    def test_get_org(self):
        keychain = self.keychain_class(self.project_config, self.key)
        assert list(keychain.orgs.keys()) == ["test"]
        assert keychain.get_org("test").config == self.org_config.config

    def test_get_org_not_found(self):
        self._clean_env(self.env)
        super(TestEnvironmentProjectKeychain, self).test_get_org_not_found()

    def test_list_orgs(self):
        keychain = self.keychain_class(self.project_config, self.key)
        assert keychain.list_orgs() == ["test"]

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
        assert keychain.list_orgs() == ["test"]
        assert keychain.orgs["test"].__class__, ScratchOrgConfig

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
        """The EnvironmentProjectKeychain does not persist default org settings"""
        org_config = self.org_config.config.copy()
        self.env.set(
            f"{self.keychain_class.org_var_prefix}test", json.dumps(org_config)
        )
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_default_org("test")
        expected_org_config = self.org_config.config.copy()
        expected_org_config["default"] = True

        assert keychain.get_default_org()[1] is None

    def test_set_and_get_scratch_org(self):
        self._clean_env(self.env)
        super(TestEnvironmentProjectKeychain, self).test_set_and_get_scratch_org()
