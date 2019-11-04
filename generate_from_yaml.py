import click
import yaml

# TODO: choose a module naming style
from parse_factory_yaml import parse_generator
from DataGenerator import output_batches
from output_streams import DebugOutputEngine, SqlOutputEngine


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
    definitions = parse_generator(yaml_file, int(count))
    variables = dict(var)
    output_batches(db, definitions, count, variables)


if __name__ == "__main__":
    generate()
