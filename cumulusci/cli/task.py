import json
from pathlib import Path

import click
from rich.console import Console
from rst2ansi import rst2ansi

from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import CumulusCIUsageError
from cumulusci.core.utils import import_global
from cumulusci.utils import doc_task

from .runtime import pass_runtime
from .ui import CliTable
from .utils import group_items


@click.group("task", help="Commands for finding and running tasks for a project")
def task():
    pass


# Commands for group: task


@task.command(name="list", help="List available tasks for the current context")
@click.option("--plain", is_flag=True, help="Print the table using plain ascii.")
@click.option("--json", "print_json", is_flag=True, help="Print a json string")
@pass_runtime(require_project=False)
def task_list(runtime, plain, print_json):
    tasks = runtime.get_available_tasks()
    plain = plain or runtime.universal_config.cli__plain_output

    console = Console()
    if print_json:
        console.print_json(json.dumps(tasks))
        return None

    task_groups = group_items(tasks)
    for group, tasks in task_groups.items():
        data = [["Task", "Description"]]
        data.extend(sorted(tasks))
        table = CliTable(
            data,
            group,
        )
        console.print(table)

    console.print(
        "Use [bold]cci task info <task_name>[/] to get more information about a task."
    )


@task.command(name="doc", help="Exports RST format documentation for all tasks")
@click.option(
    "--project", "project", is_flag=True, help="Include project-specific tasks only"
)
@click.option(
    "--write",
    "write",
    is_flag=True,
    help="If true, write output to a file (./docs/project_tasks.rst or ./docs/cumulusci_tasks.rst)",
)
@pass_runtime(require_project=False)
def task_doc(runtime, project=False, write=False):
    if project and runtime.project_config is None:
        raise click.UsageError(
            "The --project option can only be used inside a project."
        )
    if project:
        full_tasks = runtime.project_config.tasks
        selected_tasks = runtime.project_config.config_project.get("tasks", {})
        file_name = "project_tasks.rst"
        project_name = runtime.project_config.project__name
        title = f"{project_name} Tasks Reference"
    else:
        full_tasks = selected_tasks = runtime.universal_config.tasks
        file_name = "cumulusci_tasks.rst"
        title = "Tasks Reference"

    result = ["=" * len(title), title, "=" * len(title), ""]
    for name, task_config_dict in full_tasks.items():
        if name not in selected_tasks:
            continue
        task_config = TaskConfig(task_config_dict)
        doc = doc_task(name, task_config)
        result += [doc, ""]
    result = "\n".join(result)

    if write:
        Path("docs").mkdir(exist_ok=True)
        (Path("docs") / file_name).write_text(result, encoding="utf-8")
    else:
        click.echo(result)


@task.command(name="info", help="Displays information for a task")
@click.argument("task_name")
@pass_runtime(require_project=False, require_keychain=True)
def task_info(runtime, task_name):
    task_config = (
        runtime.project_config.get_task(task_name)
        if runtime.project_config is not None
        else runtime.universal_config.get_task(task_name)
    )

    doc = doc_task(task_name, task_config).encode()
    click.echo(rst2ansi(doc))


class RunTaskCommand(click.MultiCommand):
    # options that are not task specific
    global_options = {
        "no-prompt": {
            "help": "Disables all prompts. Set for non-interactive mode such as calling from scripts or CI sytems",
            "is_flag": True,
        },
        "debug": {
            "help": "Drops into the Python debugger on an exception",
            "is_flag": True,
        },
        "debug-before": {
            "help": "Drops into the Python debugger right before the task starts",
            "is_flag": True,
        },
        "debug-after": {
            "help": "Drops into the Python debugger at task completion.",
            "is_flag": True,
        },
    }

    def list_commands(self, ctx):
        runtime = ctx.obj
        tasks = runtime.get_available_tasks()
        return sorted([t["name"] for t in tasks])

    def get_command(self, ctx, task_name):
        runtime = ctx.obj
        if runtime.project_config is None:
            raise runtime.project_config_error
        runtime._load_keychain()
        task_config = runtime.project_config.get_task(task_name)

        if "options" not in task_config.config:
            task_config.config["options"] = {}

        task_class = import_global(task_config.class_path)
        task_options = task_class.task_options

        params = self._get_default_command_options(task_class.salesforce_task)
        params.extend(self._get_click_options_for_task(task_options))

        def run_task(*args, **kwargs):
            """Callback function that executes when the command fires."""
            org, org_config = runtime.get_org(
                kwargs.pop("org", None), fail_if_missing=False
            )

            # Merge old-style and new-style command line options
            old_options = kwargs.pop("o", ())
            new_options = {
                k: v for k, v in kwargs.items() if k not in self.global_options
            }
            options = self._collect_task_options(
                new_options, old_options, task_name, task_options
            )

            # Merge options from the command line into options from the task config.
            task_config.config["options"].update(options)

            try:
                task = task_class(
                    task_config.project_config, task_config, org_config=org_config
                )

                if kwargs.get("debug_before", None):
                    import pdb

                    pdb.set_trace()

                task()

                if kwargs.get("debug_after", None):
                    import pdb

                    pdb.set_trace()

            finally:
                runtime.alert(f"Task complete: {task_name}")

        cmd = click.Command(task_name, params=params, callback=run_task)
        cmd.help = task_config.description
        return cmd

    def format_help(self, ctx, formatter):
        """Custom help for `cci task run`"""
        runtime = ctx.obj
        tasks = runtime.get_available_tasks()
        task_groups = group_items(tasks)
        console = Console()
        for group, tasks in task_groups.items():
            data = [["Task", "Description"]]
            data.extend(sorted(tasks))
            table = CliTable(
                data,
                group,
            )
            console.print(table)

        console.print("Usage: cci task run <task_name> [TASK_OPTIONS...]\n")
        console.print("See above for a complete list of available tasks.")
        console.print(
            "Use [bold]cci task info <task_name>[/] to get more information about a task and its options."
        )

    def _collect_task_options(self, new_options, old_options, task_name, task_options):
        """Merge new style --options with old style -o options.

        Raises:
            CumulusCIUsageError: if there is an old option which duplicates a new one,
            or the option doesn't exist for the given task.
        """
        # filter out options with no values
        options = {
            normalize_option_name(k): v for k, v in new_options.items() if v is not None
        }

        for k, v in old_options:
            k = normalize_option_name(k)
            if options.get(k):
                raise CumulusCIUsageError(
                    f"Please make sure to specify options only once. Found duplicate option `{k}`."
                )
            if k not in task_options:
                raise CumulusCIUsageError(
                    f"No option `{k}` found in task {task_name}.\nTo view available task options run: `cci task info {task_name}`"
                )
            options[k] = v
        return options

    def _get_click_options_for_task(self, task_options):
        """
        Given a dict of options in a task, constructs and returns the
        corresponding list of click.Option instances
        """
        click_options = [click.Option(["-o"], nargs=2, multiple=True, hidden=True)]
        for name, properties in task_options.items():
            # NOTE: When task options aren't explicitly given via the command line
            # click complains that there are no values for options. We set required=False
            # to mitigate this error. Task option validation should be performed at the
            # task level via task._validate_options() or Pydantic models.
            decls = set(
                (
                    f"--{name}",
                    f"--{name.replace('_', '-')}",
                )
            )

            click_options.append(
                click.Option(
                    param_decls=tuple(decls),
                    required=False,  # don't enforce option values in Click
                    help=properties.get("description", ""),
                )
            )
        return click_options

    def _get_default_command_options(self, is_salesforce_task):
        click_options = []
        for opt_name, config in self.global_options.items():
            click_options.append(
                click.Option(
                    param_decls=(f"--{opt_name}",),
                    is_flag=config["is_flag"],
                    help=config["help"],
                )
            )

        if is_salesforce_task:
            click_options.append(
                click.Option(
                    param_decls=("--org",),
                    help="Specify the target org. By default, runs against the current default org.",
                )
            )

        return click_options


@task.command(cls=RunTaskCommand, name="run", help="Runs a task")
def task_run():
    pass  # pragma: no cover


def normalize_option_name(k):
    return k.replace("-", "_")
