import datetime
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from cumulusci.core import utils
from cumulusci.core.config import (
    BaseConfig,
    OrgConfig,
    ScratchOrgConfig,
    ServiceConfig,
    UniversalConfig,
)
from cumulusci.core.config.marketing_cloud_service_config import (
    MarketingCloudServiceConfig,
)
from cumulusci.core.config.sfdx_org_config import SfdxOrgConfig
from cumulusci.core.exceptions import (
    ConfigError,
    CumulusCIException,
    CumulusCIUsageError,
    KeychainKeyNotFound,
    OrgNotFound,
    ServiceNotConfigured,
    ServiceNotValid,
)
from cumulusci.core.keychain import EncryptedFileProjectKeychain
from cumulusci.core.keychain.base_project_keychain import (
    DEFAULT_CONNECTED_APP,
    DEFAULT_CONNECTED_APP_NAME,
)
from cumulusci.core.keychain.encrypted_file_project_keychain import (
    SERVICE_ORG_FILE_MODE,
    GlobalOrg,
)
from cumulusci.core.keychain.serialization import (
    _simplify_config,
    load_config_from_json_or_pickle,
)
from cumulusci.core.tests.utils import EnvironmentVarGuard
from cumulusci.utils import temporary_dir


@pytest.fixture(params=[True, False])
def withdifferentformats(request):
    SHOULD_SAVE_AS_JSON = request.param
    with mock.patch(
        "cumulusci.core.keychain.serialization.SHOULD_SAVE_AS_JSON", request.param
    ):
        yield "json" if SHOULD_SAVE_AS_JSON else "pickle"


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

    def test_set_and_get_org__global(
        self, keychain, org_config, key, withdifferentformats
    ):
        org_config.global_org = True
        keychain.set_org(org_config, True)
        assert list(keychain.orgs.keys()) == ["test"]
        assert _simplify_config(keychain.get_org("test").config) == org_config.config

    def test_get_org__with_config_properly_overridden(
        self, keychain, scratch_org_config
    ):
        days = 16
        config_file = "./foo/bar/baz"
        scratch_org_config.global_org = True
        # the orgs encrypted file has the default value for days and config_file
        keychain.set_org(scratch_org_config, True)
        # but this particular scratch org has days and config_file specified via cumulusci.yml
        keychain.project_config.config = {
            "orgs": {"scratch": {"test": {"days": days, "config_file": config_file}}}
        }
        org = keychain.get_org("test")

        # ensure what is configured in cumulusci.yml is what is loaded into the config
        assert org.config["days"] == days
        assert org.config["config_file"] == config_file

    def test_get_org__not_found(self, keychain):
        org_name = "mythical"
        error_message = f"Org with name '{org_name}' does not exist."
        with pytest.raises(OrgNotFound, match=error_message):
            keychain.get_org(org_name)

    def test_set_org__no_key_should_save_to_unencrypted_file(
        self, keychain, org_config
    ):
        keychain.key = None
        keychain.set_org(org_config)

        filepath = Path(keychain.project_local_dir, "test.org")
        with open(filepath, "rb") as f:
            assert load_config_from_json_or_pickle(f.read()) == {
                **org_config.config,
                # still the default for now
                "serialization_format": "pickle",
            }

    def test_set_org__should_not_save_when_environment_project_keychain_set(
        self, keychain, org_config, withdifferentformats
    ):
        with temporary_dir() as temp:
            env = EnvironmentVarGuard()
            with EnvironmentVarGuard() as env:
                env.set("CUMULUSCI_KEYCHAIN_CLASS", "EnvironmentProjectKeychain")
                with mock.patch.object(
                    EncryptedFileProjectKeychain, "project_local_dir", temp
                ):
                    keychain.set_org(org_config, global_org=False)

            actual_org = keychain.get_org("test")
            assert actual_org.config == {
                **org_config.config,
                "serialization_format": withdifferentformats,
            }
            assert not Path(temp, "test.org").is_file()

    @mock.patch("cumulusci.core.keychain.encrypted_file_project_keychain.open")
    def test_save_org_when_no_project_local_dir_present(
        self, mock_open, keychain, org_config
    ):
        with mock.patch.object(EncryptedFileProjectKeychain, "project_local_dir", None):
            keychain._save_org("alias", org_config, global_org=False)
        assert mock_open.call_count == 0

    def test_load_files__org_empty(self, keychain):
        self._write_file(
            Path(keychain.global_config_dir, "test.org"),
            keychain._get_config_bytes(BaseConfig({"foo": "bar"})).decode("utf-8"),
        )

        del keychain.config["orgs"]
        keychain._load_orgs()
        assert "foo" in keychain.get_org("test").config
        assert keychain.get_org("test").keychain == keychain

    def test_remove_org(self, keychain, org_config):
        keychain.set_org(org_config)
        keychain.remove_org("test")
        assert "test" not in keychain.orgs

    def test_remove_org__not_found(self, keychain):
        keychain.orgs["test"] = mock.Mock()
        with pytest.raises(OrgNotFound):
            keychain.remove_org("test")

    def test_remove_org__global_not_found(self, keychain):
        keychain.orgs["test"] = mock.Mock()
        with pytest.raises(OrgNotFound):
            keychain.remove_org("test", True)

    def test_set_and_get_org_local_should_not_shadow_global(
        self, keychain, org_config, project_config, key, withdifferentformats
    ):
        global_org = True
        org_config.global_org = global_org
        keychain.set_org(org_config, global_org)
        assert ["test"] == list(keychain.orgs.keys())
        assert isinstance(keychain.orgs["test"], GlobalOrg), keychain.orgs["test"]
        test_config = keychain.get_org("test").config
        assert {
            **org_config.config,
            "serialization_format": withdifferentformats,
        } == test_config

        org_filepath = Path(keychain.global_config_dir, "test.org")
        assert org_filepath.exists()

        # os.stat returns something different on windows
        # so only check this on osx/linux
        if not sys.platform.startswith("win"):
            # ensure expected file permissions
            stat_result = os.stat(org_filepath)
            actual_mode = oct(stat_result.st_mode & 0o777)
            assert actual_mode == oct(SERVICE_ORG_FILE_MODE)

        # check that it saves to the right place
        with mock.patch(
            "cumulusci.core.keychain.encrypted_file_project_keychain.os.open"
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
            assert (
                _simplify_config(keychain.get_default_org()[1].config)
                == org_config.config
            )
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
        assert (
            _simplify_config(keychain.get_default_org()[1].config) == org_config.config
        )

    def test_get_default_org__outside_project(self, keychain):
        assert keychain.get_default_org() == (None, None)

    def test_load_orgs_from_environment(self, keychain, org_config):
        scratch_config = org_config.config.copy()
        scratch_config["scratch"] = True
        env = EnvironmentVarGuard()
        with EnvironmentVarGuard() as env:
            env.set(
                f"{keychain.env_org_var_prefix}dev",
                json.dumps(scratch_config),
            )
            env.set(
                f"{keychain.env_org_var_prefix}devhub",
                json.dumps(org_config.config),
            )
            keychain._load_orgs_from_environment()

        actual_config = keychain.get_org("dev")
        assert _simplify_config(actual_config.config) == scratch_config
        actual_config = keychain.get_org("devhub")
        assert _simplify_config(actual_config.config) == org_config.config

    #######################################
    #              Services               #
    #######################################

    def test_load_service_files(self, keychain):
        github_service_path = Path(f"{keychain.global_config_dir}/services/github")
        self._write_file(
            Path(github_service_path / "alias.service"),
            keychain._get_config_bytes(BaseConfig({"name": "foo"})).decode("utf-8"),
        )

        # keychain.config["services"] = {}

        with mock.patch.object(
            EncryptedFileProjectKeychain,
            "global_config_dir",
            keychain.global_config_dir,
        ):
            keychain._load_service_files()
        github_service = keychain.get_service("github", "alias")
        assert "foo" in github_service.config["name"]

    def test_load_services__from_env(self, keychain):
        service_config_one = ServiceConfig(
            {"name": "foo1", "password": "1234", "token": "1234"}
        )
        service_config_two = ServiceConfig(
            {"name": "foo2", "password": "5678", "token": "5678"}
        )
        with EnvironmentVarGuard() as env:
            env.set(
                f"{keychain.env_service_var_prefix}github",
                json.dumps(service_config_one.config),
            )
            env.set(
                f"{keychain.env_service_var_prefix}github__OTHER",
                json.dumps(service_config_two.config),
            )
            with pytest.raises(ServiceNotConfigured):
                keychain.get_service("github")

            keychain._load_services_from_environment()

        gh_service = keychain.get_service("github")
        # this also confirms the default service is set appropriately
        assert _simplify_config(gh_service.config) == service_config_one.config
        gh_service = keychain.get_service("github", "env-OTHER")
        assert _simplify_config(gh_service.config) == service_config_two.config

    def test_load_services_from_env__same_name_throws_error(self, keychain):
        keychain.logger = mock.Mock()
        service_prefix = EncryptedFileProjectKeychain.env_service_var_prefix
        service_config = ServiceConfig(
            {"name": "foo", "password": "1234", "token": "1234"}
        )
        with EnvironmentVarGuard() as env:
            env.set(f"{service_prefix}github", json.dumps(service_config.config))
            env.set(f"{service_prefix}github", json.dumps(service_config.config))
            keychain._load_services_from_environment()

        assert 1 == 1

    def test_get_service__built_in_connected_app(self, keychain):
        built_in_connected_app = keychain.get_service("connected_app")
        assert built_in_connected_app is DEFAULT_CONNECTED_APP

    def test_get_service__with_class_path(self, keychain, service_config):
        encrypted = keychain._get_config_bytes(service_config)
        keychain.config["services"]["marketing_cloud"] = {"foo": encrypted}
        mc_service = keychain._get_service("marketing_cloud", "foo")

        assert isinstance(mc_service, MarketingCloudServiceConfig)

    @mock.patch("cumulusci.core.keychain.encrypted_file_project_keychain.import_class")
    def test_get_service__bad_class_path(self, import_class, keychain, service_config):
        import_class.side_effect = AttributeError
        encrypted = keychain._get_config_bytes(service_config)
        keychain.config["services"]["marketing_cloud"] = {"foo": encrypted}

        error_message = "Unrecognized class_path for service: cumulusci.core.config.marketing_cloud_service_config.MarketingCloudServiceConfig"
        with pytest.raises(CumulusCIException, match=error_message):
            keychain._get_service("marketing_cloud", "foo")

    def test_get_service__does_not_exist(self, keychain, service_config):
        keychain.set_service("github", "alias", service_config)
        error_message = "No service of type github exists with the name: does-not-exist"
        with pytest.raises(ServiceNotConfigured, match=error_message):
            keychain.get_service("github", "does-not-exist")

    @pytest.mark.skipif(
        sys.platform.startswith("win"),
        reason="Windows has a different value returned by os.stat",
    )
    def test_set_service_github(self, keychain, service_config):
        keychain.set_service("github", "alias", service_config)
        default_github_service = keychain.get_service("github")

        service_filepath = Path(
            keychain.global_config_dir, "services/github/alias.service"
        )
        assert service_filepath.is_file()

        if not sys.platform.startswith("win"):
            # ensure expected file permissions
            stat_result = os.stat(service_filepath)
            actual_mode = oct(stat_result.st_mode & 0o777)
            assert actual_mode == oct(SERVICE_ORG_FILE_MODE)

        assert default_github_service.config == {
            **service_config.config,
            "token": "test123",
            "serialization_format": "pickle",
        }

    @pytest.mark.skipif(
        not sys.platform.startswith("win"),
        reason="Windows has a different value returned by os.stat",
    )
    def test_set_service_github__windows_has_correct_file_perms(
        self, keychain, service_config
    ):
        keychain.set_service("github", "alias", service_config)

        service_filepath = Path(
            keychain.global_config_dir, "services/github/alias.service"
        )
        assert service_filepath.is_file()

        # ensure expected file permissions
        stat_result = os.stat(service_filepath)
        actual_mode = oct(stat_result.st_mode & 0o777)
        assert actual_mode == "0o666"

    def test_set_service__cannot_overwrite_default_connected_app(self, keychain):
        connected_app_config = ServiceConfig({"test": "foo"})
        error_message = re.escape(
            f"You cannot use the name {DEFAULT_CONNECTED_APP_NAME} for a connected app service. Please select a different name."
        )
        with pytest.raises(ServiceNotValid, match=error_message):
            keychain.set_service(
                "connected_app", DEFAULT_CONNECTED_APP_NAME, connected_app_config
            )

    def test_set_service__first_should_be_default(self, keychain):
        keychain.set_service("github", "foo_github", ServiceConfig({"name": "foo"}))
        keychain.set_service("github", "bar_github", ServiceConfig({"name": "bar"}))

        github_service = keychain.get_service("github")
        assert _simplify_config(github_service.config) == {"name": "foo"}

    def test_set_default_service(self, keychain, withdifferentformats):
        keychain.set_service("github", "foo_github", ServiceConfig({"name": "foo"}))
        keychain.set_service("github", "bar_github", ServiceConfig({"name": "bar"}))

        github_service = keychain.get_service("github")
        assert _simplify_config(github_service.config) == {"name": "foo"}
        # now set default to bar
        keychain.set_default_service("github", "bar_github")
        github_service = keychain.get_service("github")
        assert _simplify_config(github_service.config) == {"name": "bar"}

    def test_set_default_service__service_alredy_default(
        self, keychain, withdifferentformats
    ):
        keychain.set_service("github", "foo_github", ServiceConfig({"name": "foo"}))
        github_service = keychain.get_service("github")
        assert github_service.config == {
            "name": "foo",
            "serialization_format": withdifferentformats,
        }

        keychain.set_default_service("github", "foo_github")

        github_service = keychain.get_service("github")
        assert github_service.config == {
            "name": "foo",
            "serialization_format": withdifferentformats,
        }

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

    def test_create_default_service_file__file_already_exists(self, key):
        home_dir = tempfile.mkdtemp()
        cci_home_dir = Path(f"{home_dir}/.cumulusci")
        cci_home_dir.mkdir(parents=True)
        local_project_dir = cci_home_dir / "test-project"
        local_project_dir.mkdir()
        self._write_file(cci_home_dir / "DEFAULT_SERVICES.json", json.dumps({}))
        with mock.patch.object(
            EncryptedFileProjectKeychain, "global_config_dir", cci_home_dir
        ):
            keychain = EncryptedFileProjectKeychain(UniversalConfig(), key)
            keychain._create_default_service_files()

        assert not (local_project_dir / "DEFAULT_SERVICE.json").is_file()

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
        assert default_services["devhub"] == "global"
        assert default_services["github"] == "global"

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
            with mock.patch.object(
                EncryptedFileProjectKeychain, "project_local_dir", project_path
            ):
                # _create_default_services_files invoked via __init__
                EncryptedFileProjectKeychain(UniversalConfig(), key)

        global_default_services_file = Path(f"{cci_home_dir}/DEFAULT_SERVICES.json")
        assert global_default_services_file.is_file()
        with open(global_default_services_file, "r") as f:
            global_defaults = json.loads(f.read())

        assert len(global_defaults.keys()) == 2
        assert global_defaults["github"] == "global"
        assert global_defaults["devhub"] == "global"

        project_default_services_file = project_path / "DEFAULT_SERVICES.json"
        assert project_default_services_file.is_file()
        with open(project_default_services_file, "r") as f:
            default_services = json.loads(f.read())

        assert len(default_services.keys()) == 1
        assert default_services["github"] == "test-project"

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

        new_github_service_file = cci_home_dir / "services/github/global.service"
        assert new_github_service_file.is_file()

        # ensure expected file contents
        with open(cci_home_dir / "services/github/global.service") as f:
            assert f.read() == "github config"

        assert not Path.is_file(cci_home_dir / "test-project/devhub.service")
        assert (cci_home_dir / "services/github/TestProject.service").is_file()
        with open(cci_home_dir / "services/github/TestProject.service") as f:
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
        self._write_file(f"{named_devhub_service}/global.service", "migrated config")

        with mock.patch.object(
            EncryptedFileProjectKeychain, "global_config_dir", cci_home_dir
        ):
            # _migrate_services() invoked via __init__
            keychain = EncryptedFileProjectKeychain(project_config, key)
            keychain._migrate_services_from_dir(cci_home_dir)

        # ensure this file wasn't removed
        assert legacy_devhub_service.is_file()
        # ensure contents of migrated are unchanged
        with open(named_devhub_service / "global.service", "r") as f:
            assert f.read() == "migrated config"

    def test_rename_service(self, keychain, service_config, withdifferentformats):
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

        encrypted = keychain._get_config_bytes(service_config)
        keychain.services = {"github": {"old_alias": encrypted}}
        with mock.patch.object(
            EncryptedFileProjectKeychain, "global_config_dir", cci_home_dir
        ):
            keychain.rename_service("github", "old_alias", "new_alias")

        # Getting old alias should fail
        with pytest.raises(ServiceNotConfigured):
            keychain.get_service("github", "old_alias")

        # Validate new alias has same contents as original
        assert keychain.get_service("github", "new_alias").config == {
            **service_config.config,
            "token": "test123",
            "serialization_format": withdifferentformats,
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

    def test_rename_service__new_alias_already_exists(self, keychain):
        keychain.services = {
            "github": {"old-alias": "old config", "new-alias": "new config"}
        }
        with pytest.raises(
            CumulusCIUsageError,
            match="A service of type github already exists with name: new-alias",
        ):
            keychain.rename_service("github", "old-alias", "new-alias")

    def test_rename_service__invalid_service_type(self, keychain, service_config):
        keychain.services = {"github": {"alias": "config"}}
        with pytest.raises(ServiceNotConfigured):
            keychain.rename_service("does-not-exist", "old-alias", "new-alias")

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

    def test_cannot_rename_cumulusci_default_connected_app(self, keychain):
        error_message = (
            "You cannot rename the connected app service that is provided by CumulusCI."
        )
        with pytest.raises(CumulusCIException, match=error_message):
            keychain.rename_service(
                "connected_app", DEFAULT_CONNECTED_APP_NAME, "new_alias"
            )

    def test_remove_service(self, keychain, service_config):
        home_dir = tempfile.mkdtemp()

        cci_home_dir = Path(f"{home_dir}/.cumulusci")
        cci_home_dir.mkdir()
        with open(cci_home_dir / "DEFAULT_SERVICES.json", "w") as f:
            f.write(json.dumps({"github": "alias"}))

        local_project_dir = cci_home_dir / "test-project"
        local_project_dir.mkdir()
        with open(local_project_dir / "DEFAULT_SERVICES.json", "w") as f:
            f.write(json.dumps({"github": "alias"}))

        github_services_dir = Path(f"{home_dir}/.cumulusci/services/github")
        github_services_dir.mkdir(parents=True)
        self._write_file(github_services_dir / "alias.service", "github config")

        encrypted = keychain._get_config_bytes(service_config)
        keychain.services = {"github": {"alias": encrypted}}
        keychain._default_services["github"] = "alias"
        with mock.patch.object(
            EncryptedFileProjectKeychain, "global_config_dir", cci_home_dir
        ):
            keychain.remove_service("github", "alias")

        # loaded service is removed
        assert "old-alias" not in keychain.services["github"]
        # corresponding .service file is gone
        assert not (github_services_dir / "alias.service").is_file()
        # references in DEFAULT_SERVICES.json are gone
        with open(cci_home_dir / "DEFAULT_SERVICES.json", "r") as f:
            assert json.loads(f.read()) == {}
        with open(local_project_dir / "DEFAULT_SERVICES.json", "r") as f:
            assert json.loads(f.read()) == {}
        # default service is unset
        assert "github" not in keychain._default_services

    def test_remove_service__other_set_as_default(self, keychain, service_config):
        home_dir = tempfile.mkdtemp()

        cci_home_dir = Path(f"{home_dir}/.cumulusci")
        cci_home_dir.mkdir()
        with open(cci_home_dir / "DEFAULT_SERVICES.json", "w") as f:
            f.write(json.dumps({"github": "alias"}))

        local_project_dir = cci_home_dir / "test-project"
        local_project_dir.mkdir()
        with open(local_project_dir / "DEFAULT_SERVICES.json", "w") as f:
            f.write(json.dumps({"github": "alias"}))

        github_services_dir = Path(f"{home_dir}/.cumulusci/services/github")
        github_services_dir.mkdir(parents=True)
        self._write_file(github_services_dir / "alias.service", "github config")

        encrypted = keychain._get_config_bytes(service_config)
        keychain.services = {"github": {"alias": encrypted, "other-service": encrypted}}
        keychain._default_services["github"] = "alias"
        with mock.patch.object(
            EncryptedFileProjectKeychain, "global_config_dir", cci_home_dir
        ):
            keychain.remove_service("github", "alias")

        # the one other service should be the default
        assert keychain._default_services["github"] == "other-service"

    def test_remove_service__cannot_remove_default_connected_app(self, keychain):
        error_message = (
            f"Unable to remove connected app service: {DEFAULT_CONNECTED_APP_NAME}. "
            "This connected app is provided by CumulusCI and cannot be removed."
        )
        with pytest.raises(CumulusCIException, match=error_message):
            keychain.remove_service("connected_app", DEFAULT_CONNECTED_APP_NAME)

    def test_load_default_connected_app(self, keychain):
        keychain._load_default_connected_app()
        assert (
            DEFAULT_CONNECTED_APP_NAME in keychain.config["services"]["connected_app"]
        )
        assert (
            keychain.config["services"]["connected_app"][DEFAULT_CONNECTED_APP_NAME]
            == DEFAULT_CONNECTED_APP
        )

    def test_default_connected_app_should_be_default_after_loading(self, keychain):
        keychain._load_default_connected_app()
        assert keychain._default_services["connected_app"] == DEFAULT_CONNECTED_APP_NAME

    def test_load_default_services(self, keychain):
        expected_defaults = {
            "github": "github_alias",
            "metaci": "metaci_alias",
            "devhub": "devhub_alias",
            "connected_app": "connected_app__alias",
        }
        filepath = Path(f"{keychain.global_config_dir}/DEFAULT_SERVICES.json")
        with open(filepath, "w") as f:
            f.write(json.dumps(expected_defaults))

        keychain._load_default_services()
        assert keychain._default_services["connected_app"] != DEFAULT_CONNECTED_APP_NAME
        assert keychain._default_services == expected_defaults

    def test_read_default_services(self, keychain):
        expected_defaults = {
            "github": "github_alias",
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
        assert keychain._read_default_services(Path("not-a-valid-filepath")) == {}

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

    def test_decrypt_config__no_config(self, keychain):
        config = keychain._decrypt_config(OrgConfig, None, extra=["test", keychain])
        assert config.__class__ == OrgConfig
        assert config.config == {}
        assert config.keychain == keychain

    def test_decrypt_config__no_config_2(self, keychain):
        config = keychain._decrypt_config(BaseConfig, None)
        assert config.__class__ == BaseConfig
        assert config.config == {}

    def test_decrypt_config__Python_2_warning(self, keychain, caplog):
        config = keychain.cleanup_Python_2_configs({"a": "b"})
        assert config == {"a": "b"}
        assert len(caplog.records) == 0

        config = keychain.cleanup_Python_2_configs({"a": b"b", b"c": "d"})
        assert config == {"a": "b", "c": "d"}
        assert len(caplog.records) == 2

    def test_decrypt_config__wrong_key(self, keychain, org_config):
        keychain.set_org(org_config, False)
        keychain.key = "x" * 16
        with pytest.raises(KeychainKeyNotFound):
            keychain.get_org("test")

    def test_validate_key__wrong_length(self, project_config):
        with pytest.raises(ConfigError):
            EncryptedFileProjectKeychain(project_config, "1")

    def test_validate_key__no_key(self, project_config):
        keychain = EncryptedFileProjectKeychain(project_config, None)
        assert keychain._validate_key() is None

    def test_construct_config(self, keychain):
        result = keychain._construct_config(
            None, [{"scratch": "scratch org"}, "org_name"]
        )
        assert isinstance(result, ScratchOrgConfig)
        result = keychain._construct_config(None, [{"sfdx": True}, "org_name"])
        assert isinstance(result, SfdxOrgConfig)

    def test_new_service_type_creates_expected_directory(
        self, keychain, service_config
    ):
        home_dir = tempfile.mkdtemp()
        cci_home_dir = Path(f"{home_dir}/.cumulusci")
        cci_home_dir.mkdir()
        services_dir = cci_home_dir / "services"
        services_dir.mkdir()

        encrypted = keychain._get_config_bytes(service_config)
        with mock.patch.object(
            EncryptedFileProjectKeychain, "global_config_dir", cci_home_dir
        ):
            keychain._save_encrypted_service("new_service_type", "alias", encrypted)

        assert (services_dir / "new_service_type").is_dir()

    @pytest.mark.parametrize(
        "val, expected",
        (
            ("CUMULUSCI_SERVICE_github", ("github", "env")),
            ("CUMULUSCI_SERVICE_github__alias", ("github", "env-alias")),
            ("CUMULUSCI_SERVICE_connected_app", ("connected_app", "env")),
            ("CUMULUSCI_SERVICE_connected_app__alias", ("connected_app", "env-alias")),
        ),
    )
    def test_get_env_service_type_and_name(self, val, expected, project_config):
        keychain = EncryptedFileProjectKeychain(project_config, "0123456789abcdef")
        actual_type, actual_name = keychain._get_env_service_type_and_name(val)
        assert (actual_type, actual_name) == expected

    def test_backwards_compatability_with_EnvironmentProjectKeychain(
        self, project_config, key
    ):
        """Ensure we don't break backwards compatability for people still using EnvironmentProjectKeychain"""
        from cumulusci.core.keychain.environment_project_keychain import (
            EnvironmentProjectKeychain,
        )

        assert EnvironmentProjectKeychain is EncryptedFileProjectKeychain


def _touch_test_org_file(directory):
    org_dir = directory / "orginfo/something.something.saleforce.com"
    org_dir.mkdir(parents=True)
    (org_dir / "testfile.json").touch()
    return org_dir


class TestCleanupOrgCacheDir:
    def test_cleanup_cache_dir(self, keychain):
        keychain.set_org(
            OrgConfig({"instance_url": "http://foo.my.salesforce.com/"}, "dev"), False
        )
        keychain.set_org(
            OrgConfig({"instance_url": "http://bar.my.salesforce.com/"}, "qa"), False
        )

        temp_for_global = tempfile.mkdtemp()
        with mock.patch.object(
            EncryptedFileProjectKeychain, "global_config_dir", Path(temp_for_global)
        ):
            global_org_dir = _touch_test_org_file(keychain.global_config_dir)
            temp_for_project = tempfile.mkdtemp()
            keychain.project_config = mock.Mock()

            cache_dir = keychain.project_config.cache_dir = Path(temp_for_project)
            project_org_dir = _touch_test_org_file(cache_dir)
            with mock.patch(
                "cumulusci.core.keychain.encrypted_file_project_keychain.rmtree"
            ) as rmtree:
                keychain.cleanup_org_cache_dirs()
                rmtree.assert_has_calls(
                    [mock.call(global_org_dir), mock.call(project_org_dir)],
                    any_order=True,
                )

    def test_cleanup_cache_dir__no_project_config(self, keychain):
        keychain.project_config = None
        with mock.patch(
            "cumulusci.core.keychain.encrypted_file_project_keychain.rmtree"
        ) as rmtree:
            keychain.cleanup_org_cache_dirs()
            assert not rmtree.mock_calls, rmtree.mock_calls

    def test_cleanup_cache_dir_nothing_to_cleanup(self, keychain):
        keychain.set_org(
            OrgConfig({"instance_url": "http://foo.my.salesforce.com/"}, "dev"), False
        )

        keychain.project_config = mock.Mock()
        temp_for_global = tempfile.mkdtemp()
        with mock.patch.object(
            EncryptedFileProjectKeychain, "global_config_dir", Path(temp_for_global)
        ):
            temp_for_project = tempfile.mkdtemp()
            cache_dir = keychain.project_config.cache_dir = Path(temp_for_project)
            org_dir = cache_dir / "orginfo/foo.my.salesforce.com"
            org_dir.mkdir(parents=True)
            (org_dir / "schema.json").touch()
            with mock.patch(
                "cumulusci.core.keychain.encrypted_file_project_keychain.rmtree"
            ) as rmtree:
                keychain.cleanup_org_cache_dirs()
                assert not rmtree.mock_calls, rmtree.mock_calls

    duration = (
        (59, "59s"),
        (70, "1m:10s"),
        (119, "1m:59s"),
        (65, "1m:5s"),
        (4000, "1h:6m:40s"),
        (7199, "1h:59m:59s"),
    )

    @pytest.mark.parametrize("val,expected", duration)
    def test_time_delta(self, val, expected):
        formatted = utils.format_duration(datetime.timedelta(seconds=val))
        assert formatted == expected, (formatted, expected)

    def test_set_and_get_org_with_dates__json(
        self, keychain, org_config, key, withdifferentformats
    ):
        org_config.global_org = True
        keychain.key = key

        custom_datetime = datetime.datetime.now()
        custom_date = datetime.datetime.now().date()
        org_config.config["custom_datetime"] = custom_datetime
        org_config.config["custom_date"] = custom_date

        keychain.set_org(org_config, True)
        assert list(keychain.orgs.keys()) == ["test"]
        config = keychain.get_org("test").config
        assert config == {
            **org_config.config,
            "serialization_format": withdifferentformats,
        }
        assert config["custom_datetime"] == custom_datetime
        assert config["custom_date"] == custom_date

    @mock.patch("cumulusci.core.keychain.serialization.SHOULD_SAVE_AS_JSON", True)
    def test_set_and_get_org_with_bad_datatypes(self, keychain, org_config, key):
        org_config.global_org = True
        keychain.key = None
        with mock.patch("pickle.dumps") as dumps:
            dumps.return_value = b"xx"
            org_config.config["good"] = 25

            keychain.set_org(org_config, True)
            assert not dumps.mock_calls

            org_config.config["bad"] = 25j

            keychain.set_org(org_config, True)
            assert dumps.called_once_with({"bad", 25j})

    def test_set_and_get_service_with_dates__global(
        self, keychain, key, withdifferentformats
    ):
        service_config = ServiceConfig(
            {"name": "foo1", "password": "1234", "token": "1234"}
        )

        keychain.key = key

        custom_datetime = datetime.datetime.now()
        custom_date = datetime.datetime.now().date()
        service_config.config["custom_datetime"] = custom_datetime
        service_config.config["custom_date"] = custom_date

        keychain.set_service("github", "alias", service_config)
        config = keychain.get_service("github").config
        assert config == {
            **service_config.config,
            "serialization_format": withdifferentformats,
        }
        assert config["custom_datetime"] == custom_datetime
        assert config["custom_date"] == custom_date

    def test_migration_pickle_to_json(
        self, keychain, patch_home_and_env, project_config
    ):
        # This all runs in fake-home, not real home.
        with mock.patch(
            "cumulusci.core.keychain.serialization.SHOULD_SAVE_AS_JSON", False
        ):
            org_config = OrgConfig(
                {"password": "Kltpzyxm"}, "test_migration", keychain=keychain
            )
            org_config.save()
            assert Path(keychain.project_local_dir, "test_migration.org").exists()
            del keychain.config["orgs"]
            keychain._load_orgs()
            assert keychain.get_org("test_migration").password == "Kltpzyxm"
            assert keychain.get_org("test_migration").serialization_format == "pickle"

        with mock.patch(
            "cumulusci.core.keychain.serialization.SHOULD_SAVE_AS_JSON", True
        ):
            org_config.save()
            assert Path(keychain.project_local_dir, "test_migration.org").exists()
            del keychain.config["orgs"]
            keychain._load_orgs()
            assert keychain.get_org("test_migration").password == "Kltpzyxm"
            assert keychain.get_org("test_migration").serialization_format == "json"
