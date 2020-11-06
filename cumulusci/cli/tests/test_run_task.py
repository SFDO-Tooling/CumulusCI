"""Tests for the RunTaskCommand class"""

from cumulusci.cli.runtime import CliRuntime
from cumulusci.cli.cci import RunTaskCommand
import click
import pytest
from unittest.mock import Mock, patch

from cumulusci.cli import cci
from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import CumulusCIUsageError
from cumulusci.cli.tests.utils import run_click_command, DummyTask, MultipleOptionsTask

color_opts = {"options": {"color": {}}}
multiple_opts = {"options": {"foo": {}, "bar": {}, "baz": {}}}

test_tasks = {
    "dummy-task": {"class_path": "cumulusci.cli.tests.utils.DummyTask"},
    "lots-o-options-task": {
        "class_path": "cumulusci.cli.tests.utils.MultipleOptionsTask"
    },
    "dummy-derived-task": {
        "class_path": "cumulusci.cli.tests.test_run_task.DummyDerivedTask"
    },
}


@pytest.fixture
def ctx():
    ctx = Mock()
    ctx.task_class = DummyTask
    return ctx


@pytest.fixture
def runtime():
    runtime = CliRuntime(load_keychain=False)
    runtime.project_config.config["tasks"] = {**test_tasks}

    runtime.keychain = Mock()
    runtime.keychain.get_default_org.return_value = (None, None)

    with patch("cumulusci.cli.cci.RUNTIME", runtime):
        yield runtime


def test_task_run(runtime, ctx):
    DummyTask._run_task = Mock()
    multi_cmd = cci.RunTaskCommand()
    cmd = multi_cmd.get_command(ctx, "dummy-task")

    run_click_command(cmd, "dummy-task", color="blue", runtime=runtime)

    DummyTask._run_task.assert_called_once()


def test_task_run__debug_before(runtime, ctx):
    DummyTask._run_task = Mock()
    multi_cmd = cci.RunTaskCommand()
    set_trace = Mock(side_effect=SetTrace)

    with patch("pdb.set_trace", set_trace):
        with pytest.raises(SetTrace):
            cmd = multi_cmd.get_command(ctx, "dummy-task")
            run_click_command(
                cmd,
                "dummy_task",
                color="blue",
                debug_before=True,
                debug_after=False,
                runtime=runtime,
            )


def test_task_run__debug_after(runtime, ctx):
    DummyTask._run_task = Mock()
    multi_cmd = cci.RunTaskCommand()

    set_trace = Mock(side_effect=SetTrace)
    with patch("pdb.set_trace", set_trace):
        with pytest.raises(SetTrace):
            cmd = multi_cmd.get_command(ctx, "dummy-task")
            run_click_command(
                cmd,
                "dummy-task",
                color="blue",
                debug_before=False,
                debug_after=True,
                runtime=runtime,
            )


def test_task_run__list_commands(runtime, ctx):
    multi_cmd = cci.RunTaskCommand()
    commands = multi_cmd.list_commands(ctx)
    assert commands == ["dummy-derived-task", "dummy-task", "lots-o-options-task"]


def test_task_run__resolve_command(runtime):
    args = ["dummy-task", "-o", "color", "blue"]
    multi_cmd = cci.RunTaskCommand()
    cmd_name, cmd, args = multi_cmd.resolve_command(Mock(), args)

    assert cmd_name == "dummy-task"
    assert isinstance(cmd, click.Command)
    assert args == [
        "--color",
        "blue",
    ]


def test_convert_old_option_syntax__nothing_to_convert(runtime):
    args = ["dummy-task", "--color", "blue"]
    converted = RunTaskCommand()._convert_old_option_syntax(
        args, Mock(task_options={"color": {}})
    )
    assert args == converted


def test_convert_old_option_syntax__convert_single_option(runtime):
    args = ["dummy-task", "-o", "color", "blue"]
    converted = RunTaskCommand()._convert_old_option_syntax(args, DummyTask)

    assert converted == ["dummy-task", "--color", "blue"]


def test_convert_old_option_syntax__convert_multiple_options(runtime):
    args = [
        "lots-o-options-task",
        "-o",
        "foo",
        "fooey",
        "-o",
        "bar",
        "bary",
        "-o",
        "baz",
        "bazzy",
    ]
    task = MultipleOptionsTask(None, TaskConfig(multiple_opts))
    converted = RunTaskCommand()._convert_old_option_syntax(args, task)

    assert converted == [
        "lots-o-options-task",
        "--foo",
        "fooey",
        "--bar",
        "bary",
        "--baz",
        "bazzy",
    ]


def test_convert_old_option_syntax__convert_mixed_options(runtime):
    args = [
        "lots-o-options-task",
        "-o",
        "foo",
        "fooey",
        "--bar",
        "bary",
        "-o",
        "baz",
        "bazzy",
    ]

    converted = RunTaskCommand()._convert_old_option_syntax(args, MultipleOptionsTask)

    assert converted == [
        "lots-o-options-task",
        "--foo",
        "fooey",
        "--bar",
        "bary",
        "--baz",
        "bazzy",
    ]


def test_convert_old_option_syntax__duplicate_option(runtime):
    """We only test duplicate options specified in the old
    option syntax: -o name value. Click takes care of the new
    syntax for us."""
    args = [
        "lots-o-options-task",
        "-o",
        "foo",
        "fooey",
        "--bar",
        "bary",
        "-o",
        "baz",
        "bazzy",
        "-o",
        "foo",
        "duplicate",
    ]

    task = DummyTask(None, TaskConfig(color_opts))
    with pytest.raises(CumulusCIUsageError):
        RunTaskCommand()._convert_old_option_syntax(args, task)


def test_convert_old_option_syntax__extra_dashes(runtime):
    args = [
        "lots-o-options-task",
        "-o",
        "foo",
        "fooey",
        "--bar",
        "bary",
        "-o",
        "baz",
        "-bazzy",
    ]
    task = DummyTask(None, TaskConfig(color_opts))
    # test option value fails
    with pytest.raises(CumulusCIUsageError):
        RunTaskCommand()._convert_old_option_syntax(args, task)

    args[2] = "-foo"
    # test option name fails
    with pytest.raises(CumulusCIUsageError):
        RunTaskCommand()._convert_old_option_syntax(args, task)


def test_convert_old_option_syntax__option_not_found(runtime):
    args = [
        "lots-o-options-task",
        "-o",
        "pizza",
        "olives",
    ]

    task = MultipleOptionsTask(None, TaskConfig(multiple_opts))
    with pytest.raises(CumulusCIUsageError):
        RunTaskCommand()._convert_old_option_syntax(args, task)


def test_option_in_task__true(runtime):
    assert RunTaskCommand()._option_in_task(
        "color", DummyTask(None, TaskConfig(color_opts))
    )


def test_option_in_task__false(runtime):
    assert not RunTaskCommand()._option_in_task(
        "pizza", DummyTask(None, TaskConfig(color_opts))
    )


def test_option_in_task__non_task_option(runtime):
    task = DummyTask(None, TaskConfig(color_opts))
    assert RunTaskCommand()._option_in_task("org", task)


def test_parse_option_name_value_pairs__no_option_value_old_syntax():
    args = ["task-name", "-o", "old-opt"]
    with pytest.raises(CumulusCIUsageError):
        RunTaskCommand()._parse_option_name_value_pairs(args)


def test_parse_option_name_value_pairs__no_option_value_new_syntax():
    args = ["task-name", "--option-name"]
    with pytest.raises(CumulusCIUsageError):
        RunTaskCommand()._parse_option_name_value_pairs(args)


def test_has_duplicate_options():
    """Test that we can parse option names correctly"""
    options = [
        ("hotdog", "chicago"),
        ("pizza", "new york"),
    ]
    duplicate = RunTaskCommand()._has_duplicate_options(options)
    assert duplicate is False

    options.append(("hotdog", "Cincinnati"))
    duplicate = RunTaskCommand()._has_duplicate_options(options)
    assert duplicate == "hotdog"


def test_format_help__proj_conf_exists(runtime):
    with patch("cumulusci.cli.cci.click.echo") as echo:
        runtime.universal_config = Mock()
        RunTaskCommand().format_help(Mock(), Mock())
        assert 4 == echo.call_count
        assert 0 == len(runtime.universal_config.method_calls)


def test_format_help__proj_conf_does_not_exist(runtime):
    with patch("cumulusci.cli.cci.click.echo") as echo:
        runtime.universal_config = runtime.project_config
        runtime.project_config = None
        RunTaskCommand().format_help(Mock(), Mock())
        assert 4 == echo.call_count


def test_get_default_command_options():
    opts = RunTaskCommand()._get_default_command_options(is_salesforce_task=False)
    assert len(opts) == 4

    opts = RunTaskCommand()._get_default_command_options(is_salesforce_task=True)
    assert len(opts) == 5
    assert any([o.name == "org" for o in opts])


class SetTrace(Exception):
    pass


class DummyDerivedTask(DummyTask):
    def _run_task(self):
        click.echo(f"<{self.__class__}>\n\tcolor: {self.options['color']}")
