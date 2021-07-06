import os
import click
from unittest import mock

from cumulusci.core.tasks import BaseTask


def run_click_command(cmd, *args, **kw):
    """Run a click command with a mock context and injected CCI runtime object."""
    runtime = kw.pop("runtime", mock.Mock())
    with click.Context(command=mock.Mock(), obj=runtime):
        return cmd.callback(*args, **kw)


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
