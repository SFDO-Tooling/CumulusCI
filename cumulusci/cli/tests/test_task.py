import contextlib
import io
import json
from unittest.mock import Mock, patch

import click
import pytest

from cumulusci.cli.runtime import CliRuntime
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.exceptions import CumulusCIUsageError

from .. import task
from .utils import DummyTask, run_click_command

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
    runtime._load_keychain = Mock()

    yield runtime


def test_task_run(runtime):
    DummyTask._run_task = Mock()
    multi_cmd = task.RunTaskCommand()
    with click.Context(multi_cmd, obj=runtime) as ctx:
        cmd = multi_cmd.get_command(ctx, "dummy-task")
        cmd.callback(runtime, "dummy-task", color="blue")

    DummyTask._run_task.assert_called_once()


def test_task_run__extra_yaml_applied(runtime, tmp_path):
    """--extra-yaml resolves via resolve_command before get_task runs."""
    extra = tmp_path / "extra.yml"
    extra.write_text(
        "tasks:\n  dummy-task:\n    description: Overridden from --extra-yaml\n"
    )

    DummyTask._run_task = Mock()
    runtime.reload_project_config = Mock()
    multi_cmd = task.RunTaskCommand()
    with click.Context(multi_cmd, obj=runtime) as ctx:
        multi_cmd.resolve_command(ctx, ["dummy-task", "--extra-yaml", str(extra)])

    runtime.reload_project_config.assert_called_once()
    call_kwargs = runtime.reload_project_config.call_args.kwargs
    assert "Overridden from --extra-yaml" in call_kwargs["additional_yaml"]


def test_task_run__extra_yaml_equals_syntax(runtime, tmp_path):
    """--extra-yaml=<path> form is also accepted."""
    extra = tmp_path / "extra.yml"
    extra.write_text("tasks:\n  dummy-task:\n    description: eq-syntax\n")

    DummyTask._run_task = Mock()
    runtime.reload_project_config = Mock()
    multi_cmd = task.RunTaskCommand()
    with click.Context(multi_cmd, obj=runtime) as ctx:
        multi_cmd.resolve_command(ctx, ["dummy-task", f"--extra-yaml={extra}"])

    runtime.reload_project_config.assert_called_once()
    assert (
        "eq-syntax" in runtime.reload_project_config.call_args.kwargs["additional_yaml"]
    )


def test_task_run__no_extra_yaml_still_calls_reload_with_none(runtime):
    DummyTask._run_task = Mock()
    runtime.reload_project_config = Mock()
    multi_cmd = task.RunTaskCommand()
    with click.Context(multi_cmd, obj=runtime) as ctx:
        multi_cmd.resolve_command(ctx, ["dummy-task"])

    runtime.reload_project_config.assert_called_once_with(additional_yaml=None)


def test_task_run__extra_yaml_missing_path_raises(runtime):
    multi_cmd = task.RunTaskCommand()
    with click.Context(multi_cmd, obj=runtime) as ctx:
        with pytest.raises(CumulusCIUsageError, match="requires a path"):
            multi_cmd.resolve_command(ctx, ["dummy-task", "--extra-yaml"])


def test_task_run__dash_o_overrides_extra_yaml(runtime):
    """``-o taskname__option value`` wins over ``--extra-yaml``.

    Extra YAML merges into the project config at load time; ``-o`` options
    are applied to ``task_config.config["options"]`` at invocation time
    (see ``task.py`` -- after ``reload_project_config``). The final task
    receives the ``-o`` value.

    ``reload_project_config`` is mocked because the fixture builds a fake
    project in-memory; the relevant assertion is that ``-o`` wins over any
    option already present in ``task_config.config['options']`` regardless
    of whether that value came from ``cumulusci.yml`` or from extra YAML.
    """
    # Pretend the extra YAML already set tasks.dummy-task.options.color
    # (the runtime fixture lets us just pre-populate the config).
    runtime.project_config.config["tasks"]["dummy-task"]["options"] = {
        "color": "red-from-extra-yaml",
    }
    runtime.reload_project_config = Mock()

    captured = {}

    def _capture_options(self):
        captured["color"] = self.options["color"]

    DummyTask._run_task = _capture_options
    multi_cmd = task.RunTaskCommand()
    with click.Context(multi_cmd, obj=runtime) as ctx:
        cmd = multi_cmd.get_command(ctx, "dummy-task")
        cmd.callback(
            runtime,
            "dummy-task",
            o=(("color", "blue"),),
            no_prompt=False,
            debug=False,
            debug_before=False,
            debug_after=False,
        )

    assert captured["color"] == "blue"


def test_task_run__no_project(runtime):
    runtime.project_config = None
    runtime.project_config_error = Exception("Broken")
    multi_cmd = task.RunTaskCommand()
    with pytest.raises(Exception, match="Broken"):
        with click.Context(multi_cmd, obj=runtime) as ctx:
            multi_cmd.get_command(ctx, "dummy-task")


def test_task_run__debug_before(runtime):
    DummyTask._run_task = Mock()
    multi_cmd = task.RunTaskCommand()
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
    multi_cmd = task.RunTaskCommand()
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
    multi_cmd = task.RunTaskCommand()
    with click.Context(multi_cmd, obj=runtime) as ctx:
        cmd = multi_cmd.get_command(ctx, "dummy-task")

    assert "This is a dummy task." in cmd.help  # task description


def test_task_run__list_commands(runtime):
    multi_cmd = task.RunTaskCommand()
    with click.Context(multi_cmd, obj=runtime) as ctx:
        commands = multi_cmd.list_commands(ctx)
    assert commands == ["dummy-derived-task", "dummy-task"]


def test_task_run__list_commands_with_extra_yaml_in_args(runtime, tmp_path):
    """--help paths reach list_commands/format_help directly, not through
    resolve_command. --extra-yaml in the arg vector must not break them."""
    extra = tmp_path / "extra.yml"
    extra.write_text("tasks:\n  dummy-task:\n    description: from extra\n")
    multi_cmd = task.RunTaskCommand()
    with click.Context(multi_cmd, obj=runtime) as ctx:
        ctx.args = ["--extra-yaml", str(extra)]
        commands = multi_cmd.list_commands(ctx)
    assert "dummy-task" in commands


def test_format_help(runtime):
    runtime.universal_config = Mock()
    multi_cmd = task.RunTaskCommand()
    with contextlib.redirect_stdout(io.StringIO()) as stdout:
        with click.Context(multi_cmd, obj=runtime) as ctx:
            multi_cmd.format_help(ctx, Mock())

    stdout = stdout.getvalue()
    assert "Usage: cci task run <task_name> [TASK_OPTIONS...]" in stdout
    assert "See above for a complete list of available tasks." in stdout
    assert "Use cci task info <task_name>" in stdout
    assert len(runtime.universal_config.method_calls) == 0


def test_get_default_command_options():
    opts = task.RunTaskCommand()._get_default_command_options(is_salesforce_task=False)
    assert len(opts) == 5

    opts = task.RunTaskCommand()._get_default_command_options(is_salesforce_task=True)
    assert len(opts) == 6
    assert any([o.name == "org" for o in opts])
    assert any([o.name == "extra_yaml" for o in opts])


def test_collect_task_options():
    new_options = {"debug-before": None}
    old_options = (("color", "green"),)

    opts = task.RunTaskCommand()._collect_task_options(
        new_options, old_options, "dummy-task", color_opts["options"]
    )
    assert opts == {"color": "green"}


def test_collect_task_options__duplicate():
    new_options = {"color": "aqua"}
    old_options = (("color", "green"),)

    with pytest.raises(CumulusCIUsageError):
        task.RunTaskCommand()._collect_task_options(
            new_options, old_options, "dummy-task", color_opts["options"]
        )


def test_collect_task_options__not_in_task():
    new_options = {}
    old_options = (("color", "green"),)

    with pytest.raises(CumulusCIUsageError):
        task.RunTaskCommand()._collect_task_options(
            new_options, old_options, "dummy-task", {"not-color": {}}
        )


@patch("cumulusci.cli.task.CliTable")
def test_task_list(cli_tbl):
    runtime = Mock()
    runtime.universal_config.cli__plain_output = None
    runtime.get_available_tasks.return_value = [
        {"name": "test_task", "description": "Test Task", "group": "Test Group"}
    ]

    run_click_command(task.task_list, runtime=runtime, plain=False, print_json=False)

    cli_tbl.assert_called_with(
        [["Task", "Description"], ["test_task", "Test Task"]], "Test Group"
    )


def test_task_list__json(capsys):
    expected_output = {
        "name": "test_task",
        "description": "This can be a really long description that might need a newline if some library is formatting it for ANSI output.",
        "group": "Test Group",
    }
    runtime = Mock()
    runtime.universal_config.cli__plain_output = None
    runtime.get_available_tasks.return_value = [expected_output]

    run_click_command(task.task_list, runtime=runtime, plain=False, print_json=True)

    captured = capsys.readouterr()
    parsed_output = json.loads(captured.out)[0]
    assert parsed_output == expected_output


@patch("cumulusci.cli.task.doc_task", return_value="docs")
def test_task_doc(doc_task):
    runtime = Mock()
    runtime.universal_config.tasks = {"test": {}}
    run_click_command(task.task_doc, runtime=runtime, project=False)
    doc_task.assert_called()


def test_task_doc__project__outside_project():
    runtime = Mock()
    runtime.project_config = None
    with pytest.raises(click.UsageError):
        run_click_command(task.task_doc, runtime=runtime, project=True)


@patch("click.echo")
@patch("cumulusci.cli.task.doc_task", return_value="docs")
def test_task_doc_project(doc_task, echo):
    runtime = Mock()
    runtime.universal_config = {"tasks": {}}
    runtime.project_config = BaseProjectConfig(
        runtime.universal_config,
        {
            "project": {"name": "Test"},
            "tasks": {"task1": {"a": "b"}, "task2": {}},
        },
    )
    runtime.project_config.config_project = {"tasks": {"task1": {"a": "b"}}}
    run_click_command(task.task_doc, runtime=runtime, project=True)
    doc_task.assert_called()
    echo.assert_called()


@patch("cumulusci.cli.task.Path")
@patch("click.echo")
@patch("cumulusci.cli.task.doc_task", return_value="docs")
def test_task_doc_project_write(doc_task, echo, Path):
    runtime = Mock()
    runtime.universal_config.tasks = {"test": {}}
    runtime.project_config = BaseProjectConfig(
        runtime.universal_config,
        {
            "project": {"name": "Test"},
            "tasks": {"option": {"a": "b"}},
        },
    )
    runtime.project_config.config_project = {"tasks": {"option": {"a": "b"}}}
    run_click_command(task.task_doc, runtime=runtime, project=True, write=True)
    doc_task.assert_called()
    echo.assert_not_called()


@patch("cumulusci.cli.task.rst2ansi")
@patch("cumulusci.cli.task.doc_task")
def test_task_info(doc_task, rst2ansi):
    runtime = Mock()
    runtime.project_config.tasks__test = {"options": {}}
    run_click_command(task.task_info, runtime=runtime, task_name="test", extra_yaml=())
    doc_task.assert_called_once()
    rst2ansi.assert_called_once()


@patch("cumulusci.cli.task.rst2ansi")
@patch("cumulusci.cli.task.doc_task")
def test_task_info__extra_yaml_applied(doc_task, rst2ansi, tmp_path):
    extra = tmp_path / "extra.yml"
    extra.write_text(
        "tasks:\n"
        "  injected_task:\n"
        "    description: injected\n"
        "    class_path: cumulusci.tasks.util.Sleep\n"
    )
    runtime = Mock()
    runtime.project_config.tasks__injected_task = {"options": {}}

    run_click_command(
        task.task_info,
        runtime=runtime,
        task_name="injected_task",
        extra_yaml=(str(extra),),
    )

    runtime.reload_project_config.assert_called_once()
    call_kwargs = runtime.reload_project_config.call_args.kwargs
    assert "injected" in call_kwargs["additional_yaml"]


class SetTrace(Exception):
    pass


class DummyDerivedTask(DummyTask):
    def _run_task(self):
        click.echo(f"<{self.__class__}>\n\tcolor: {self.options['color']}")
