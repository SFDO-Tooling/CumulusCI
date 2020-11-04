"""Tests for the RunTaskCommand class"""

from cumulusci.cli.cci import RunTaskCommand
import click
import pytest
from unittest.mock import Mock, patch

from cumulusci.cli import cci
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.exceptions import CumulusCIUsageError, CumulusCIException
from cumulusci.cli.tests.utils import run_click_command, DummyTask


@pytest.fixture
def runtime():
    runtime = Mock()
    runtime.get_org.return_value = (None, None)
    runtime.project_config = BaseProjectConfig(
        None,
        config={
            "tasks": {
                "dummy-task": {"class_path": "cumulusci.cli.tests.utils.DummyTask"},
                "lots-o-options-task": {
                    "class_path": "cumulusci.cli.tests.utils.MultipleOptionsTask"
                },
                "dummy-derived-task": {
                    "class_path": "cumulusci.cli.tests.test_run_task.DummyDerivedTask"
                },
            }
        },
    )
    return runtime


def test_task_run(runtime):
    DummyTask._run_task = Mock()
    multi_cmd = cci.RunTaskCommand()
    with patch("cumulusci.cli.cci.RUNTIME", runtime):
        cmd = multi_cmd.get_command(Mock(), "dummy-task")
        run_click_command(cmd, "dummy-task", color="blue", runtime=runtime)

    DummyTask._run_task.assert_called_once()


def test_task_run__debug_before(runtime):
    DummyTask._run_task = Mock()
    multi_cmd = cci.RunTaskCommand()

    set_trace = Mock(side_effect=SetTrace)
    with patch("cumulusci.cli.cci.RUNTIME", runtime):
        with patch("pdb.set_trace", set_trace):
            with pytest.raises(SetTrace):
                cmd = multi_cmd.get_command(Mock(), "dummy-task")
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
                cmd = multi_cmd.get_command(Mock(), "dummy-task")
                run_click_command(
                    cmd,
                    "dummy-task",
                    color="blue",
                    debug_before=False,
                    debug_after=True,
                    runtime=runtime,
                )


def test_task_run__list_commands(runtime):
    multi_cmd = cci.RunTaskCommand()
    with patch("cumulusci.cli.cci.RUNTIME", runtime):
        commands = multi_cmd.list_commands(Mock())
    assert commands == ["dummy-derived-task", "dummy-task", "lots-o-options-task"]


def test_task_run__resolve_command(runtime):
    args = ["dummy-task", "-o", "color", "blue"]
    multi_cmd = cci.RunTaskCommand()
    with patch("cumulusci.cli.cci.RUNTIME", runtime):
        cmd_name, cmd, args = multi_cmd.resolve_command(Mock(), args)

    assert cmd_name == "dummy-task"
    assert isinstance(cmd, click.Command)
    assert args == [
        "--color",
        "blue",
    ]


def test_convert_old_option_syntax__nothing_to_convert():
    args = ["test-task", "run", "util_sleep", "--seconds", "3.88"]
    converted = RunTaskCommand()._convert_old_option_syntax(args)
    assert args == converted


def test_convert_old_option_syntax__convert_single_option(runtime):
    args = ["dummy-task", "-o", "color", "blue"]
    with patch("cumulusci.cli.cci.RUNTIME", runtime):
        converted = RunTaskCommand()._convert_old_option_syntax(args)
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
    with patch("cumulusci.cli.cci.RUNTIME", runtime):
        converted = RunTaskCommand()._convert_old_option_syntax(args)
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
    with patch("cumulusci.cli.cci.RUNTIME", runtime):
        converted = RunTaskCommand()._convert_old_option_syntax(args)
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
    with patch("cumulusci.cli.cci.RUNTIME", runtime):
        with pytest.raises(CumulusCIUsageError):
            RunTaskCommand()._convert_old_option_syntax(args)


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

    # test option value fails
    with patch("cumulusci.cli.cci.RUNTIME", runtime):
        with pytest.raises(CumulusCIUsageError):
            RunTaskCommand()._convert_old_option_syntax(args)

    args[2] = "-foo"
    # test option name fails
    with patch("cumulusci.cli.cci.RUNTIME", runtime):
        with pytest.raises(CumulusCIUsageError):
            RunTaskCommand()._convert_old_option_syntax(args)


def test_convert_old_option_syntax__option_not_found(runtime):
    args = [
        "lots-o-options-task",
        "-o",
        "pizza",
        "olives",
    ]

    # test option value fails
    with patch("cumulusci.cli.cci.RUNTIME", runtime):
        with pytest.raises(CumulusCIUsageError):
            RunTaskCommand()._convert_old_option_syntax(args)


def test_option_in_task__true(runtime):
    with patch("cumulusci.cli.cci.RUNTIME", runtime):
        assert RunTaskCommand()._option_in_task("color", "dummy-task")


def test_option_in_task__false(runtime):
    with patch("cumulusci.cli.cci.RUNTIME", runtime):
        assert not RunTaskCommand()._option_in_task("pizza", "dummy-task")


def test_option_in_task__option_in_base_class(runtime):
    with patch("cumulusci.cli.cci.RUNTIME", runtime):
        assert RunTaskCommand()._option_in_task("color", "dummy-derived-task")


def test_get_task_options_in_hierarchy__task_options_not_present_on_base(runtime):
    task_class = Mock(__bases__=["one", "two"])
    with pytest.raises(CumulusCIException):
        RunTaskCommand()._get_task_options_in_hierarchy(task_class)


def test_get_task_options_in_hierarchy__options_found(runtime):
    class_w_opts = Mock(task_options={"color": "blue"})
    task_class = Mock(__bases__=["one", class_w_opts])

    options = RunTaskCommand()._get_task_options_in_hierarchy(task_class)
    assert options == ["color"]


def test_parse_option_names():
    """Test that we can parse option names correctly"""
    args = [
        "-o",
        "name1",
        "value1",
        "--name2",
        "value2",
        "--name3",
        "value3",
        "-o",
        "name4",
        "value4",
    ]
    opt_names = RunTaskCommand()._parse_option_names(args)
    assert opt_names == ["name1", "name2", "name3", "name4"]


def test_has_duplicate_options__duplicate_old_syntax():
    args = [
        "-o",
        "dupe",
        "dupe1",
        "-o",
        "name2",
        "value2",
        "--name3",
        "value3",
        "-o",
        "dupe",
        "dupe2",
    ]
    duplicate = RunTaskCommand()._has_duplicate_options(args)
    assert duplicate == "dupe"


def test_has_duplicate_options__duplicate_new_syntax():
    args = [
        "-o",
        "pizza",
        "olives",
        "--dupe",
        "value2",
        "--dupe",
        "value3",
        "-o",
        "salad",
        "ceasar",
    ]
    duplicate = RunTaskCommand()._has_duplicate_options(args)
    assert duplicate == "dupe"


def test_has_duplicate_options__duplicate_mixed_syntax():
    args = [
        "-o",
        "pizza",
        "olives",
        "--hotdog",
        "Chicago",
        "--drink",
        "water",
        "-o",
        "hotdog",
        "Cincinnati",
    ]
    duplicate = RunTaskCommand()._has_duplicate_options(args)
    assert duplicate == "hotdog"


def test_format_help__proj_conf_exists(runtime):
    with patch("cumulusci.cli.cci.click.echo") as echo:
        with patch("cumulusci.cli.cci.RUNTIME", runtime) as rt:
            RunTaskCommand().format_help(Mock(), Mock())
            assert 4 == echo.call_count
            assert 0 == len(rt.universal_config.method_calls)


def test_format_help__proj_conf_does_not_exist(runtime):
    with patch("cumulusci.cli.cci.click.echo") as echo:
        with patch("cumulusci.cli.cci.RUNTIME", runtime) as rt:
            rt.universal_config = rt.project_config
            rt.project_config = None
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


class DummyBaseNoOpts:
    pass


class DummyDerivedNoOpts(DummyBaseNoOpts):
    pass
