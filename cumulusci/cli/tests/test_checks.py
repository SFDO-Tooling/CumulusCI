from unittest import mock

from cumulusci.cli.runtime import CliRuntime

from .. import checks
from .utils import run_click_command


@mock.patch("click.echo")
def test_flow_info(echo):

    runtime = CliRuntime(
        config={
            "flows": {
                "test": {
                    "steps": {
                        1: {
                            "task": "test_task",
                            "options": {"option_name": "option_value"},
                        }
                    }
                }
            },
            "tasks": {
                "test_task": {
                    "class_path": "cumulusci.cli.tests.test_flow.DummyTask",
                    "description": "Test Task",
                }
            },
        },
        load_keychain=False,
    )

    run_click_command(checks.checks_info, runtime=runtime, plan_name="test")

    echo.assert_called_with("This plan has the following preflight checks: ")


@mock.patch("click.echo")
def test_checks_run(echo):
    org_config = mock.Mock(scratch=True, config={})
    runtime = CliRuntime(
        config={
            "flows": {"test": {"steps": {1: {"task": "test_task"}}}},
            "tasks": {
                "test_task": {
                    "class_path": "cumulusci.cli.tests.test_flow.DummyTask",
                    "description": "Test Task",
                }
            },
        },
        load_keychain=False,
    )
    runtime.get_org = mock.Mock(return_value=("test", org_config))

    run_click_command(
        checks.checks_run,
        runtime=runtime,
        plan_name="test",
        org="test",
    )

    echo.assert_called_with("Running checks for the plan test")
