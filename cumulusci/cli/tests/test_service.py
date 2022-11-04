import json
from unittest import mock

import click
import pytest

from cumulusci.cli.service import get_sensitive_service_attributes, get_service_data
from cumulusci.core.config import ServiceConfig
from cumulusci.core.runtime import BaseCumulusCI
from cumulusci.core.tests.utils import EnvironmentVarGuard

from .utils import run_cli_command


@mock.patch("cumulusci.cli.service.CliTable")
def test_service_list(table_mock):
    runtime = BaseCumulusCI(
        config={
            "services": {
                "bad": {"description": "Unconfigured Service"},
                "test": {"description": "Test Service"},
                "something_else": {"description": "something else"},
            }
        }
    )
    runtime.keychain.config["services"] = {
        "test": {"test_alias": ServiceConfig({}), "test2_alias": ServiceConfig({})},
        "bad": {"bad_alias": ServiceConfig({})},
    }
    runtime.keychain._default_services = {"test": "test_alias", "bad": "bad_alias"}

    run_cli_command("service", "list", runtime=runtime)

    table_mock.assert_called_once_with(
        [
            ["Default", "Type", "Name", "Description"],
            [True, "bad", "bad_alias", "Unconfigured Service"],
            [False, "something_else", "", "something else"],
            [False, "test", "test2_alias", "Test Service"],
            [True, "test", "test_alias", "Test Service"],
        ],
        title="Services",
        dim_rows=[2],
    )


def test_service_list__json():
    expected_services = {
        "bad": {"description": "Unconfigured Service"},
        "test": {"description": "Test Service"},
    }
    runtime = BaseCumulusCI(config={"services": expected_services})

    result = run_cli_command("service", "list", "--json", runtime=runtime)
    result_json = json.loads(result.output)
    # I don't think this is actually very useful...
    assert result_json == expected_services


def test_service_connect__list_service_types():
    runtime = BaseCumulusCI(config={"services": {"project_test": {}}})

    result = run_cli_command("service", "connect", runtime=runtime)
    assert "project_test" in result.output


def test_service_connect__list_service_types_from_universal_config():
    runtime = BaseCumulusCI()
    runtime.project_config = None
    runtime.universal_config.config["services"] = {"universal_test": {}}

    result = run_cli_command("service", "connect", runtime=runtime)
    assert "universal_test" in result.output


def test_service_connect():
    runtime = BaseCumulusCI(
        config={"services": {"test": {"attributes": {"attr": {"required": False}}}}}
    )

    run_cli_command("service", "connect", "test", "test-alias", runtime=runtime)

    assert "test-alias" in runtime.keychain.list_services()["test"]


def test_service_connect__attr_with_default_value():
    runtime = BaseCumulusCI(
        config={
            "services": {
                "test": {
                    "attributes": {
                        "attr": {"default": "PRESET", "description": "example"}
                    }
                }
            }
        },
    )

    result = run_cli_command(
        "service", "connect", "test", "test-alias", runtime=runtime, input="\n"
    )

    # User should have been prompted to override the default,
    # but input of an empty line accepts the default.
    assert "attr (example) [PRESET]: " in result.output
    service_config = runtime.keychain.get_service("test", "test-alias")
    with mock.patch(
        "cumulusci.core.config.base_config.STRICT_GETATTR", False
    ), pytest.warns(DeprecationWarning, match="attr"):
        assert service_config.lookup("attr") == "PRESET"
        assert service_config.attr == "PRESET"


def test_service_connect__attr_with_default_factory():
    runtime = BaseCumulusCI(
        config={
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

    run_cli_command("service", "connect", "test", "test-alias", runtime=runtime)

    # The service should have the attribute value returned by the default factory.
    service_config = runtime.keychain.get_service("test", "test-alias")
    with mock.patch(
        "cumulusci.core.config.base_config.STRICT_GETATTR", False
    ), pytest.warns(DeprecationWarning, match="attr"):
        assert service_config.lookup("attr") == "CALCULATED"
        assert service_config.attr == "CALCULATED"


def test_service_connect__alias_already_exists():
    runtime = BaseCumulusCI(
        config={
            "services": {"test-type": {"attributes": {"attr": {"required": True}}}}
        },
    )
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
    with mock.patch(
        "cumulusci.core.config.base_config.STRICT_GETATTR", False
    ), pytest.warns(DeprecationWarning, match="attr"):
        assert service_config.lookup("attr") == "new"
        assert service_config.attr == "new"


def test_service_connect__set_new_service_as_default():
    runtime = BaseCumulusCI(
        config={
            "services": {"test-type": {"attributes": {"attr": {"required": False}}}}
        }
    )
    runtime.keychain.set_service("test-type", "existing-service", ServiceConfig({}))

    run_cli_command(
        "service", "connect", "test-type", "new-service", runtime=runtime, input="y\n"
    )

    assert runtime.keychain.get_default_service_name("test-type") == "new-service"


def test_service_connect__do_not_set_new_service_as_default():
    runtime = BaseCumulusCI(
        config={
            "services": {"test-type": {"attributes": {"attr": {"required": False}}}}
        }
    )
    runtime.keychain.set_service("test-type", "existing-service", ServiceConfig({}))

    run_cli_command(
        "service", "connect", "test-type", "new-service", input="n\n", runtime=runtime
    )

    assert runtime.keychain.get_default_service_name("test-type") == "existing-service"


def test_service_connect__no_name_given():
    runtime = BaseCumulusCI(
        config={
            "services": {"test-type": {"attributes": {"attr": {"required": False}}}}
        }
    )

    result = run_cli_command("service", "connect", "test-type", runtime=runtime)

    # service_name is None, so the alias when setting the service should be 'default'
    assert (
        "No service name specified. Using 'default' as the service name."
        in result.output
    )
    assert "default" in runtime.keychain.list_services()["test-type"]


def test_service_connect__global_default():
    runtime = BaseCumulusCI(
        config={"services": {"test": {"attributes": {"attr": {"required": False}}}}}
    )

    result = run_cli_command(
        "service", "connect", "test", "test-alias", "--default", runtime=runtime
    )

    assert "Service test:test-alias is now connected" in result.output
    assert (
        "Service test:test-alias is now the default for all CumulusCI projects"
        in result.output
    )


def test_service_connect__project_default():
    runtime = BaseCumulusCI(
        config={"services": {"test": {"attributes": {"attr": {"required": False}}}}}
    )

    result = run_cli_command(
        "service", "connect", "test", "test-alias", "--project", runtime=runtime
    )

    assert "Service test:test-alias is now connected" in result.output
    assert "Service test:test-alias is now the default for project" in result.output


def test_service_connect__global_keychain():
    runtime = BaseCumulusCI()
    runtime.project_config = None
    runtime.keychain.project_config = runtime.universal_config
    runtime.universal_config.config["services"] = {
        "test": {"attributes": {"attr": {"required": False}}}
    }

    run_cli_command("service", "connect", "test", "test-alias", runtime=runtime)

    assert "test-alias" in runtime.keychain.list_services()["test"]


def test_service_connect__invalid_service():
    runtime = BaseCumulusCI()
    with pytest.raises(click.UsageError):
        run_cli_command("service", "connect", "test", runtime=runtime)


def test_service_connect_validator():
    runtime = BaseCumulusCI(
        config={
            "services": {
                "test": {
                    "attributes": {},
                    "validator": "cumulusci.cli.tests.test_service.validate_service",
                }
            }
        }
    )

    run_cli_command("service", "connect", "test", "test-alias", runtime=runtime)

    service_config = runtime.keychain.get_service("test", "test-alias")
    assert service_config.config == {"service_name": "test-alias", "key": "value"}


def test_service_connect_validator_failure():
    runtime = BaseCumulusCI(
        config={
            "services": {
                "test": {
                    "attributes": {},
                    "validator": "cumulusci.cli.tests.test_service.validate_service_error",
                }
            }
        }
    )

    with pytest.raises(Exception, match="Validation failed"):
        run_cli_command("service", "connect", "test", "test-alias", runtime=runtime)


def test_service_connect__connected_app():
    runtime = BaseCumulusCI()
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
    runtime = BaseCumulusCI()
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


def test_service_info():
    runtime = BaseCumulusCI(
        config={
            "services": {
                "test": {
                    "attributes": {
                        "sensitive_attr": {"sensitive": True},
                        "non_sensitive_attr": {},
                    }
                }
            }
        }
    )
    runtime.keychain.set_service(
        "test",
        "test-alias",
        ServiceConfig({"sensitive_attr": "abcdefgh", "non_sensitive_attr": 1}),
    )

    result = run_cli_command("service", "info", "test", "test-alias", runtime=runtime)
    assert (
        result.output
        == """            test:test-alias            
                                       
  Key                        Value     
 ───────────────────────────────────── 
  \x1b[1msensitive_attr\x1b[0m       ********  
  \x1b[1mnon_sensitive_attr\x1b[0m   1         
                                       
"""  # noqa: W291,W293
    )


def test_service_info_json():
    runtime = BaseCumulusCI(
        config={
            "services": {
                "test": {
                    "attributes": {
                        "sensitive_attr": {"sensitive": True},
                        "non_sensitive_attr": {},
                    }
                }
            }
        }
    )
    runtime.keychain.set_service(
        "test",
        "test-alias",
        ServiceConfig({"sensitive_attr": "abcdefgh", "non_sensitive_attr": True}),
    )
    result = run_cli_command(
        "service", "info", "test", "test-alias", "--json", runtime=runtime
    )

    assert (
        result.output == '{"sensitive_attr": "abcdefgh", "non_sensitive_attr": true}\n'
    )  # noqa: W291,W293


def test_get_service_data():
    service_config = ServiceConfig(
        {
            "sensitive_attr": "abcdef",
            "other_secret": "abcdefghijk",
            "non_sensitive_attr": "hellothere",
        }
    )
    result = get_service_data(service_config, ["sensitive_attr", "other_secret"])
    assert result == [
        ["Key", "Value"],
        ["\x1b[1msensitive_attr\x1b[0m", "******"],
        ["\x1b[1mother_secret\x1b[0m", "abcde******"],
        ["\x1b[1mnon_sensitive_attr\x1b[0m", "hellothere"],
    ]


def test_get_sensitive_service_attributes():
    runtime = BaseCumulusCI(
        config={
            "services": {
                "universal_test": {
                    "attributes": {
                        "sensitive_attr": {"sensitive": True},
                        "non_sensitive_attr": {},
                    }
                }
            }
        }
    )
    result = get_sensitive_service_attributes(runtime, "universal_test")
    assert result == ["sensitive_attr"]


def test_service_info_not_configured():
    runtime = BaseCumulusCI()
    result = run_cli_command("service", "info", "test", "test-alias", runtime=runtime)
    assert "not configured for this project" in result.output


def test_service_default__global():
    runtime = BaseCumulusCI(config={"services": {"test": {"attributes": {}}}})
    runtime.keychain.set_service("test", "test-alias", ServiceConfig({}))
    runtime.keychain._default_services["test"] = None

    result = run_cli_command(
        "service", "default", "test", "test-alias", runtime=runtime
    )

    assert (
        "Service test:test-alias is now the default for all CumulusCI projects"
        in result.output
    )
    assert runtime.keychain.get_default_service_name("test") == "test-alias"


def test_service_default__project():
    runtime = BaseCumulusCI(config={"services": {"test": {"attributes": {}}}})
    runtime.keychain.project_local_dir = "test"
    runtime.keychain.set_service("test", "test-alias", ServiceConfig({}))
    runtime.keychain._default_services["test"] = None

    result = run_cli_command(
        "service", "default", "test", "test-alias", "--project", runtime=runtime
    )

    assert (
        "Service test:test-alias is now the default for project 'test'" in result.output
    )
    assert runtime.keychain.get_default_service_name("test") == "test-alias"


def test_service_connect__project_default_no_project():
    runtime = BaseCumulusCI()
    runtime.project_config = None
    runtime.keychain.project_config = runtime.universal_config

    with pytest.raises(click.UsageError):
        run_cli_command(
            "service", "default", "test", "test-alias", "--project", runtime=runtime
        )


def test_service_default__bad_service_type():
    runtime = BaseCumulusCI()
    result = run_cli_command(
        "service", "default", "no-such-type", "test-alias", runtime=runtime
    )
    assert (
        "An error occurred setting the default service: No services of type no-such-type are currently configured"
        in result.output
    )


def test_service_rename():
    expected_config = {"a": "a"}
    runtime = BaseCumulusCI(config={"services": {"test-type": {"attributes": {}}}})
    runtime.keychain.set_service(
        "test-type", "old-alias", ServiceConfig(expected_config)
    )

    result = run_cli_command(
        "service", "rename", "test-type", "old-alias", "new-alias", runtime=runtime
    )

    assert "Service test-type:old-alias has been renamed to new-alias" in result.output
    assert list(runtime.keychain.list_services()["test-type"]) == ["new-alias"]
    service_config = runtime.keychain.get_service("test-type", "new-alias")
    assert service_config.config == expected_config


def test_service_rename__bad_service_type():
    runtime = BaseCumulusCI()
    result = run_cli_command(
        "service", "rename", "test-type", "old-alias", "new-alias", runtime=runtime
    )
    assert (
        "An error occurred renaming the service: No services of type test-type are currently configured"
        in result.output
    )


def test_service_remove():
    runtime = BaseCumulusCI(config={"services": {"test-type": {"attributes": {}}}})
    runtime.keychain.env_service_var_prefix = "CUMULUSCI_SERVICE_"
    runtime.keychain.set_service(
        "test-type", "current-default-alias", ServiceConfig({})
    )
    runtime.keychain.set_service("test-type", "other-alias", ServiceConfig({}))
    runtime.keychain.set_service("test-type", "future-default-alias", ServiceConfig({}))

    result = run_cli_command(
        "service",
        "remove",
        "test-type",
        "current-default-alias",
        input="future-default-alias\n",
        runtime=runtime,
    )

    assert "Service test-type:current-default-alias has been removed." in result.output
    assert "current-default-alias" not in runtime.keychain.list_services()["test-type"]
    assert (
        runtime.keychain.get_default_service_name("test-type") == "future-default-alias"
    )


def test_service_remove__new_default_does_not_exist():
    runtime = BaseCumulusCI(config={"services": {"test-type": {"attributes": {}}}})
    runtime.keychain.env_service_var_prefix = "CUMULUSCI_SERVICE_"
    runtime.keychain.set_service(
        "test-type", "current-default-alias", ServiceConfig({})
    )
    runtime.keychain.set_service("test-type", "other-alias-1", ServiceConfig({}))
    runtime.keychain.set_service("test-type", "other-alias-2", ServiceConfig({}))
    result = run_cli_command(
        "service",
        "remove",
        "test-type",
        "current-default-alias",
        input="this-alias-does-not-exist\n",
        runtime=runtime,
    )
    assert (
        "No service of type test-type with name: this-alias-does-not-exist"
        in result.output
    )
    assert "current-default-alias" in runtime.keychain.list_services()["test-type"]
    assert (
        runtime.keychain.get_default_service_name("test-type")
        == "current-default-alias"
    )


def test_service_remove__bad_service_name():
    runtime = BaseCumulusCI(config={"services": {"test-type": {"attributes": {}}}})
    runtime.keychain.env_service_var_prefix = "CUMULUSCI_SERVICE_"
    result = run_cli_command(
        "service",
        "remove",
        "test-type",
        "bogus",
        runtime=runtime,
    )
    assert (
        "An error occurred removing the service: No services of type test-type are currently configured"
        in result.output
    )


def test_service_remove__environment_service_cannot_be_removed():
    runtime = BaseCumulusCI(config={"services": {"test-type": {"attributes": {}}}})
    runtime.keychain.env_service_var_prefix = "CUMULUSCI_SERVICE_"
    runtime.keychain.set_service("test-type", "env-foo", ServiceConfig({}))
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


def validate_service(options, keychain):
    return {"key": "value"}


def validate_service_error(options, keychain):
    raise Exception("Validation failed")


def get_default():
    return "CALCULATED"
