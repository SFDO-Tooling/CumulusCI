import json
from unittest import mock

import pytest

from cumulusci.cli.runtime import CliRuntime

from .. import plan
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


class TestPlanCommands:
    @mock.patch("cumulusci.cli.plan.CliTable")
    def test_plan_list(self, cli_table, runtime):
        """Happy-path smoke test"""

        run_click_command(plan.plan_list, runtime=runtime, print_json=False)

        cli_table.assert_has_calls(
            [
                mock.call(
                    title="Optional",
                    data=[
                        ["Name", "Title", "Slug", "Tier"],
                        ["plan 3", "Test Plan #3", "plan3_slug", "additional"],
                    ],
                ),
                mock.call(
                    title="Uncategorized Plans",
                    data=[
                        ["Name", "Title", "Slug", "Tier"],
                        ["plan 1", "Test Plan #1", "plan1_slug", "primary"],
                        ["plan 2", "Test Plan #2", "plan2_slug", "secondary"],
                    ],
                ),
            ]
        )

    @mock.patch("cumulusci.cli.plan.CliTable")
    def test_plan_list__no_plans(self, cli_table, runtime):
        """Make sure we gracefully handle projects with no plans"""
        runtime.project_config.config["plans"] = []

        run_click_command(plan.plan_list, runtime=runtime, print_json=False)

        assert cli_table.call_count == 1
        cli_table.assert_has_calls(
            [
                mock.call(
                    title="Uncategorized Plans",
                    data=[["Name", "Title", "Slug", "Tier"]],
                ),
            ]
        )

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
                    "group": "",
                    "title": "Test Plan #1",
                    "slug": "plan1_slug",
                    "tier": "primary",
                },
                {
                    "name": "plan 2",
                    "group": "",
                    "title": "Test Plan #2",
                    "slug": "plan2_slug",
                    "tier": "secondary",
                },
                {
                    "name": "plan 3",
                    "group": "optional",
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
            "Plan 6": dict(tier="additional", group="Group B"),
            "Plan 5": dict(tier="secondary", group="Group B"),
            "Plan 4": dict(tier="primary", group="Group B"),
            "Plan 3": dict(tier="additional", group="Group A"),
            "Plan 2": dict(tier="secondary", group="Group A"),
            "Plan 1": dict(tier="primary", group="Group A"),
            "Another Plan": dict(tier="primary", group=""),
        }

        run_click_command(plan.plan_list, runtime=runtime, print_json=False)
        assert cli_table.call_count == 3
        cli_table.assert_has_calls(
            [
                mock.call(
                    title="Group A",
                    data=[
                        ["Name", "Title", "Slug", "Tier"],
                        ["Plan 1", "", "", "primary"],
                        ["Plan 2", "", "", "secondary"],
                        ["Plan 3", "", "", "additional"],
                    ],
                ),
                mock.call(
                    title="Group B",
                    data=[
                        ["Name", "Title", "Slug", "Tier"],
                        ["Plan 4", "", "", "primary"],
                        ["Plan 5", "", "", "secondary"],
                        ["Plan 6", "", "", "additional"],
                    ],
                ),
                mock.call(
                    title="Uncategorized Plans",
                    data=[
                        ["Name", "Title", "Slug", "Tier"],
                        ["Another Plan", "", "", "primary"],
                    ],
                ),
            ]
        )
