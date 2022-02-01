import json
from unittest import mock

import click
import pytest

from cumulusci.core.config import BaseProjectConfig, ServiceConfig, UniversalConfig
from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.tests.utils import EnvironmentVarGuard

from .utils import run_cli_command


@mock.patch("cumulusci.cli.service.CliTable")
def test_service_list__no_active_defaults(cli_tbl):
    runtime = mock.Mock()
    runtime.project_config.services = {
        "bad": {"description": "Unconfigured Service"},
        "test": {"description": "Test Service"},
        "something_else": {"description": "something else"},
    }
    runtime.keychain.list_services.return_value = {
        "test": ["test_alias", "test2_alias"],
        "bad": ["bad_alias"],
    }
    runtime.keychain._default_services = {"test": "test_alias"}
    runtime.universal_config.cli__plain_output = None

    run_cli_command("service", "list", runtime=runtime)

    cli_tbl.assert_called_with(
        [
            ["Default", "Type", "Name", "Description"],
            [False, "bad", "bad_alias", "Unconfigured Service"],
            [False, "something_else", "", "something else"],
            [True, "test", "test_alias", "Test Service"],
            [False, "test", "test2_alias", "Test Service"],
        ],
        title="Services",
        dim_rows=[2],
    )


@mock.patch("cumulusci.cli.service.CliTable")
def test_service_list(cli_tbl):
    runtime = mock.Mock()
    runtime.project_config.services = {
        "bad": {"description": "Unconfigured Service"},
        "test": {"description": "Test Service"},
        "something_else": {"description": "something else"},
    }
    runtime.keychain.list_services.return_value = {
        "test": ["test_alias", "test2_alias"],
        "bad": ["bad_alias"],
    }
    runtime.keychain._default_services = {"test": "test_alias", "bad": "bad_alias"}
    runtime.universal_config.cli__plain_output = None

    run_cli_command("service", "list", runtime=runtime)

    cli_tbl.assert_called_with(
        [
            ["Default", "Type", "Name", "Description"],
            [True, "bad", "bad_alias", "Unconfigured Service"],
            [False, "something_else", "", "something else"],
            [True, "test", "test_alias", "Test Service"],
            [False, "test", "test2_alias", "Test Service"],
        ],
        title="Services",
        dim_rows=[2],
    )


def test_service_list_json():
    services = {
        "bad": {"description": "Unconfigured Service"},
        "test": {"description": "Test Service"},
    }
    runtime = mock.Mock()
    runtime.project_config.services = services
    runtime.keychain.list_services.return_value = ["test"]
    runtime.universal_config.cli__plain_output = None

    result = run_cli_command("service", "list", "--json", runtime=runtime)
    result_json = json.loads(result.output)
    assert result_json == services


def test_service_connect__list_service_types():
    runtime = mock.Mock()
    runtime.project_config.services = {"project_test": {}}

    result = run_cli_command("service", "connect", runtime=runtime)
    assert "project_test" in result.output


def test_service_connect__list_service_types_from_universal_config():
    runtime = mock.Mock()
    runtime.project_config = None
    runtime.universal_config.services = {"universal_test": {}}

    result = run_cli_command("service", "connect", runtime=runtime)
    assert "universal_test" in result.output


def test_service_connect():
    runtime = mock.MagicMock()
    runtime.keychain.get_default_service_name.return_value = None
    runtime.project_config.services = {
        "test": {"attributes": {"attr": {"required": False}}}
    }

    run_cli_command(
        "service", "connect", "test", "test-alias", "--project", runtime=runtime
    )

    runtime.keychain.set_service.assert_called_once()


def test_service_connect__attr_with_default_value():
    runtime = mock.MagicMock()
    runtime.project_config = project_config = BaseProjectConfig(
        None,
        {
            "services": {
                "test": {
                    "attributes": {
                        "attr": {"default": "PRESET", "description": "example"}
                    }
                }
            }
        },
    )
    runtime.keychain = keychain = BaseProjectKeychain(project_config, None)

    result = run_cli_command(
        "service", "connect", "test", "test-alias", runtime=runtime, input="\n"
    )

    # User should have been prompted to override the default,
    # but input of an empty line accepts the default.
    assert "attr (example) [PRESET]: " in result.output
    service_config = keychain.get_service("test", "test-alias")
    assert service_config.attr == "PRESET"


def test_service_connect__attr_with_default_factory():
    runtime = mock.MagicMock()
    runtime.project_config = project_config = BaseProjectConfig(
        None,
        {
            "services": {
                "test": {
                    "attributes": {
                        "attr": {
                            "default_factory": "cumulusci.cli.tests.test_service.get_default"
                        }
                    }
                }
            }
        },
    )
    runtime.keychain = keychain = BaseProjectKeychain(project_config, None)

    run_cli_command("service", "connect", "test", "test-alias", runtime=runtime)

    # The service should have the attribute value returned by the default factory.
    service_config = keychain.get_service("test", "test-alias")
    assert service_config.attr == "CALCULATED"


def test_service_connect__alias_already_exists():
    runtime = mock.MagicMock()
    runtime.project_config = BaseProjectConfig(
        None,
        config={
            "services": {"test-type": {"attributes": {"attr": {"required": True}}}}
        },
    )
    runtime.keychain = BaseProjectKeychain(runtime.project_config, None)
    runtime.keychain.set_service(
        "test-type", "already-exists", ServiceConfig({"attr": "old"})
    )

    run_cli_command(
        "service",
        "connect",
        "test-type",
        "already-exists",
        runtime=runtime,
        input="new\ny\n",
    )

    service_config = runtime.keychain.get_service("test-type", "already-exists")
    assert service_config.attr == "new"


def test_service_connect__set_new_service_as_default():
    runtime = mock.MagicMock()
    runtime.project_config.services = {
        "test-type": {"attributes": {"attr": {"required": False}}}
    }
    service_name = "existing-service"
    runtime.services = {"test-type": {service_name: "some config"}}
    runtime.keychain.list_services.return_value = {"test-type": [service_name]}
    runtime.keychain.get_default_service_name.return_value = service_name

    run_cli_command(
        "service", "connect", "test-type", "new-service", runtime=runtime, input="y\n"
    )

    runtime.keychain.set_default_service.assert_called_once_with(
        "test-type", "new-service"
    )


def test_service_connect__do_not_set_new_service_as_default():
    runtime = mock.MagicMock()
    runtime.project_config.services = {
        "test-type": {"attributes": {"attr": {"required": False}}}
    }
    service_name = "existing-service"
    runtime.services = {"test-type": {service_name: "some config"}}
    runtime.keychain.list_services.return_value = {"test-type": [service_name]}
    runtime.keychain.get_default_service_name.return_value = service_name

    run_cli_command("service", "connect", "test-type", "new-service", runtime=runtime)

    assert runtime.keychain.set_default_service.call_count == 0


def test_service_connect__no_name_given():
    runtime = mock.MagicMock()
    runtime.project_config.services = {
        "test-type": {"attributes": {"attr": {"required": False}}}
    }
    runtime.services = {"test-type": {}}
    runtime.keychain.list_services.return_value = {"test-type": []}
    runtime.keychain.get_default_service_name.return_value = None

    result = run_cli_command("service", "connect", "test-type", runtime=runtime)

    # service_name is None, so the alias when setting the service should be 'default'
    assert (
        "No service name specified. Using 'default' as the service name."
        in result.output
    )


def test_service_connect__global_default():
    runtime = mock.MagicMock()
    runtime.project_config.services = {
        "test": {"attributes": {"attr": {"required": False}}}
    }
    runtime.keychain.get_default_service_name.return_value = None

    result = run_cli_command(
        "service", "connect", "test", "test-alias", "--default", runtime=runtime
    )

    assert "Service test:test-alias is now connected" in result.output
    assert (
        "Service test:test-alias is now the default for all CumulusCI projects"
        in result.output
    )


def test_service_connect__project_default():
    runtime = mock.MagicMock()
    runtime.project_config.services = {
        "test": {"attributes": {"attr": {"required": False}}}
    }
    runtime.keychain.get_default_service_name.return_value = None

    result = run_cli_command(
        "service", "connect", "test", "test-alias", "--project", runtime=runtime
    )

    assert "Service test:test-alias is now connected" in result.output
    assert "Service test:test-alias is now the default for project" in result.output


def test_service_connect__global_keychain():
    runtime = mock.MagicMock()
    runtime.project_config = None
    runtime.universal_config.services = {
        "test": {"attributes": {"attr": {"required": False}}}
    }
    runtime.keychain.get_default_service_name.return_value = None

    run_cli_command("service", "connect", "test", "test-alias", runtime=runtime)

    runtime.keychain.set_service.assert_called_once()


def test_service_connect__invalid_service():
    runtime = mock.MagicMock()
    runtime.project_config.services = {}

    with pytest.raises(click.UsageError):
        run_cli_command("service", "connect", "test", runtime=runtime)


def test_service_connect_validator():
    runtime = mock.MagicMock()
    runtime.project_config = BaseProjectConfig(
        None,
        config={
            "services": {
                "test": {
                    "attributes": {},
                    "validator": "cumulusci.cli.tests.test_service.validate_service",
                }
            }
        },
    )
    runtime.keychain = BaseProjectKeychain(runtime.project_config, None)

    run_cli_command("service", "connect", "test", "test-alias", runtime=runtime)

    service_config = runtime.keychain.get_service("test", "test-alias")
    assert service_config.config == {"service_name": "test-alias", "key": "value"}


@mock.patch("cumulusci.cli.tests.test_service.validate_service")
def test_service_connect_validator_failure(validator):
    runtime = mock.MagicMock()
    runtime.project_config.services = {
        "test": {
            "attributes": {},
            "validator": "cumulusci.cli.tests.test_service.validate_service",
        }
    }
    runtime.keychain.get_default_service_name.return_value = None

    validator.side_effect = Exception("Validation failed")

    with pytest.raises(Exception, match="Validation failed"):
        run_cli_command("service", "connect", "test", "test-alias", runtime=runtime)


def test_service_connect__connected_app():
    runtime = mock.MagicMock()
    runtime.project_config = BaseProjectConfig(UniversalConfig())
    runtime.keychain = BaseProjectKeychain(runtime.project_config, None)

    run_cli_command(
        "service",
        "connect",
        "connected_app",
        "new",
        input="\n\nID\nSECRET\n",
        runtime=runtime,
    )

    service_config = runtime.keychain.get_service("connected_app", "new")
    assert service_config.config == {
        "service_name": "new",
        "login_url": "https://login.salesforce.com",
        "callback_url": "http://localhost:8080/callback",
        "client_id": "ID",
        "client_secret": "SECRET",
    }


def test_service_connect__connected_app__with_cli_options():
    runtime = mock.MagicMock()
    runtime.project_config = BaseProjectConfig(UniversalConfig())
    runtime.keychain = BaseProjectKeychain(runtime.project_config, None)

    run_cli_command(
        "service",
        "connect",
        "connected_app",
        "new",
        "--login_url",
        "https://custom",
        input="\nID\nSECRET\n",  # not prompted for login_url
        runtime=runtime,
    )

    service_config = runtime.keychain.get_service("connected_app", "new")
    assert service_config.config == {
        "service_name": "new",
        "login_url": "https://custom",
        "callback_url": "http://localhost:8080/callback",
        "client_id": "ID",
        "client_secret": "SECRET",
    }


@mock.patch("cumulusci.cli.service.CliTable")
def test_service_info(cli_tbl):
    cli_tbl._table = mock.Mock()
    service_config = mock.Mock()
    service_config.config = {"description": "Test Service"}
    runtime = mock.Mock()
    runtime.keychain.get_service.return_value = service_config
    runtime.universal_config.cli__plain_output = None

    run_cli_command("service", "info", "test", "test-alias", runtime=runtime)

    cli_tbl.assert_called_with(
        [["Key", "Value"], ["\x1b[1mdescription\x1b[0m", "Test Service"]],
        title="test:test-alias",
    )


def test_service_info_not_configured():
    runtime = mock.Mock()
    runtime.keychain.get_service.side_effect = ServiceNotConfigured

    result = run_cli_command("service", "info", "test", "test-alias", runtime=runtime)

    assert "not configured for this project" in result.output


def test_service_default__global():
    runtime = mock.Mock()
    result = run_cli_command(
        "service", "default", "test", "test-alias", runtime=runtime
    )

    runtime.keychain.set_default_service.called_once_with("test", "test-alias")
    assert (
        "Service test:test-alias is now the default for all CumulusCI projects"
        in result.output
    )


def test_service_default__project():
    runtime = mock.Mock()
    runtime.keychain.project_local_dir = "test"
    result = run_cli_command(
        "service", "default", "test", "test-alias", "--project", runtime=runtime
    )

    runtime.keychain.set_default_service.called_once_with("test", "test-alias")
    assert (
        "Service test:test-alias is now the default for project 'test'" in result.output
    )


def test_service_connect__project_default_no_project():
    runtime = mock.Mock()
    runtime.project_config = None
    runtime.keychain.project_local_dir = "test"

    with pytest.raises(click.UsageError):
        run_cli_command(
            "service", "default", "test", "test-alias", "--project", runtime=runtime
        )


def test_service_default__exception():
    runtime = mock.Mock()
    runtime.keychain.set_default_service.side_effect = ServiceNotConfigured(
        "test error"
    )

    result = run_cli_command(
        "service", "default", "no-such-type", "test-alias", runtime=runtime
    )
    assert "An error occurred setting the default service: test error" in result.output


def test_service_rename():
    runtime = mock.Mock()
    result = run_cli_command(
        "service", "rename", "test-type", "old-alias", "new-alias", runtime=runtime
    )

    runtime.keychain.rename_service.assert_called_once_with(
        "test-type", "old-alias", "new-alias"
    )
    assert "Service test-type:old-alias has been renamed to new-alias" in result.output


def test_service_rename__exception():
    runtime = mock.Mock()
    runtime.keychain.rename_service.side_effect = ServiceNotConfigured("test error")
    result = run_cli_command(
        "service", "rename", "test-type", "old-alias", "new-alias", runtime=runtime
    )
    assert "An error occurred renaming the service: test error" in result.output


def test_service_remove():
    runtime = mock.Mock()
    runtime.keychain.env_service_var_prefix = "CUMULUSCI_SERVICE_"
    runtime.keychain.services = {
        "github": {
            "current-default-alias": "config1",
            "another-alias": "config2",
            "future-default-alias": "config3",
        }
    }
    runtime.keychain._default_services = {"github": "current-default-alias"}
    runtime.keychain.list_services.return_value = {
        "github": ["current-default-alias", "another-alias", "future-default-alias"]
    }

    result = run_cli_command(
        "service",
        "remove",
        "github",
        "current-default-alias",
        input="future-default-alias\n",
        runtime=runtime,
    )

    runtime.keychain.remove_service.assert_called_once_with(
        "github", "current-default-alias"
    )
    runtime.keychain.set_default_service.assert_called_once_with(
        "github", "future-default-alias"
    )
    assert "Service github:current-default-alias has been removed." in result.output


def test_service_remove__name_does_not_exist():
    runtime = mock.Mock()
    runtime.keychain.env_service_var_prefix = "CUMULUSCI_SERVICE_"
    runtime.keychain.services = {
        "github": {
            "current-default-alias": "config1",
            "another-alias": "config2",
            "future-default-alias": "config3",
        }
    }
    runtime.keychain._default_services = {"github": "current-default-alias"}
    runtime.keychain.list_services.return_value = {
        "github": ["current-default-alias", "another-alias", "future-default-alias"]
    }
    result = run_cli_command(
        "service",
        "remove",
        "github",
        "current-default-alias",
        input="this-alias-does-not-exist\n",
        runtime=runtime,
    )
    assert (
        "No service of type github with name: this-alias-does-not-exist"
        in result.output
    )
    assert runtime.keychain.remove_service.call_count == 0
    assert runtime.keychain.set_default_service.call_count == 0


def test_service_remove__exception_thrown():
    runtime = mock.Mock()
    runtime.keychain.env_service_var_prefix = "CUMULUSCI_SERVICE_"
    runtime.keychain.services = {
        "github": {
            "current-default-alias": "config1",
            "another-alias": "config2",
            "future-default-alias": "config3",
        }
    }
    runtime.keychain._default_services = {"github": "current-default-alias"}
    runtime.keychain.list_services.return_value = {
        "github": ["current-default-alias", "another-alias", "future-default-alias"]
    }
    runtime.keychain.remove_service.side_effect = ServiceNotConfigured("test error")
    result = run_cli_command(
        "service",
        "remove",
        "github",
        "current-default-alias",
        input="future-default-alias\n",
        runtime=runtime,
    )
    assert "An error occurred removing the service: test error" in result.output


def test_service_remove__environment_service_cannot_be_removed():
    runtime = mock.Mock()
    runtime.keychain.env_service_var_prefix = "CUMULUSCI_SERVICE_"
    runtime.keychain.services = {
        "github": {
            "env-foo": "config-from-env",
            "another-alias": "config-from-file",
        }
    }
    with EnvironmentVarGuard() as env:
        env.set(
            "CUMULUSCI_SERVICE_github__env-foo", '{"username":"foo", "token": "bar"}'
        )
        result = run_cli_command(
            "service", "remove", "github", "env-foo", runtime=runtime
        )
    assert (
        "The service github:env-foo is defined by environment variables. "
        "If you would like it removed please delete the environment variable with name: "
        "CUMULUSCI_SERVICE_github__env-foo"
    ) in result.output


def validate_service(options):
    return {"key": "value"}


def get_default():
    return "CALCULATED"
