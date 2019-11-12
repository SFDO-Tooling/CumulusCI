import os

import yaml
import click

from cumulusci.core.utils import process_list_of_pairs_dict_arg

from cumulusci.tasks.bulkdata.data_generation.data_generator import generate
from cumulusci.tasks.bulkdata.data_generation.data_gen_exceptions import DataGenError
from cumulusci.tasks.bulkdata.data_generation.output_streams import (
    DebugOutputStream,
    SqlOutputStream,
)

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.bulkdata.base_generate_data_task import BaseGenerateDataTask


class GenerateFromYaml(BaseGenerateDataTask):
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
            generate(
                open_yaml_file,
                self.num_records,
                self.vars,
                output_stream,
                self.mapping_file,
            )


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
@click.option("--verbose/--no-verbose", default=False)
def generate_from_yaml(yaml_file, count, option, dburl, mapping_file, verbose):
    if dburl:
        raise click.ClickException("Mapping file must be supplied.")
        with click.open_file(mapping_file, "r") as f:
            mappings = yaml.safe_load(f)
        output_stream = SqlOutputStream(dburl, mappings)
    else:
        output_stream = DebugOutputStream()
    try:
        generate(
            click.open_file(yaml_file), count, dict(option), output_stream, mapping_file
        )
    except DataGenError as e:
        if verbose:
            raise e
        else:
            click.echo("")
            raise click.ClickException(e)


if __name__ == "__main__":
    generate_from_yaml()
