import os
from unittest import mock

import click
from click.testing import CliRunner

from cumulusci.cli.cci import cli
from cumulusci.core.tasks import BaseTask


def run_click_command(cmd, *args, **kw):
    """Run a click command with a mock context and injected CCI runtime object."""
    runtime = kw.pop("runtime", mock.Mock())
    with click.Context(command=mock.Mock(), obj=runtime):
        return cmd.callback(*args, **kw)


def run_cli_command(*args, runtime=None, input=None, **kw):
    """Run a click command with arg parsing and injected CCI runtime object."""
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        cli,
        args,
        obj=runtime,
        input=input,
        catch_exceptions=False,
        standalone_mode=False,
    )
    return result


def recursive_list_files(d="."):
    result = []
    for d, subdirs, files in os.walk(d):
        d = d.replace(os.path.sep, "/")
        if d != ".":
            result.append("/".join([d, ""])[2:])
        for f in files:
            result.append("/".join([d, f])[2:])
    result.sort()
    return result


class DummyTask(BaseTask):
    task_docs = "Some task docs."
    task_options = {"color": {"description": "It's a color!", "required": True}}

    def _run_task(self):
        click.echo(f"<{self.__class__}>\n\tcolor: {self.options['color']}")
