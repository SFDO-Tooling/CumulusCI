import click

# TODO: choose a module naming style
from parse_factory_yaml import parse_generator
from output_streams import DebugOutputEngine


@click.command()
@click.argument("yaml_file", type=click.Path(exists=True))
@click.argument("count", default=1)
@click.option("--var", nargs=2, type=(str, str), multiple=True)
def generate(yaml_file, count, var):
    db = DebugOutputEngine()
    definitions = parse_generator(yaml_file, int(count))
    db.output_batches(definitions, count, var)


if __name__ == "__main__":
    generate()
