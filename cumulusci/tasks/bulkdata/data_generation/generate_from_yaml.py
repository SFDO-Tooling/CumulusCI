import click
import yaml

# TODO: choose a module naming style
from cumulusci.tasks.bulkdata.data_generation.parse_factory_yaml import parse_generator
from cumulusci.tasks.bulkdata.data_generation.data_generator import output_batches
from cumulusci.tasks.bulkdata.data_generation.output_streams import (
    DebugOutputEngine,
    SqlOutputEngine,
)


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
@click.option("--var", nargs=2, type=(str, eval_arg), multiple=True)
def generate(yaml_file, count, var, dburl, mapping_file):
    if dburl:
        assert mapping_file, "Mapping file must be supplied."
        with open(mapping_file, "r") as f:
            mappings = yaml.safe_load(f)
        db = SqlOutputEngine(dburl, mappings)
    else:
        db = DebugOutputEngine()
    variable_definitions, definitions = parse_generator(yaml_file, int(count))
    cli_variables = dict(var)
    variables = {}
    for variable in variable_definitions:
        name = variable["variable"]
        if cli_variables.get(name):
            variables[name] = cli_variables.get(name)
        elif variable["default"]:
            variables[name] = variable["default"]
        else:
            click.echo(f"No definition supplied for variable {name}", err=True)
            click.exit()

    extra_variables = set(cli_variables.keys()) - set(variables.keys())

    if extra_variables:
        click.echo(f"Warning: unknown variables: {extra_variables}")

    output_batches(db, definitions, count, variables)


if __name__ == "__main__":
    generate()
