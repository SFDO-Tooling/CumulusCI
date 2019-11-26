#!/usr/bin/env python3
import sys
from pathlib import Path

import yaml
import click

from cumulusci.tasks.bulkdata.data_generation.data_generator import generate
from cumulusci.tasks.bulkdata.data_generation.data_gen_exceptions import DataGenError
from cumulusci.tasks.bulkdata.data_generation.output_streams import (
    DebugOutputStream,
    SqlOutputStream,
    JSONOutputStream,
    CSVOutputStream,
    ImageOutputStream,
    MultiplexOutputStream,
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
@click.option("--count", default=1, help="How many times to instantiate the template")
@click.option(
    "--dburl",
    type=str,
    help="URL for database to save data to. "
    "Use sqlite:///foo.db if you don't have one set up.",
)
@click.option(
    "--output-format",
    "output_format",
    type=click.Choice(
        ["JSON", "json", "PNG", "png", "SVG", "svg", "svgz", "jpeg", "jpg", "ps", "dot"]
    ),
)
@click.option(
    "--output-file", "-o", "output_file", type=click.File("w+"), multiple=True
)
@click.option(
    "--option",
    nargs=2,
    type=eval_arg,
    multiple=True,
    help="Options to send to the generator YAML.",
)
@click.option(
    "--debug-internals/--no-debug-internals", "debug_internals", default=False
)
@click.option("--cci-mapping-file", "mapping_file", type=click.Path(exists=True))
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
    output_file=None,
):
    """
    Generates records from a YAML file

\b
    Records can go to:
        * stdout (default)
        * JSON file (--output_format=json --output-file=foo.json)
        * diagram file (--output_format=png --output-file=foo.png)
        * a database identified by --dburl (e.g. --dburl sqlite:////tmp/foo.db)
        * or to a directory as a set of CSV files (--dburl csvfile:///directory/)

    Diagram output depends on the installation of pygraphviz ("pip install pygraphviz")
    """
    if dburl and output_format:
        raise click.ClickException(
            "Sorry, you need to pick --dburl or --output-format "
            "because they are mutually exclusive."
        )
    if dburl and output_file:
        raise click.ClickException(
            "Sorry, you need to pick --dburl or --output-file "
            "because they are mutually exclusive."
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
        output_stream = JSONOutputStream(output_file[0] if output_file else sys.stdout)
    elif output_format:
        if not output_file:
            raise click.ClickException("--output-format specified but no --output-file")
        output_stream = ImageOutputStream(output_file)
    elif output_file:
        outputstreams = []
        for file in output_file:
            format = Path(file.name).suffix[1:]
            if format == "json":
                outputstreams.append(JSONOutputStream(file))
            elif not format:
                outputstreams.append(DebugOutputStream())
            else:
                outputstreams.append(ImageOutputStream(file, format))
        output_stream = MultiplexOutputStream(outputstreams)
    else:
        output_stream = DebugOutputStream()
    try:
        summary = generate(
            click.open_file(yaml_file), count, dict(option), output_stream
        )
        output_stream.close()
        if debug_internals:
            debuginfo = yaml.dump(summary.summarize_for_debugging(), sort_keys=False)
            sys.stdout.write(debuginfo)
        if generate_cci_mapping_file:
            with click.open_file(generate_cci_mapping_file, "w") as f:
                yaml.safe_dump(mapping_from_factory_templates(summary), f)
    except DataGenError as e:
        if debug_internals:
            raise e
        else:
            click.echo("")
            click.echo(
                "An error occurred. If you would like to see a Python traceback, use the --debug-internals option."
            )
            raise click.ClickException(str(e)) from e


if __name__ == "__main__":  # pragma: no cover
    generate_cli()
