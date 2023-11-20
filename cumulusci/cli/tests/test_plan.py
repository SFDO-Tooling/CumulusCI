import json
from unittest import mock

import click
import pytest

from cumulusci.cli.runtime import CliRuntime

from .. import plan
from .utils import run_click_command

pytestmark = pytest.mark.metadeploy


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
        "plan 2": {
            "title": "Test Plan #2",
            "slug": "plan2_slug",
            "tier": "secondary",
        },
        "plan 3": {
            "title": "Test Plan #3",
            "slug": "plan3_slug",
            "tier": "additional",
            "group": "optional",
        },
    }

    yield runtime


class TestPlanList:
    @mock.patch("cumulusci.cli.plan.CliTable")
    def test_plan_list(self, cli_table, runtime):
        """Happy-path smoke test"""

        run_click_command(plan.plan_list, runtime=runtime, print_json=False)

        cli_table.assert_called_once_with(
            data=[
                ["Name", "Title", "Slug", "Tier"],
                ["plan 1", "Test Plan #1", "plan1_slug", "primary"],
                ["plan 2", "Test Plan #2", "plan2_slug", "secondary"],
                ["plan 3", "Test Plan #3", "plan3_slug", "additional"],
            ]
        )

    @mock.patch("cumulusci.cli.plan.CliTable")
    def test_plan_list__no_plans(self, cli_table, runtime):
        """Make sure we gracefully handle projects with no plans"""
        runtime.project_config.config["plans"] = []

        run_click_command(plan.plan_list, runtime=runtime, print_json=False)

        assert cli_table.call_count == 1
        cli_table.assert_called_once_with(data=[["Name", "Title", "Slug", "Tier"]])

    def test_plan_list__json(self, runtime):
        """Verify we get valid json output with --json"""
        stdout = []
        with mock.patch("click.echo", stdout.append):
            run_click_command(plan.plan_list, runtime=runtime, print_json=True)
            assert len(stdout) == 1
            data = json.loads(stdout[0])
            assert data == [
                {
                    "name": "plan 1",
                    "title": "Test Plan #1",
                    "slug": "plan1_slug",
                    "tier": "primary",
                },
                {
                    "name": "plan 2",
                    "title": "Test Plan #2",
                    "slug": "plan2_slug",
                    "tier": "secondary",
                },
                {
                    "name": "plan 3",
                    "title": "Test Plan #3",
                    "slug": "plan3_slug",
                    "tier": "additional",
                },
            ]

    @mock.patch("cumulusci.cli.plan.CliTable")
    def test_plan_list__sorting(self, cli_table):
        runtime = CliRuntime()
        # define some plans in reverse order from how they
        # should appear...
        runtime.project_config.config["plans"] = {
            "Plan 4": dict(tier="additional"),
            "Plan 3": dict(tier="additional"),
            "Plan 2": dict(tier="secondary"),
            "Plan 1": dict(tier="primary"),
        }

        run_click_command(plan.plan_list, runtime=runtime, print_json=False)
        cli_table.assert_called_once_with(
            data=[
                ["Name", "Title", "Slug", "Tier"],
                ["Plan 1", "", "", "primary"],
                ["Plan 2", "", "", "secondary"],
                ["Plan 3", "", "", "additional"],
                ["Plan 4", "", "", "additional"],
            ],
        )


class TestPlanInfo:
    @mock.patch("cumulusci.cli.plan.CliTable")
    def test_plan_info__config(self, cli_table, runtime):
        """Verify we are creating a CliTable for the config"""
        run_click_command(
            plan.plan_info, "plan 1", runtime=runtime, messages_only=False
        )
        cli_table.assert_any_call(
            title="Config",
            data=[
                ["Key", "Value"],
                ["YAML Key", "plan 1"],
                ["Slug", "plan1_slug"],
                ["Tier", "primary"],
                ["Hidden?", False],
            ],
        ),

    @mock.patch("cumulusci.cli.plan.CliTable")
    def test_plan_info__messages(self, cli_table, runtime):
        """Verify we are creating a CliTable for messages"""
        run_click_command(
            plan.plan_info, "plan 1", runtime=runtime, messages_only=False
        )
        cli_table.assert_any_call(
            title="Messages",
            data=[
                ["Type", "Message"],
                ["Title", "Test Plan #1"],
                ["Preflight", "This is a preflight message"],
                ["Post-install", ""],
                ["Error", "This is an error message"],
            ],
        )

    @mock.patch("cumulusci.cli.plan.CliTable")
    def test_plan_info__preflight_checks(self, cli_table, runtime):
        """Verify we are creating a CliTable for the preflight checks"""
        run_click_command(
            plan.plan_info, "plan 1", runtime=runtime, messages_only=False
        )
        cli_table.assert_any_call(
            title="Plan Preflights",
            data=[
                ["Action", "Message", "When"],
                [
                    "error",
                    "Test Package must be installed in your org.",
                    "'test package' not in tasks.get_installed_packages()",
                ],
            ],
        ),

    @mock.patch("cumulusci.cli.plan.CliTable")
    def test_plan_info__step_preflight_checks(self, cli_table, runtime):
        """Verify we are creating a CliTable for the step preflight checks"""
        run_click_command(
            plan.plan_info, "plan 1", runtime=runtime, messages_only=False
        )
        cli_table.assert_any_call(
            title="Step Preflights",
            data=[
                ["Step", "Action", "Message", "When"],
                [1, "error", "Danger Will Robinson!", "soon"],
            ],
        ),

    @mock.patch("cumulusci.cli.plan.CliTable")
    def test_plan_info__steps(self, cli_table, runtime):
        """Verify we are creating a CliTable for the preflight checks"""
        run_click_command(
            plan.plan_info, "plan 1", runtime=runtime, messages_only=False
        )
        cli_table.assert_any_call(
            title="Steps",
            data=[
                ["Step", "Name", "Required", "Recommended"],
                [1, "Run Tests", False, False],
            ],
        )

    @mock.patch("cumulusci.cli.plan.CliTable")
    def test_plan_info__messages_only(self, cli_table, runtime):
        """Verify that --messages results in only messages being output"""
        run_click_command(plan.plan_info, "plan 1", runtime=runtime, messages_only=True)
        cli_table.assert_called_once_with(
            title="Messages",
            data=[
                ["Type", "Message"],
                ["Title", "Test Plan #1"],
                ["Preflight", "This is a preflight message"],
                ["Post-install", ""],
                ["Error", "This is an error message"],
            ],
        )

    def test_plan_info__bogus_plan(self, runtime):
        """Verify a missing play causes a useful message"""
        with pytest.raises(click.UsageError, match=r"Unknown plan 'invalid_plan'."):
            run_click_command(
                plan.plan_info, "invalid_plan", runtime=runtime, messages_only=False
            )
