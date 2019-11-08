import click
import yaml

# TODO: choose a module naming style
from cumulusci.tasks.bulkdata.data_generation.parse_factory_yaml import parse_generator
from cumulusci.tasks.bulkdata.data_generation.data_generator import (
    output_batches,
    DataGenError,
)
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
@click.option("--option", nargs=2, type=(str, eval_arg), multiple=True)
def generate(yaml_file, count, option, dburl, mapping_file):
    try:
        _generate(click.open_file(yaml_file), count, dict(option), dburl, mapping_file)
    except DataGenError as e:
        click.echo("")
        raise click.ClickException(e)


def _generate(open_yaml_file, count, cli_options, dburl, mapping_file):
    if dburl:
        assert mapping_file, "Mapping file must be supplied."
        with click.open_file(mapping_file, "r") as f:
            mappings = yaml.safe_load(f)
        db = SqlOutputEngine(dburl, mappings)
    else:
        db = DebugOutputEngine()
    option_definitions, definitions = parse_generator(open_yaml_file)

    options, extra_options = merge_options(option_definitions, cli_options)

    if extra_options:
        click.echo("")
        click.echo(f"Warning: unknown options: {extra_options}", color="yellow")
        click.echo("")

    output_batches(db, definitions, count, options)


def merge_options(option_definitions, user_options):
    options = {}
    for option in option_definitions:
        name = option["option"]
        if user_options.get(name):
            options[name] = user_options.get(name)
        elif option["default"]:
            options[name] = option["default"]
        else:
            click.echo(f"No definition supplied for option {name}", err=True)
            click.exit()

    extra_options = set(user_options.keys()) - set(options.keys())
    return options, extra_options


if __name__ == "__main__":
    generate()
