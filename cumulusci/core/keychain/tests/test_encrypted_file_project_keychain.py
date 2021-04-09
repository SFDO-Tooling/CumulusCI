import json
import pytest
import tempfile

from pathlib import Path
from unittest import mock

from cumulusci.core.exceptions import (
    CumulusCIException,
    OrgNotFound,
    ServiceNotConfigured,
)
from cumulusci.core.keychain import EncryptedFileProjectKeychain
from cumulusci.core.keychain.encrypted_file_project_keychain import GlobalOrg
from cumulusci.core.config import (
    BaseConfig,
    OrgConfig,
    ServiceConfig,
    UniversalConfig,
)


@pytest.fixture()
def keychain(project_config, key) -> EncryptedFileProjectKeychain:
    keychain = EncryptedFileProjectKeychain(project_config, key)
    assert keychain.project_config == project_config
    assert keychain.key == key
    return keychain


class TestEncryptedFileProjectKeychain:

    project_name = "TestProject"

    def _write_file(self, filepath, contents):
        with open(filepath, "w") as f:
            f.write(contents)

    def _default_org_path(self, keychain: EncryptedFileProjectKeychain):
        return Path(keychain.global_config_dir, "TestProject/DEFAULT_ORG.txt")

    def test_cache_dir(self, keychain):
        assert keychain.cache_dir.name == ".cci"

    def test_raise_service_not_configured(self, keychain):
        with pytest.raises(ServiceNotConfigured):
            keychain._raise_service_not_configured("test-name")

    #######################################
    #               Orgs                  #
    #######################################

    def test_set_and_get_org__global(self, keychain, org_config):
        org_config.global_org = True
        keychain.set_org(org_config, True)
        assert list(keychain.orgs.keys()) == ["test"]
        assert keychain.get_org("test").config == org_config.config

    def test_set_and_get_org__universal_config(self, key, org_config):
        keychain = EncryptedFileProjectKeychain(UniversalConfig(), key)
        keychain.set_org(org_config, False)
        assert list(keychain.orgs.keys()) == []

    def test_load_files__org_empty(self, keychain):
        self._write_file(
            Path(keychain.global_config_dir, "test.org"),
            keychain._encrypt_config(BaseConfig({"foo": "bar"})).decode("utf-8"),
        )

        del keychain.config["orgs"]
        keychain._load_orgs()
        assert "foo" in keychain.get_org("test").config
        assert keychain.get_org("test").keychain == keychain

    @mock.patch("cumulusci.core.utils.cleanup_org_cache_dirs")
    def test_remove_org(
        self, cleanup_org_cache_dirs, keychain, org_config, project_config
    ):
        keychain.set_org(org_config)
        keychain.remove_org("test")
        assert "test" not in keychain.orgs
        assert cleanup_org_cache_dirs.called_once_with(keychain, project_config)

    def test_remove_org__not_found(self, keychain):
        keychain.orgs["test"] = mock.Mock()
        with pytest.raises(OrgNotFound):
            keychain.remove_org("test")

    def test_remove_org__global_not_found(self, keychain):
        keychain.orgs["test"] = mock.Mock()
        with pytest.raises(OrgNotFound):
            keychain.remove_org("test", True)

    def test_set_and_get_org_local_should_not_shadow_global(
        self,
        keychain,
        org_config,
        project_config,
        key,
    ):
        global_org = True
        org_config.global_org = global_org
        keychain.set_org(org_config, global_org)
        assert ["test"] == list(keychain.orgs.keys())
        assert isinstance(keychain.orgs["test"], GlobalOrg), keychain.orgs["test"]
        assert org_config.config == keychain.get_org("test").config
        assert Path(keychain.global_config_dir, "test.org").exists()

        # check that it saves to the right place
        with mock.patch(
            "cumulusci.core.keychain.encrypted_file_project_keychain.open"
        ) as o:
            org_config.save()
            opened_file = o.mock_calls[0][1][0]
            assert opened_file.parent.name == ".cumulusci"
            assert opened_file.name == "test.org"

        # check that it can be loaded in a fresh keychain
        new_keychain = EncryptedFileProjectKeychain(project_config, key)
        org_config = new_keychain.get_org("test")
        assert org_config.global_org

    def test_get_default_org__with_files(self, keychain, org_config):
        org_config = OrgConfig(org_config.config.copy(), "test", keychain=keychain)
        org_config.save()
        with open(self._default_org_path(keychain), "w") as f:
            f.write("test")
        try:
            assert keychain.get_default_org()[1].config == org_config.config
        finally:
            self._default_org_path(keychain).unlink()

    def test_get_default_org__with_files__missing_org(self, keychain):
        with open(self._default_org_path(keychain), "w") as f:
            f.write("should_not_exist")
        assert self._default_org_path(keychain).exists()
        assert keychain.get_default_org() == (None, None)
        assert not self._default_org_path(keychain).exists()

    @mock.patch("sarge.Command")
    def test_set_default_org__with_files(self, Command, keychain, org_config):
        org_config = OrgConfig(org_config.config.copy(), "test")
        keychain.set_org(org_config)
        keychain.set_default_org("test")
        with open(self._default_org_path(keychain)) as f:
            assert f.read() == "test"
        self._default_org_path(keychain).unlink()

    @mock.patch("sarge.Command")
    def test_unset_default_org__with_files(self, Command, keychain, org_config):
        org_config = org_config.config.copy()
        org_config = OrgConfig(org_config, "test")
        keychain.set_org(org_config)
        keychain.set_default_org("test")
        keychain.unset_default_org()
        assert keychain.get_default_org()[1] is None
        assert not self._default_org_path(keychain).exists()

    # old way of finding defaults used contents of the files themselves
    # we should preserve backwards compatibiliity for a few months
    def test_get_default_org__file_missing_fallback(self, keychain, org_config):
        org_config = OrgConfig(org_config.config.copy(), "test", keychain=keychain)
        org_config.config["default"] = True
        org_config.save()
        assert keychain.get_default_org()[1].config == org_config.config

    def test_get_default_org__outside_project(self, keychain):
        assert keychain.get_default_org() == (None, None)

    #######################################
    #              Services               #
    #######################################

    def test_load_service_files(self, keychain):
        github_service_path = Path(f"{keychain.global_config_dir}/services/github")
        self._write_file(
            Path(github_service_path / "alias.service"),
            keychain._encrypt_config(BaseConfig({"foo": "bar"})).decode("utf-8"),
        )

        del keychain.config["services"]

        with mock.patch.object(
            EncryptedFileProjectKeychain,
            "global_config_dir",
            keychain.global_config_dir,
        ):
            keychain._load_service_files()
        github_service = keychain.get_service("github", "alias")
        assert "foo" in github_service.config

    def test_set_service_github(self, keychain, service_config):
        keychain.set_service("github", "alias", service_config)
        default_github_service = keychain.get_service("github")

        assert default_github_service.config == {
            **service_config.config,
            "token": "test123",
        }

    def test_set_service__first_should_be_default(self, keychain):
        keychain.set_service("github", "foo_github", ServiceConfig({"name": "foo"}))
        keychain.set_service("github", "bar_github", ServiceConfig({"name": "bar"}))

        github_service = keychain.get_service("github")
        assert github_service.config == {"name": "foo"}

    def test_set_default_service(self, keychain):
        keychain.set_service("github", "foo_github", ServiceConfig({"name": "foo"}))
        keychain.set_service("github", "bar_github", ServiceConfig({"name": "bar"}))

        github_service = keychain.get_service("github")
        assert github_service.config == {"name": "foo"}
        # now set default to bar
        keychain.set_default_service("github", "bar_github")
        github_service = keychain.get_service("github")
        assert github_service.config == {"name": "bar"}

    def test_set_default_service__service_alredy_default(self, keychain):
        keychain.set_service("github", "foo_github", ServiceConfig({"name": "foo"}))
        github_service = keychain.get_service("github")
        assert github_service.config == {"name": "foo"}

        keychain.set_default_service("github", "foo_github")

        github_service = keychain.get_service("github")
        assert github_service.config == {"name": "foo"}

    def test_set_default_service__no_such_service(self, keychain):
        with pytest.raises(ServiceNotConfigured):
            keychain.set_default_service("fooey", "alias")

    def test_set_default_service__no_such_alias(self, keychain):
        keychain.set_service("github", "foo_github", ServiceConfig({"name": "foo"}))
        with pytest.raises(ServiceNotConfigured):
            keychain.set_default_service("github", "wrong_alias")

    def test_save_default_service__global_default_service(self, keychain):
        with open(Path(keychain.global_config_dir, "DEFAULT_SERVICES.json"), "w") as f:
            f.write(
                json.dumps({"devhub": "current_default", "github": "current_default"})
            )

        keychain._save_default_service("github", "new_default", project=False)

        with open(Path(keychain.global_config_dir, "DEFAULT_SERVICES.json"), "r") as f:
            default_services = json.loads(f.read())

        assert default_services["devhub"] == "current_default"
        assert default_services["github"] == "new_default"

        with open(Path(keychain.project_local_dir, "DEFAULT_SERVICES.json"), "r") as f:
            project_defaults = json.loads(f.read())

        assert project_defaults == {}

    def test_save_default_service__project_default_service(self, keychain):
        with open(Path(keychain.project_local_dir, "DEFAULT_SERVICES.json"), "w") as f:
            f.write(
                json.dumps({"devhub": "current_default", "github": "current_default"})
            )

        keychain._save_default_service("github", "new_default", project=True)

        with open(Path(keychain.project_local_dir, "DEFAULT_SERVICES.json"), "r") as f:
            default_services = json.loads(f.read())

        assert default_services["devhub"] == "current_default"
        assert default_services["github"] == "new_default"

        with open(Path(keychain.global_config_dir, "DEFAULT_SERVICES.json"), "r") as f:
            global_defaults = json.loads(f.read())

        assert global_defaults == {}

    def test_iter_local_project_dirs(self, keychain):
        cci_home_dir = Path(keychain.global_config_dir)
        (cci_home_dir / "logs").mkdir()
        (cci_home_dir / "chewy").mkdir()
        (cci_home_dir / "yoshi").mkdir()
        # services/ and TestProject/ are also presenct in ~/.cumulusci

        local_project_dirs = list(keychain._iter_local_project_dirs())
        assert cci_home_dir / "TestProject" in local_project_dirs
        assert cci_home_dir / "chewy" in local_project_dirs
        assert cci_home_dir / "yoshi" in local_project_dirs

    def test_create_default_services_files__without_project_service(self, key):
        home_dir = tempfile.mkdtemp()
        cci_home_dir = Path(f"{home_dir}/.cumulusci")
        cci_home_dir.mkdir(parents=True)

        self._write_file(cci_home_dir / "devhub.service", "<encrypted devhub config>")
        self._write_file(cci_home_dir / "github.service", "<encrypted github config>")

        # local project dir without a .service file
        (cci_home_dir / "test-project").mkdir()
        # we should ignore everything in the log dir
        log_dir = cci_home_dir / "logs"
        log_dir.mkdir()
        self._write_file(log_dir / "connected_app.service", "<encrypted config>")

        with mock.patch.object(
            EncryptedFileProjectKeychain, "global_config_dir", cci_home_dir
        ):
            # _create_default_services_files() invoked via __init__
            EncryptedFileProjectKeychain(UniversalConfig(), key)

        default_services_file = cci_home_dir / "DEFAULT_SERVICES.json"
        with open(default_services_file, "r") as f:
            default_services = json.loads(f.read())

        assert len(default_services.keys()) == 2  # we shouldn't get connected_app
        assert default_services["devhub"] == "devhub__global"
        assert default_services["github"] == "github__global"

        project_default_services_file = Path(
            f"{cci_home_dir}/test-project/DEFAULT_SERVICES.json"
        )
        with open(project_default_services_file, "r") as f:
            assert json.loads(f.read()) == {}

    def test_create_default_services_files__with_project_service(self, key):
        home_dir = tempfile.mkdtemp()
        cci_home_dir = Path(f"{home_dir}/.cumulusci")
        cci_home_dir.mkdir(parents=True)

        self._write_file(cci_home_dir / "devhub.service", "<encrypted devhub config>")
        self._write_file(cci_home_dir / "github.service", "<encrypted github config>")

        project_path = cci_home_dir / "test-project"
        project_path.mkdir(parents=True)
        self._write_file(project_path / "github.service", "project level github config")

        with mock.patch.object(
            EncryptedFileProjectKeychain, "global_config_dir", cci_home_dir
        ):
            # _create_default_services_files invoked via __init__
            EncryptedFileProjectKeychain(UniversalConfig(), key)

        global_default_services_file = Path(f"{cci_home_dir}/DEFAULT_SERVICES.json")
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
        assert default_services["github"] == "github__test-project"

    def test_create_services_dir_structure(self, key):
        service_types = list(UniversalConfig().config["services"].keys())
        num_services = len(service_types)

        # _create_services_dir_structure() is invoked via constructor
        keychain = EncryptedFileProjectKeychain(UniversalConfig(), key)

        services_path = Path(f"{keychain.global_config_dir}/services")
        for path in Path.iterdir(services_path):
            if path.name in service_types:
                assert Path.is_dir(path)
                service_types.remove(path.name)

        assert len(service_types) == 0

        # explicitly invoke a second time to test idempotency
        keychain._create_services_dir_structure()
        # make sure no new dirs appeared
        assert num_services == len(list(Path.iterdir(services_path)))

    def test_migrate_services(self, key, project_config):
        home_dir = tempfile.mkdtemp()
        cci_home_dir = Path(f"{home_dir}/.cumulusci")
        cci_home_dir.mkdir(parents=True)

        self._write_file(cci_home_dir / "github.service", "github config")
        self._write_file(cci_home_dir / "foo.service", "foo config")

        local_proj_dir = cci_home_dir / "test-project"
        local_proj_dir.mkdir()
        self._write_file(local_proj_dir / "github.service", "github2 config")

        with mock.patch.object(
            EncryptedFileProjectKeychain, "global_config_dir", cci_home_dir
        ):
            # _migrade_services() invoked via __init__
            EncryptedFileProjectKeychain(project_config, key)

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

    def test_migrate_services__warn_duplicate_default_service(
        self, project_config, key
    ):
        home_dir = tempfile.mkdtemp()
        cci_home_dir = Path(f"{home_dir}/.cumulusci")
        cci_home_dir.mkdir(parents=True)

        # make unnamed devhub service
        legacy_devhub_service = Path(f"{cci_home_dir}/devhub.service")
        self._write_file(legacy_devhub_service, "legacy config")
        # make existing default aliased devhub service
        named_devhub_service = Path(f"{cci_home_dir}/services/devhub/")
        named_devhub_service.mkdir(parents=True)
        self._write_file(
            f"{named_devhub_service}/devhub__global.service", "migrated config"
        )

        with mock.patch.object(
            EncryptedFileProjectKeychain, "global_config_dir", cci_home_dir
        ):
            # _migrate_services() invoked via __init__
            EncryptedFileProjectKeychain(project_config, key)

        # ensure this file wasn't removed
        assert legacy_devhub_service.is_file()
        # ensure contents of migrated are unchanged
        with open(named_devhub_service / "devhub__global.service", "r") as f:
            assert f.read() == "migrated config"

    def test_rename_service(self, keychain, service_config):
        home_dir = tempfile.mkdtemp()

        cci_home_dir = Path(f"{home_dir}/.cumulusci")
        cci_home_dir.mkdir()
        with open(cci_home_dir / "DEFAULT_SERVICES.json", "w") as f:
            f.write(json.dumps({"github": "old_alias"}))

        local_project_dir = cci_home_dir / "test-project"
        local_project_dir.mkdir()
        with open(local_project_dir / "DEFAULT_SERVICES.json", "w") as f:
            f.write(json.dumps({"github": "old_alias"}))

        github_services_dir = Path(f"{home_dir}/.cumulusci/services/github")
        github_services_dir.mkdir(parents=True)
        self._write_file(github_services_dir / "old_alias.service", "github config")

        encrypted = keychain._encrypt_config(service_config)
        keychain.services = {"github": {"old_alias": encrypted}}
        with mock.patch.object(
            EncryptedFileProjectKeychain, "global_config_dir", cci_home_dir
        ):
            keychain.rename_service("github", "old_alias", "new_alias")

        # Getting old alias should fail
        with pytest.raises(KeyError):
            keychain.get_service("github", "old_alias")

        # Validate new alias has same contents as original
        assert keychain.get_service("github", "new_alias").config == {
            **service_config.config,
            "token": "test123",
        }
        # Old service file should be gone
        assert not (github_services_dir / "old_alias.service").is_file()
        # New service file should be present
        assert (github_services_dir / "new_alias.service").is_file()

        # DEFAULT_SERVICES.json files should have updated aliases
        with open(local_project_dir / "DEFAULT_SERVICES.json", "r") as f:
            assert json.loads(f.read()) == {"github": "new_alias"}

        with open(cci_home_dir / "DEFAULT_SERVICES.json", "r") as f:
            assert json.loads(f.read()) == {"github": "new_alias"}

    def test_rename_service__invalid_service_type(self, keychain, service_config):
        with pytest.raises(ServiceNotConfigured):
            keychain.rename_service("does-not-exist", "old_alias", "new_alias")

    def test_rename_service__invalid_service_alias(self, keychain, service_config):
        keychain.services = {"github": {"current_alias": "some config"}}
        with pytest.raises(ServiceNotConfigured):
            keychain.rename_service("github", "does-not-exist", "new_alias")

    def test_rename_alias_in_default_service_file__no_default_present(self, keychain):
        filepath = Path(f"{keychain.global_config_dir}/DEFAULT_SERVICES.json")
        with open(filepath, "w") as f:
            f.write(json.dumps({"saucelabs": "default_alias"}))
        keychain._rename_alias_in_default_service_file(
            filepath, "github", "current_alias", "new_alias"
        )

        with open(filepath, "r") as f:
            assert json.loads(f.read()) == {"saucelabs": "default_alias"}

    def test_read_default_services(self, keychain):
        expected_defaults = {
            "github": "github_alias",
            "apextestdb": "apextestdb_alias",
            "metaci": "metaci_alias",
            "devhub": "devhub_alias",
            "connected_app": "connected_app__alias",
        }
        filepath = Path(f"{keychain.global_config_dir}/DEFAULT_SERVICES.json")
        with open(filepath, "w") as f:
            f.write(json.dumps(expected_defaults))

        actual_defaults = keychain._read_default_services(filepath)
        assert actual_defaults == expected_defaults

    def test_read_default_services__file_does_not_exist(self, keychain):
        with pytest.raises(CumulusCIException):
            keychain._read_default_services(Path("not-a-valid-filepath"))

    def test_write_default_services(self, keychain):
        expected_defaults = {
            "github": "github_alias",
            "apextestdb": "apextestdb_alias",
            "metaci": "metaci_alias",
            "devhub": "devhub_alias",
            "connected_app": "connected_app__alias",
        }
        filepath = Path(f"{keychain.global_config_dir}/DEFAULT_SERVICES.json")
        keychain._write_default_services(filepath, expected_defaults)

        with open(filepath, "r") as f:
            actual_defaults = json.loads(f.read())
        assert actual_defaults == expected_defaults

    def test_write_default_services__bad_filename(self, keychain):
        filepath = Path("DEFAULT_THINGS.json")
        with pytest.raises(CumulusCIException):
            keychain._write_default_services(filepath, {})
