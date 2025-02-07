from unittest import mock

import click
import pytest

from cumulusci.cli.runtime import CliRuntime

from .. import checks
from .utils import run_click_command


@pytest.fixture
def runtime():
    runtime = CliRuntime()
    runtime.project_config.config["plans"] = {
        "plan 1": {
            "title": "Test Plan #1",
            "slug": "plan1_slug",
            "tier": "primary",
            "preflight_message": "This is a preflight message",
            "error_message": "This is an error message",
            "steps": {
                1: {
                    "task": "run_tests",
                    "ui_options": {
                        "name": "Run Tests",
                        "is_recommended": False,
                        "is_required": False,
                    },
                    "checks": [
                        {
                            "when": "soon",
                            "action": "error",
                            "message": "Danger Will Robinson!",
                        }
                    ],
                }
            },
            "checks": [
                {
                    "when": "'test package' not in tasks.get_installed_packages()",
                    "action": "error",
                    "message": "Test Package must be installed in your org.",
                }
            ],
        },
    }

    yield runtime


@mock.patch("cumulusci.cli.checks.CliTable")
def test_checks_info(cli_table, runtime):

    run_click_command(checks.checks_info, runtime=runtime, plan_name="plan 1")
    cli_table.assert_called_once_with(
        title="Plan Preflights",
        data=[
            ["Action", "Message", "When"],
            [
                "error",
                "Test Package must be installed in your org.",
                "'test package' not in tasks.get_installed_packages()",
            ],
        ],
    )


@mock.patch("cumulusci.cli.checks.PreflightFlowCoordinator")
def test_checks_run(mock_flow_coordinator, runtime):
    org_config = mock.Mock(scratch=True, config={})
    org_config.username = "test_user"
    org_config.org_id = "test_org_id"
    runtime.get_org = mock.Mock(return_value=("test", org_config))

    mock_flow_coordinator_return_value = mock.Mock()
    mock_flow_coordinator_return_value.preflight_results = {}  # No errors or warnings
    mock_flow_coordinator.return_value = mock_flow_coordinator_return_value
    with mock.patch("logging.getLogger") as mock_logger:

        run_click_command(
            checks.checks_run,
            runtime=runtime,
            plan_name="plan 1",
            org="test",
        )
        mock_logger.assert_called()
        mock_flow_coordinator.assert_called_once_with(
            runtime.project_config, mock.ANY, name="preflight"
        )


@mock.patch("cumulusci.cli.checks.PreflightFlowCoordinator")
@mock.patch("logging.getLogger")
def test_checks_run_unknown_plan(mock_flow_coordinator, mock_logger, runtime):
    org_config = mock.Mock(scratch=True, config={})
    org_config.username = "test_user"
    org_config.org_id = "test_org_id"
    runtime.get_org = mock.Mock(return_value=("test", org_config))

    mock_flow_coordinator_return_value = mock.Mock()
    mock_flow_coordinator_return_value.preflight_results = {}  # No errors or warnings
    mock_flow_coordinator.return_value = mock_flow_coordinator_return_value
    with pytest.raises(click.UsageError) as error:

        run_click_command(
            checks.checks_run,
            runtime=runtime,
            plan_name="unknown plan",
            org="test",
        )
        mock_flow_coordinator.assert_called_once_with(
            runtime.project_config, mock.ANY, name="preflight"
        )
        assert "Unknown plan 'unknown_plan'" in error.value


@mock.patch("cumulusci.cli.checks.PreflightFlowCoordinator")
def test_checks_run_with_warnings(mock_flow_coordinator, runtime):
    org_config = mock.Mock(scratch=True, config={})
    org_config.username = "test_user"
    org_config.org_id = "test_org_id"
    runtime.get_org = mock.Mock(return_value=("test", org_config))

    mock_flow_coordinator.return_value.preflight_results = {
        None: [
            {
                "status": "warning",
                "message": "You need Context Service AdminPsl in your Org assigned Admin User to use this feature. Contact your Administrator.",
            }
        ]
    }

    run_click_command(
        checks.checks_run,
        runtime=runtime,
        plan_name="plan 1",
        org="test",
    )
    mock_flow_coordinator.assert_called_once_with(
        runtime.project_config, mock.ANY, name="preflight"
    )


@mock.patch("cumulusci.cli.checks.PreflightFlowCoordinator")
def test_checks_run_with_errors(mock_flow_coordinator, runtime):
    org_config = mock.Mock(scratch=True, config={})
    org_config.username = "test_user"
    org_config.org_id = "test_org_id"
    runtime.get_org = mock.Mock(return_value=("test", org_config))

    mock_flow_coordinator.return_value.preflight_results = {
        None: [
            {
                "status": "error",
                "message": "You need Context Service AdminPsl in your Org assigned Admin User to use this feature. Contact your Administrator.",
            }
        ]
    }
    with pytest.raises(Exception) as error:

        run_click_command(
            checks.checks_run,
            runtime=runtime,
            plan_name="plan 1",
            org="test",
        )
        mock_flow_coordinator.assert_called_once_with(
            runtime.project_config, mock.ANY, name="preflight"
        )
        assert (
            "Some of the checks failed with errors. Please check the logs for details."
            in error.value
        )
