from unittest import mock

import click
import pytest

from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci.core.tests.utils import EnvironmentVarGuard

from .. import service
from .utils import run_click_command


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

    run_click_command(
        service.service_list, runtime=runtime, plain=False, print_json=False
    )

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

    run_click_command(
        service.service_list, runtime=runtime, plain=False, print_json=False
    )

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


@mock.patch("json.dumps")
def test_service_list_json(json_):
    services = {
        "bad": {"description": "Unconfigured Service"},
        "test": {"description": "Test Service"},
    }
    runtime = mock.Mock()
    runtime.project_config.services = services
    runtime.keychain.list_services.return_value = ["test"]
    runtime.universal_config.cli__plain_output = None

    run_click_command(
        service.service_list, runtime=runtime, plain=False, print_json=True
    )

    json_.assert_called_with(services)


def test_service_connect__list_commands():
    multi_cmd = service.ConnectServiceCommand()
    runtime = mock.Mock()
    runtime.project_config.services = {"test": {}}

    with click.Context(multi_cmd, obj=runtime) as ctx:
        result = multi_cmd.list_commands(ctx)
    assert result == ["test"]


def test_service_connect__list_global_keychain():
    multi_cmd = service.ConnectServiceCommand()
    runtime = mock.Mock()
    runtime.project_config = None
    runtime.universal_config.services = {"test": {}}

    with click.Context(multi_cmd, obj=runtime) as ctx:
        result = multi_cmd.list_commands(ctx)
    assert result == ["test"]


def test_service_connect():
    multi_cmd = service.ConnectServiceCommand()
    runtime = mock.MagicMock()
    runtime.keychain.get_default_service_name.return_value = None
    runtime.project_config.services = {
        "test": {"attributes": {"attr": {"required": False}}}
    }

    with click.Context(multi_cmd, obj=runtime) as ctx:
        cmd = multi_cmd.get_command(ctx, "test")
        cmd.callback(ctx.obj, project=True, service_name="test-alias")

        runtime.keychain.set_service.assert_called_once()

        cmd.callback(ctx.obj, project=False, service_name="test-alias")


@mock.patch("click.confirm")
def test_service_connect__alias_already_exists(confirm):
    confirm.side_effect = "y"
    multi_cmd = service.ConnectServiceCommand()
    ctx = mock.Mock()
    runtime = mock.MagicMock()
    runtime.project_config.services = {
        "test-type": {"attributes": {"attr": {"required": False}}}
    }
    runtime.services = {"test-type": {"already-exists": "some config"}}
    runtime.keychain.list_services.return_value = {"test-type": ["already-exists"]}
    runtime.keychain.get_default_service_name.return_value = None

    with click.Context(multi_cmd, obj=runtime) as ctx:
        cmd = multi_cmd.get_command(ctx, "test-type")
        cmd.callback(
            runtime,
            service_type="test-type",
            service_name="already-exists",
            project=True,
        )

    confirm.assert_called_once()


@mock.patch("click.confirm")
def test_service_connect__set_new_service_as_default(confirm):
    confirm.return_value = True
    multi_cmd = service.ConnectServiceCommand()
    runtime = mock.MagicMock()
    runtime.project_config.services = {
        "test-type": {"attributes": {"attr": {"required": False}}}
    }
    service_name = "existing-service"
    runtime.services = {"test-type": {service_name: "some config"}}
    runtime.keychain.list_services.return_value = {"test-type": [service_name]}
    runtime.keychain.get_default_service_name.return_value = service_name

    with click.Context(multi_cmd, obj=runtime) as ctx:
        cmd = multi_cmd.get_command(ctx, "test-type")
        cmd.callback(
            runtime,
            service_type="test-type",
            service_name="new-service",
            project=False,
        )

    confirm.assert_called_once()
    runtime.keychain.set_default_service.assert_called_once_with(
        "test-type", "new-service"
    )


@mock.patch("click.confirm")
def test_service_connect__do_not_set_new_service_as_default(confirm):
    confirm.return_value = False
    multi_cmd = service.ConnectServiceCommand()
    runtime = mock.MagicMock()
    runtime.project_config.services = {
        "test-type": {"attributes": {"attr": {"required": False}}}
    }
    service_name = "existing-service"
    runtime.services = {"test-type": {service_name: "some config"}}
    runtime.keychain.list_services.return_value = {"test-type": [service_name]}
    runtime.keychain.get_default_service_name.return_value = service_name

    with click.Context(multi_cmd, obj=runtime) as ctx:
        cmd = multi_cmd.get_command(ctx, "test-type")
        cmd.callback(
            runtime,
            service_type="test-type",
            service_name="new-service",
            project=False,
        )

    confirm.assert_called_once()
    runtime.keychain.set_default_service.call_count = 0


@mock.patch("click.echo")
def test_service_connect__no_name_given(echo):
    multi_cmd = service.ConnectServiceCommand()
    ctx = mock.Mock()
    runtime = mock.MagicMock()
    runtime.project_config.services = {
        "test-type": {"attributes": {"attr": {"required": False}}}
    }
    runtime.services = {"test-type": {}}
    runtime.keychain.list_services.return_value = {"test-type": []}
    runtime.keychain.get_default_service_name.return_value = None

    with click.Context(multi_cmd, obj=runtime) as ctx:
        cmd = multi_cmd.get_command(ctx, "test-type")
        cmd.callback(
            runtime,
            service_type="test-type",
            service_name=None,
            project=True,
        )

    # service_name is None, so the alias when setting the service should be 'default'
    assert "default" in runtime.keychain.set_service.call_args_list[0][0]
    assert (
        echo.call_args_list[0][0][0]
        == "No service name specified. Using 'default' as the service name."
    )


@mock.patch("click.echo")
def test_service_connect__global_default(echo):
    multi_cmd = service.ConnectServiceCommand()
    ctx = mock.Mock()
    runtime = mock.MagicMock()
    runtime.project_config.services = {
        "test": {"attributes": {"attr": {"required": False}}}
    }
    runtime.keychain.get_default_service_name.return_value = None

    with click.Context(multi_cmd, obj=runtime) as ctx:
        cmd = multi_cmd.get_command(ctx, "test")
        cmd.callback(runtime, service_name="test-alias", default=True, project=False)

    runtime.keychain.set_default_service.assert_called_once_with(
        "test", "test-alias", project=False
    )
    assert echo.call_args_list[0][0][0] == "Service test:test-alias is now connected"
    assert (
        echo.call_args_list[1][0][0]
        == "Service test:test-alias is now the default for all CumulusCI projects"
    )


@mock.patch("click.echo")
def test_service_connect__project_default(echo):
    multi_cmd = service.ConnectServiceCommand()
    ctx = mock.Mock()
    runtime = mock.MagicMock()
    runtime.project_config.services = {
        "test": {"attributes": {"attr": {"required": False}}}
    }
    runtime.keychain.get_default_service_name.return_value = None

    with click.Context(multi_cmd, obj=runtime) as ctx:
        cmd = multi_cmd.get_command(ctx, "test")
        cmd.callback(runtime, service_name="test-alias", default=False, project=True)

    runtime.keychain.set_default_service.assert_called_once_with(
        "test", "test-alias", project=True
    )
    assert echo.call_args_list[0][0][0] == "Service test:test-alias is now connected"
    assert (
        "Service test:test-alias is now the default for project"
        in echo.call_args_list[1][0][0]
    )


def test_service_connect_global_keychain():
    multi_cmd = service.ConnectServiceCommand()
    runtime = mock.MagicMock()
    runtime.project_config = None
    runtime.universal_config.services = {
        "test": {"attributes": {"attr": {"required": False}}}
    }
    runtime.keychain.get_default_service_name.return_value = None

    with click.Context(multi_cmd, obj=runtime) as ctx:
        cmd = multi_cmd.get_command(ctx, "test")
        cmd.callback(ctx.obj, project=True, service_name="test-alias")

        runtime.keychain.set_service.assert_called_once()

        cmd.callback(ctx.obj, project=False, service_name="test-alias")


def test_service_connect_invalid_service():
    multi_cmd = service.ConnectServiceCommand()
    runtime = mock.MagicMock()
    runtime.project_config.services = {}

    with click.Context(multi_cmd, obj=runtime) as ctx:
        with pytest.raises(click.UsageError):
            multi_cmd.get_command(ctx, "test")


@mock.patch("cumulusci.cli.tests.test_service.validate_service")
def test_service_connect_validator(validator):
    multi_cmd = service.ConnectServiceCommand()
    runtime = mock.MagicMock()
    runtime.project_config.services = {
        "test": {
            "attributes": {},
            "validator": "cumulusci.cli.tests.test_service.validate_service",
        }
    }
    runtime.keychain.get_default_service_name.return_value = None

    expected_conf = {
        "service_type": "test",
        "service_name": "test-alias",
        "key": "value",
    }
    validator.return_value = expected_conf
    with click.Context(multi_cmd, obj=runtime) as ctx:
        cmd = multi_cmd.get_command(ctx, "test")
        cmd.callback(
            runtime,
            service_type="test",
            service_name="test-alias",
            project=False,
            key="value",
        )
        validator.assert_called_once_with(expected_conf)


@mock.patch("cumulusci.cli.tests.test_service.validate_service")
def test_service_connect_validator_failure(validator):
    multi_cmd = service.ConnectServiceCommand()
    runtime = mock.MagicMock()
    runtime.project_config.services = {
        "test": {
            "attributes": {},
            "validator": "cumulusci.cli.tests.test_service.validate_service",
        }
    }
    runtime.keychain.get_default_service_name.return_value = None

    validator.side_effect = Exception("Validation failed")
    with click.Context(multi_cmd, obj=runtime) as ctx:
        cmd = multi_cmd.get_command(ctx, "test")
        with pytest.raises(Exception, match="Validation failed"):
            cmd.callback(
                runtime,
                service_type="test",
                service_name="test-alias",
                project=False,
            )


@mock.patch("cumulusci.cli.service.CliTable")
def test_service_info(cli_tbl):
    cli_tbl._table = mock.Mock()
    service_config = mock.Mock()
    service_config.config = {"description": "Test Service"}
    runtime = mock.Mock()
    runtime.keychain.get_service.return_value = service_config
    runtime.universal_config.cli__plain_output = None

    run_click_command(
        service.service_info,
        runtime=runtime,
        service_type="test",
        service_name="test-alias",
        plain=False,
    )

    cli_tbl.assert_called_with(
        [["Key", "Value"], ["\x1b[1mdescription\x1b[0m", "Test Service"]],
        title="test:test-alias",
    )


@mock.patch("click.echo")
def test_service_info_not_configured(echo):
    runtime = mock.Mock()
    runtime.keychain.get_service.side_effect = ServiceNotConfigured

    run_click_command(
        service.service_info,
        runtime=runtime,
        service_type="test",
        service_name="test-alias",
        plain=False,
    )
    assert "not configured for this project" in echo.call_args[0][0]


@mock.patch("click.echo")
def test_service_default__global(echo):
    runtime = mock.Mock()
    run_click_command(
        service.service_default,
        runtime=runtime,
        service_type="test",
        service_name="test-alias",
        project=False,
    )
    runtime.keychain.set_default_service.called_once_with("test", "test-alias")
    echo.assert_called_once_with(
        "Service test:test-alias is now the default for all CumulusCI projects"
    )


@mock.patch("click.echo")
def test_service_default__project(echo):
    runtime = mock.Mock()
    runtime.keychain.project_local_dir = "test"
    run_click_command(
        service.service_default,
        runtime=runtime,
        service_type="test",
        service_name="test-alias",
        project=True,
    )
    runtime.keychain.set_default_service.called_once_with("test", "test-alias")
    echo.assert_called_once_with(
        "Service test:test-alias is now the default for project 'test'"
    )


@mock.patch("click.echo")
def test_service_default__exception(echo):
    runtime = mock.Mock()
    runtime.keychain.set_default_service.side_effect = ServiceNotConfigured(
        "test error"
    )
    run_click_command(
        service.service_default,
        runtime=runtime,
        service_type="no-such-type",
        service_name="test-alias",
        project=False,
    )
    echo.assert_called_once_with(
        "An error occurred setting the default service: test error"
    )


@mock.patch("click.echo")
def test_service_rename(echo):
    runtime = mock.Mock()
    run_click_command(
        service.service_rename,
        runtime=runtime,
        service_type="test-type",
        current_name="old-alias",
        new_name="new-alias",
    )
    runtime.keychain.rename_service.assert_called_once_with(
        "test-type", "old-alias", "new-alias"
    )
    echo.assert_called_once_with(
        "Service test-type:old-alias has been renamed to new-alias"
    )


@mock.patch("click.echo")
def test_service_rename__exception(echo):
    runtime = mock.Mock()
    runtime.keychain.rename_service.side_effect = ServiceNotConfigured("test error")
    run_click_command(
        service.service_rename,
        runtime=runtime,
        service_type="test-type",
        current_name="old-alias",
        new_name="new-alias",
    )
    echo.assert_called_once_with("An error occurred renaming the service: test error")


@mock.patch("cumulusci.cli.service.click")
def test_service_remove(click):
    click.prompt.side_effect = ("future-default-alias",)
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
    run_click_command(
        service.service_remove,
        runtime=runtime,
        service_type="github",
        service_name="current-default-alias",
    )
    runtime.keychain.remove_service.assert_called_once_with(
        "github", "current-default-alias"
    )
    runtime.keychain.set_default_service.assert_called_once_with(
        "github", "future-default-alias"
    )
    assert (
        click.echo.call_args_list[-1][0][0]
        == "Service github:current-default-alias has been removed."
    )


@mock.patch("cumulusci.cli.service.click")
def test_service_remove__name_does_not_exist(click):
    click.prompt.side_effect = ("this-alias-does-not-exist",)
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
    run_click_command(
        service.service_remove,
        runtime=runtime,
        service_type="github",
        service_name="current-default-alias",
    )
    assert (
        click.echo.call_args_list[-1][0][0]
        == "No service of type github with name: this-alias-does-not-exist"
    )
    assert runtime.keychain.remove_service.call_count == 0
    assert runtime.keychain.set_default_service.call_count == 0


@mock.patch("cumulusci.cli.service.click")
def test_service_remove__exception_thrown(click):
    click.prompt.side_effect = ("future-default-alias",)
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
    run_click_command(
        service.service_remove,
        runtime=runtime,
        service_type="github",
        service_name="current-default-alias",
    )
    assert (
        click.echo.call_args_list[-1][0][0]
        == "An error occurred removing the service: test error"
    )


@mock.patch("cumulusci.cli.service.click")
def test_service_remove__environment_service_cannot_be_removed(click):
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
        run_click_command(
            service.service_remove,
            runtime=runtime,
            service_type="github",
            service_name="env-foo",
        )
    assert (
        click.echo.call_args_list[-1][0][0]
        == "The service github:env-foo is defined by environment variables. If you would like it removed please delete the environment variable with name: CUMULUSCI_SERVICE_github__env-foo"
    )


def validate_service(options):
    pass
