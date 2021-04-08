"""Tests for the RunTaskCommand class"""

from cumulusci.cli.runtime import CliRuntime
from cumulusci.cli.cci import RunTaskCommand
import click
import pytest
from unittest.mock import Mock, patch

from cumulusci.cli import cci
from cumulusci.core.exceptions import CumulusCIUsageError
from cumulusci.cli.tests.utils import DummyTask

color_opts = {"options": {"color": {}}}
multiple_opts = {"options": {"foo": {}, "bar": {}, "baz": {}}}

test_tasks = {
    "dummy-task": {
        "class_path": "cumulusci.cli.tests.utils.DummyTask",
        "description": "This is a dummy task.",
    },
    "dummy-derived-task": {
        "class_path": "cumulusci.cli.tests.test_run_task.DummyDerivedTask"
    },
}


@pytest.fixture
def runtime():
    runtime = CliRuntime(load_keychain=False)
    runtime.project_config.config["tasks"] = {**test_tasks}

    runtime.keychain = Mock()
    runtime.keychain.get_default_org.return_value = (None, None)

    yield runtime


def test_task_run(runtime):
    DummyTask._run_task = Mock()
    multi_cmd = cci.RunTaskCommand()
    with click.Context(multi_cmd, obj=runtime) as ctx:
        cmd = multi_cmd.get_command(ctx, "dummy-task")
        cmd.callback(runtime, "dummy-task", color="blue")

    DummyTask._run_task.assert_called_once()


def test_task_run__no_project(runtime):
    runtime.project_config = None
    runtime.project_config_error = Exception("Broken")
    multi_cmd = cci.RunTaskCommand()
    with pytest.raises(Exception, match="Broken"):
        with click.Context(multi_cmd, obj=runtime) as ctx:
            multi_cmd.get_command(ctx, "dummy-task")


def test_task_run__debug_before(runtime):
    DummyTask._run_task = Mock()
    multi_cmd = cci.RunTaskCommand()
    set_trace = Mock(side_effect=SetTrace)

    with click.Context(multi_cmd, obj=runtime) as ctx:
        with patch("pdb.set_trace", set_trace):
            with pytest.raises(SetTrace):
                cmd = multi_cmd.get_command(ctx, "dummy-task")
                cmd.callback(
                    runtime,
                    "dummy_task",
                    color="blue",
                    debug_before=True,
                    debug_after=False,
                )


def test_task_run__debug_after(runtime):
    DummyTask._run_task = Mock()
    multi_cmd = cci.RunTaskCommand()
    set_trace = Mock(side_effect=SetTrace)

    with click.Context(multi_cmd, obj=runtime) as ctx:
        with patch("pdb.set_trace", set_trace):
            with pytest.raises(SetTrace):
                cmd = multi_cmd.get_command(ctx, "dummy-task")
                cmd.callback(
                    runtime,
                    "dummy-task",
                    color="blue",
                    debug_before=False,
                    debug_after=True,
                )


def test_task_run__help(runtime):
    DummyTask._run_task = Mock()
    multi_cmd = cci.RunTaskCommand()
    with click.Context(multi_cmd, obj=runtime) as ctx:
        cmd = multi_cmd.get_command(ctx, "dummy-task")

    assert "This is a dummy task." in cmd.help  # task description


def test_task_run__list_commands(runtime):
    multi_cmd = cci.RunTaskCommand()
    with click.Context(multi_cmd, obj=runtime) as ctx:
        commands = multi_cmd.list_commands(ctx)
    assert commands == ["dummy-derived-task", "dummy-task"]


def test_format_help(runtime):
    with patch("cumulusci.cli.cci.click.echo") as echo:
        runtime.universal_config = Mock()
        multi_cmd = cci.RunTaskCommand()
        with click.Context(multi_cmd, obj=runtime) as ctx:
            multi_cmd.format_help(ctx, Mock())
        assert 4 == echo.call_count

        assert 0 == len(runtime.universal_config.method_calls)


def test_get_default_command_options():
    opts = RunTaskCommand()._get_default_command_options(is_salesforce_task=False)
    assert len(opts) == 4

    opts = RunTaskCommand()._get_default_command_options(is_salesforce_task=True)
    assert len(opts) == 5
    assert any([o.name == "org" for o in opts])


def test_collect_task_options():
    new_options = {"debug-before": None}
    old_options = (("color", "green"),)

    opts = RunTaskCommand()._collect_task_options(
        new_options, old_options, "dummy-task", color_opts["options"]
    )
    assert opts == {"color": "green"}


def test_collect_task_options__duplicate():
    new_options = {"color": "aqua"}
    old_options = (("color", "green"),)

    with pytest.raises(CumulusCIUsageError):
        RunTaskCommand()._collect_task_options(
            new_options, old_options, "dummy-task", color_opts["options"]
        )


def test_collect_task_options__not_in_task():
    new_options = {}
    old_options = (("color", "green"),)

    with pytest.raises(CumulusCIUsageError):
        RunTaskCommand()._collect_task_options(
            new_options, old_options, "dummy-task", {"not-color": {}}
        )


class SetTrace(Exception):
    pass


class DummyDerivedTask(DummyTask):
    def _run_task(self):
        click.echo(f"<{self.__class__}>\n\tcolor: {self.options['color']}")
