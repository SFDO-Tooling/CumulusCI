from sys import stdout

import yaml
import click

from .data_generator import generate
from .data_gen_exceptions import DataGenError
from .output_streams import DebugOutputStream, SqlOutputStream
from .generate_mapping_from_factory import mapping_from_factory_templates


def eval_arg(arg):
    if arg.isnumeric():
        return int(float(arg))
    else:
        return arg


@click.command()
@click.argument("yaml_file", type=click.Path(exists=True))
@click.option("--count", default=1)
@click.option("--output-format", type=str)
@click.option("--dburl", type=str)
@click.option("--mapping_file", type=click.Path(exists=True))
@click.option("--option", nargs=2, type=(str, eval_arg), multiple=True)
@click.option(
    "--debug-internals/--no-debug-internals", "debug_internals", default=False
)
@click.option("--generate_cci_mapping_file", type=click.Path(exists=False))
def generate_cli(
    yaml_file,
    count,
    option,
    dburl=None,
    mapping_file=None,
    debug_internals=False,
    generate_cci_mapping_file=None,
):
    """Fooo"""
    if dburl:
        if mapping_file:
            with click.open_file(mapping_file, "r") as f:
                mappings = yaml.safe_load(f)
        else:
            mappings = None
        output_stream = SqlOutputStream.from_url(dburl, mappings)
    else:
        output_stream = DebugOutputStream()
    try:
        summary = generate(
            click.open_file(yaml_file), count, dict(option), output_stream
        )
        if debug_internals:
            debuginfo = yaml.dump(summary.summarize_for_debugging(), sort_keys=False)
            stdout.write(debuginfo)
        if generate_cci_mapping_file:
            with click.open_file(generate_cci_mapping_file, "w") as f:
                yaml.safe_dump(mapping_from_factory_templates(summary), f)
    except DataGenError as e:
        if debug_internals:
            raise e
        else:
            click.echo("")
            click.echo(
                "An error occurred. If you would like to see a Python traceback, use the --verbose option."
            )
            raise click.ClickException(e)


if __name__ == "__main__":
    generate_cli()  # pragma: no cover
