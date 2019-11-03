import click
import yaml

# TODO: choose a module naming style
from parse_factory_yaml import parse_generator
from output_streams import DebugOutputEngine, SqlOutputEngine


@click.command()
@click.argument("yaml_file", type=click.Path(exists=True))
@click.option("--count", default=1)
@click.option("--dburl", type=str)
@click.option("--mapping_file", type=click.Path(exists=True))
@click.option("--var", nargs=2, type=(str, str), multiple=True)
def generate(yaml_file, count, var, dburl, mapping_file):
    if dburl:
        assert mapping_file, "Mapping file must be supplied."
        with open(mapping_file, "r") as f:
            mappings = yaml.safe_load(f)
        db = SqlOutputEngine(dburl, mappings)
    else:
        db = DebugOutputEngine()
    definitions = parse_generator(yaml_file, int(count))
    db.output_batches(definitions, count, var)


if __name__ == "__main__":
    generate()
