"""Tests for the RunTaskCommand"""

from cumulusci.cli.cci import RunTaskCommand
import click
import pytest
from unittest.mock import Mock, patch

from cumulusci.cli import cci
from cumulusci.core.config import BaseProjectConfig
from cumulusci.cli.tests.utils import run_click_command, DummyTask


@pytest.fixture
def runtime():
    runtime = Mock()
    runtime.get_org.return_value = (None, None)
    runtime.project_config = BaseProjectConfig(
        None,
        config={
            "tasks": {
                "DummyTask": {"class_path": "cumulusci.cli.tests.utils.DummyTask"}
            }
        },
    )
    return runtime


def test_task_run(runtime):
    DummyTask._run_task = Mock()
    multi_cmd = cci.RunTaskCommand()
    with patch("cumulusci.cli.cci.RUNTIME", runtime):
        cmd = multi_cmd.get_command(Mock(), "DummyTask")
        run_click_command(cmd, "dummy_task", color="blue", runtime=runtime)

    DummyTask._run_task.assert_called_once()


def test_task_run__debug_before(runtime):
    DummyTask._run_task = Mock()
    multi_cmd = cci.RunTaskCommand()

    set_trace = Mock(side_effect=SetTrace)
    with patch("cumulusci.cli.cci.RUNTIME", runtime):
        with patch("pdb.set_trace", set_trace):
            with pytest.raises(SetTrace):
                cmd = multi_cmd.get_command(Mock(), "DummyTask")
                run_click_command(
                    cmd,
                    "dummy_task",
                    color="blue",
                    debug_before=True,
                    debug_after=False,
                    runtime=runtime,
                )


def test_task_run__debug_after(runtime):
    DummyTask._run_task = Mock()
    multi_cmd = cci.RunTaskCommand()

    set_trace = Mock(side_effect=SetTrace)
    with patch("cumulusci.cli.cci.RUNTIME", runtime):
        with patch("pdb.set_trace", set_trace):
            with pytest.raises(SetTrace):
                cmd = multi_cmd.get_command(Mock(), "DummyTask")
                run_click_command(
                    cmd,
                    "dummy_task",
                    color="blue",
                    debug_before=False,
                    debug_after=True,
                    runtime=runtime,
                )


def test_task_run__list_commands(runtime):
    multi_cmd = cci.RunTaskCommand()
    with patch("cumulusci.cli.cci.RUNTIME", runtime):
        commands = multi_cmd.list_commands(Mock())
    assert commands == ["DummyTask"]


def test_task_run__resolve_command(runtime):
    multi_cmd = cci.RunTaskCommand()
    args = ["dummy_task", "-o", "color", "blue"]
    runtime.project_config = BaseProjectConfig(
        None,
        config={
            "tasks": {
                "dummy_task": {"class_path": "cumulusci.cli.tests.test_cci.DummyTask"}
            }
        },
    )

    with patch("cumulusci.cli.cci.RUNTIME", runtime):
        cmd_name, cmd, args = multi_cmd.resolve_command(Mock(), args)

    assert cmd_name == "dummy_task"
    assert isinstance(cmd, click.Command)
    assert args == [
        "--color",
        "blue",
    ]


def test_convert_old_option_syntax__nothing_to_convert():
    args = ["task", "run", "util_sleep", "--seconds", "3.88"]
    converted = RunTaskCommand()._convert_old_option_syntax(args)
    assert args == converted


class SetTrace(Exception):
    pass
