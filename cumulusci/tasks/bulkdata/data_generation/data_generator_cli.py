from sys import stdout

import yaml
import click

from cumulusci.tasks.bulkdata.data_generation.data_generator import generate
from cumulusci.tasks.bulkdata.data_generation.data_gen_exceptions import DataGenError
from cumulusci.tasks.bulkdata.data_generation.output_streams import (
    DebugOutputStream,
    SqlOutputStream,
    JSONOutputStream,
    CSVOutputStream,
)
from cumulusci.tasks.bulkdata.data_generation.generate_mapping_from_factory import (
    mapping_from_factory_templates,
)


def eval_arg(arg):
    if arg.isnumeric():
        return int(float(arg))
    else:
        return arg


@click.command()
@click.argument("yaml_file", type=click.Path(exists=True))
@click.option("--count", default=1)
@click.option("--output-format", "output_format", type=click.Choice(["JSON", "json"]))
@click.option("--dburl", type=str)
@click.option("--mapping-file", "mapping_file", type=click.Path(exists=True))
@click.option("--option", nargs=2, type=eval_arg, multiple=True)
@click.option(
    "--debug-internals/--no-debug-internals", "debug_internals", default=False
)
@click.option(
    "--generate-cci-mapping-file",
    "generate_cci_mapping_file",
    type=click.Path(exists=False),
)
def generate_cli(
    yaml_file,
    count=1,
    option=[],
    dburl=None,
    mapping_file=None,
    debug_internals=False,
    generate_cci_mapping_file=None,
    output_format=None,
):
    """
    Generates records from a YAML file

    Records can go to stdout (default), JSON (--output_format=json),
    a database identified by dburl or to a CSV file (--dburl csvfile:///path.../)
    """
    if dburl and output_format:
        raise click.ClickException(
            "Sorry, you need to pick dburl or output_format because they are mutually exclusive."
        )
    if dburl:
        if mapping_file:
            with click.open_file(mapping_file, "r") as f:
                mappings = yaml.safe_load(f)
        else:
            mappings = None
        if dburl.startswith("csvfile:/"):
            output_stream = CSVOutputStream(dburl)
        else:
            output_stream = SqlOutputStream.from_url(dburl, mappings)
    elif mapping_file:
        raise click.ClickException("Mapping file can only be used with --dburl")
    elif output_format and output_format.lower() == "json":
        output_stream = JSONOutputStream(stdout)
    else:
        output_stream = DebugOutputStream()
    try:
        summary = generate(
            click.open_file(yaml_file), count, dict(option), output_stream
        )
        output_stream.close()
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
            raise click.ClickException(str(e)) from e


if __name__ == "__main__":  # pragma: nocover
    generate_cli()
