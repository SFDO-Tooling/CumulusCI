import json
import os
import pytest
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
from cumulusci.core.exceptions import OrgNotFound, ServiceNotValid, ServiceNotConfigured
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

    def test_set_and_get_org(self, global_org=False):
        keychain = self.keychain_class(self.project_config, self.key)
        self.org_config.global_org = global_org
        keychain.set_org(self.org_config, global_org)
        assert list(keychain.orgs.keys()) == ["test"]
        assert keychain.get_org("test").config == self.org_config.config

    def test_set_service_github(self, project=False):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_service(
            "github", "alias", self.services["github"], project=project
        )
        github_service = keychain.get_service("github", "alias")
        assert github_service.config == self.services["github"].config


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

    def test_set_and_get_org_global(self):
        self.test_set_and_get_org(True)

    def test_set_and_get_org__universal_config(self):
        keychain = self.keychain_class(self.universal_config, self.key)
        keychain.set_org(self.org_config, False)
        assert list(keychain.orgs.keys()) == []

    def test_load_files__org_empty(self):
        dummy_keychain = BaseEncryptedProjectKeychain(self.project_config, self.key)
        local_project_dir = Path(f"{self.tempdir_home}/.cumulusci/{self.project_name}")
        local_project_dir.mkdir(parents=True)
        self._write_file(
            Path(f"{self.tempdir_home}/test.org"),
            dummy_keychain._encrypt_config(BaseConfig({"foo": "bar"})).decode("utf-8"),
        )
        keychain = self.keychain_class(self.project_config, self.key)
        del keychain.config["orgs"]
        with mock.patch.object(
            self.keychain_class, "global_config_dir", Path(self.tempdir_home)
        ):
            keychain._load_orgs()
        assert "foo" in keychain.get_org("test").config
        assert keychain.get_org("test").keychain == keychain

    def test_load_service_files(self):
        dummy_keychain = BaseEncryptedProjectKeychain(self.project_config, self.key)
        github_service_path = Path(f"{self.tempdir_home}/.cumulusci/services/github")
        github_service_path.mkdir(parents=True)
        self._write_file(
            Path(github_service_path / "alias.service"),
            dummy_keychain._encrypt_config(BaseConfig({"foo": "bar"})).decode("utf-8"),
        )

        keychain = self.keychain_class(self.project_config, self.key)
        del keychain.config["services"]

        keychain._load_service_files()

        github_service = keychain.get_service("github", "alias")
        assert "foo" in github_service.config

    def test_load_file(self):
        self._write_file(Path(f"{self.tempdir_home}/config"), "foo")
        keychain = self.keychain_class(self.project_config, self.key)
        keychain._load_app_file(self.tempdir_home, "config", "from_file")
        assert "foo" == keychain.config["from_file"]

    def test_load_file__universal_config(self):
        self._write_file(Path(f"{self.tempdir_home}/config"), "foo")
        keychain = self.keychain_class(self.project_config, self.key)
        keychain._load_app_file(self.tempdir_home, "config", "from_file")
        assert "foo" == keychain.config["from_file"]

    @mock.patch("cumulusci.core.utils.cleanup_org_cache_dirs")
    def test_remove_org(self, cleanup_org_cache_dirs):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_org(self.org_config)
        keychain.remove_org("test")
        assert "test" not in keychain.orgs
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

    def test_iter_local_project_dirs(self):
        cci_home_dir = Path(f"{self.tempdir_home}/.cumulusci")
        (cci_home_dir / "logs").mkdir()
        (cci_home_dir / "services").mkdir()
        (cci_home_dir / "chewy").mkdir()
        (cci_home_dir / "yoshi").mkdir()

        keychain = self.keychain_class(self.universal_config, self.key)
        local_project_dirs = list(keychain._iter_local_project_dirs())

        assert local_project_dirs == [cci_home_dir / "chewy", cci_home_dir / "yoshi"]

    def test_create_default_services_files__without_project_service(self):
        cci_home_dir = Path(f"{self.tempdir_home}/.cumulusci")

        self._write_file(cci_home_dir / "devhub.service", "<encrypted devhub config>")
        self._write_file(cci_home_dir / "github.service", "<encrypted github config>")

        # local project dir without a .service file
        (cci_home_dir / "test-project").mkdir()
        # we should ignore everything in the log dir
        log_dir = cci_home_dir / "logs"
        log_dir.mkdir()
        self._write_file(log_dir / "connected_app.service", "<encrypted config>")

        # _create_default_services_files() invoked via __init__
        keychain = self.keychain_class(self.universal_config, self.key)

        default_services_file = keychain.global_config_dir / "DEFAULT_SERVICES.json"
        with open(default_services_file, "r") as f:
            default_services = json.loads(f.read())

        assert len(default_services.keys()) == 2  # we shouldn't get connected_app
        assert default_services["devhub"] == "devhub__global"
        assert default_services["github"] == "github__global"

        project_default_services_file = Path(
            f"{keychain.global_config_dir}/test-project/DEFAULT_SERVICES.json"
        )
        with open(project_default_services_file, "r") as f:
            assert json.loads(f.read()) == {}

    def test_create_default_services_files__with_project_service(self):
        cci_home_dir = Path(f"{self.tempdir_home}/.cumulusci")

        self._write_file(cci_home_dir / "devhub.service", "<encrypted devhub config>")
        self._write_file(cci_home_dir / "github.service", "<encrypted github config>")

        project_path = cci_home_dir / "test-project"
        project_path.mkdir(parents=True)
        self._write_file(project_path / "github.service", "project level github config")

        # _create_default_services_files invoked via __init__
        keychain = self.keychain_class(self.universal_config, self.key)

        global_default_services_file = Path(
            f"{keychain.global_config_dir}/DEFAULT_SERVICES.json"
        )
        assert global_default_services_file.is_file()
        with open(global_default_services_file, "r") as f:
            default_services = json.loads(f.read())

        assert len(default_services.keys()) == 2
        assert default_services["github"] == "github__global"
        assert default_services["devhub"] == "devhub__global"

        project_default_services_file = project_path / "DEFAULT_SERVICES.json"
        assert project_default_services_file.is_file()
        with open(project_default_services_file, "r") as f:
            default_services = json.loads(f.read())

        assert len(default_services.keys()) == 1
        assert default_services["github"] == "github__project"

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
        keychain._create_services_dir_structure()
        # make sure no new dirs appeared
        assert num_services == len(list(Path.iterdir(services_path)))

    def test_migrate_services(self):
        cci_home_dir = Path(f"{self.tempdir_home}/.cumulusci")
        self._write_file(cci_home_dir / "github.service", "github config")
        self._write_file(cci_home_dir / "foo.service", "foo config")

        local_proj_dir = cci_home_dir / "test-project"
        local_proj_dir.mkdir()
        self._write_file(local_proj_dir / "github.service", "github2 config")

        # _migrade_services() invoked via __init__
        self.keychain_class(self.project_config, self.key)

        assert not Path.is_file(cci_home_dir / "github.service")
        assert (cci_home_dir / "services/github/github__global.service").is_file()
        with open(cci_home_dir / "services/github/github__global.service") as f:
            assert f.read() == "github config"

        assert not Path.is_file(cci_home_dir / "test-project/devhub.service")
        assert (cci_home_dir / "services/github/github__project.service").is_file()
        with open(cci_home_dir / "services/github/github__project.service") as f:
            assert f.read() == "github2 config"

        # unrecognized services should be left alone
        assert (cci_home_dir / "foo.service").is_file()

    def test_migrate_services__warn_duplicate_default_service(self):
        # make unaliased devhub service
        legacy_devhub_service = Path(f"{self.tempdir_home}/.cumulusci/devhub.service")
        self._write_file(legacy_devhub_service, "legacy config")
        # make existing default aliased devhub service
        named_devhub_service = Path(f"{self.tempdir_home}/.cumulusci/services/devhub/")
        named_devhub_service.mkdir(parents=True)
        self._write_file(
            f"{named_devhub_service}/devhub__global.service", "migrated config"
        )

        # _migrate_services() invoked via __init__
        self.keychain_class(self.universal_config, self.key)

        # ensure we don't remove this service file
        assert legacy_devhub_service.is_file()
        # ensure contents of migrated are unchanged
        with open(named_devhub_service / "devhub__global.service", "r") as f:
            assert f.read() == "migrated config"

    def test_set_service__first_should_be_default(self):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_service("github", "foo_github", ServiceConfig({"git": "foo"}))
        keychain.set_service("github", "bar_github", ServiceConfig({"git": "bar"}))

        github_service = keychain.get_service("github")
        assert github_service.config == {"git": "foo"}

    def test_set_default_service(self):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_service("github", "foo_github", ServiceConfig({"git": "foo"}))
        keychain.set_service("github", "bar_github", ServiceConfig({"git": "bar"}))

        github_service = keychain.get_service("github")
        assert github_service.config == {"git": "foo"}
        # now set default to bar
        keychain.set_default_service("github", "bar_github")
        github_service = keychain.get_service("github")
        assert github_service.config == {"git": "bar"}

    def test_set_default_service__no_such_service(self):
        keychain = self.keychain_class(self.project_config, self.key)
        with pytest.raises(ServiceNotValid):
            keychain.set_default_service("fooey", "alias")

    def test_set_default_service__no_such_alias(self):
        keychain = self.keychain_class(self.project_config, self.key)
        keychain.set_service("github", "foo_github", ServiceConfig({"git": "foo"}))
        with pytest.raises(ServiceNotConfigured):
            keychain.set_default_service("github", "wrong_alias")
