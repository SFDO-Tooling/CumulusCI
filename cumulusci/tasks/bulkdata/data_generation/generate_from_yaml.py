import warnings
import os

import yaml
import click

from cumulusci.core.utils import process_list_of_pairs_dict_arg

from cumulusci.tasks.bulkdata.data_generation.parse_factory_yaml import parse_generator
from cumulusci.tasks.bulkdata.data_generation.data_generator import output_batches
from cumulusci.tasks.bulkdata.data_generation.data_gen_exceptions import DataGenError
from cumulusci.tasks.bulkdata.data_generation.output_streams import (
    DebugOutputStream,
    SqlOutputStream,
)

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.bulkdata.base_generate_data_task import BaseGenerateDataTask


class DataGenerator(BaseGenerateDataTask):
    """Generate sample data from a YAML template file."""

    task_docs = """
    """

    task_options = {
        **BaseGenerateDataTask.task_options,
        "generator_yaml": {
            "description": "A generator YAML file to use",
            "required": True,
        },
        "vars": {
            "description": "Pass values to override options in the format VAR1:foo,VAR2:bar"
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.yaml_file = os.path.abspath(self.options["generator_yaml"])
        if not os.path.exists(self.yaml_file):
            raise TaskOptionsError(f"Cannot find {self.yaml_file}")
        if "vars" in self.options:
            self.vars = process_list_of_pairs_dict_arg(self.options["vars"])
        else:
            self.vars = {}

    def generate_data(self, session, engine, base, num_records, current_batch_num):
        output_stream = SqlOutputStream(session, engine, base)
        with open(self.yaml_file) as open_yaml_file:
            _generate(
                open_yaml_file,
                self.num_records,
                self.vars,
                output_stream,
                self.mapping_file,
            )


def merge_options(option_definitions, user_options):
    options = {}
    for option in option_definitions:
        name = option["option"]
        if user_options.get(name):
            options[name] = user_options.get(name)
        elif option["default"]:
            options[name] = option["default"]
        else:
            raise TaskOptionsError(f"No definition supplied for option {name}")

    extra_options = set(user_options.keys()) - set(options.keys())
    return options, extra_options


def _generate(open_yaml_file, count, cli_options, output_stream, mapping_file):
    output_stream = output_stream or DebugOutputStream()
    option_definitions, definitions = parse_generator(open_yaml_file)

    options, extra_options = merge_options(option_definitions, cli_options)

    if extra_options:
        warnings.warn(f"Warning: unknown options: {extra_options}")

    output_batches(output_stream, definitions, count, options)


#########################
#
# The rest of this file allows the tool to be used as a command line.
#
#########################


def eval_arg(arg):
    if arg.isnumeric():
        return int(float(arg))
    else:
        return arg


@click.command()
@click.argument("yaml_file", type=click.Path(exists=True))
@click.option("--count", default=1)
@click.option("--dburl", type=str)
@click.option("--mapping_file", type=click.Path(exists=True))
@click.option("--option", nargs=2, type=(str, eval_arg), multiple=True)
def generate(yaml_file, count, option, dburl, mapping_file):
    if dburl:
        assert mapping_file, "Mapping file must be supplied."
        with click.open_file(mapping_file, "r") as f:
            mappings = yaml.safe_load(f)
        output_stream = SqlOutputStream(dburl, mappings)
    else:
        output_stream = DebugOutputStream()
    try:
        _generate(
            click.open_file(yaml_file), count, dict(option), output_stream, mapping_file
        )
    except DataGenError as e:
        click.echo("")
        raise click.ClickException(e)


if __name__ == "__main__":
    generate()
