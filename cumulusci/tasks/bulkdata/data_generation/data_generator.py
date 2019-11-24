import warnings

from cumulusci.tasks.bulkdata.data_generation.data_gen_exceptions import (
    DataGenNameError,
)
from cumulusci.tasks.bulkdata.data_generation.output_streams import DebugOutputStream
from cumulusci.tasks.bulkdata.data_generation.parse_factory_yaml import parse_generator
from cumulusci.tasks.bulkdata.data_generation.data_generator_runtime import (
    output_batches,
)


### This tool is essentially a three stage interpreter.
#
# 1. Yaml parsing into Python data structures.
# 2. Walking the tree, sorting things into groups like macros, file inclusions,
#    etc., and doing the file inclusions (parse_factory_yaml.parse_generator)
# 2 a) merge options informtion from the parse with options from the
#      environment
# 3. Generating the objects top to bottom (including evaluating Jinja) in
#    data_generator_runtime.output_batches
#
# The function generate at the bottom of this file is the entry point to all
# of it.


class ExecutionSummary:
    """Summarize everything that happened during parsing and evaluating."""

    def __init__(self, parse_results, runtime_results):
        self.tables = parse_results.tables
        self.dom = parse_results.templates
        self.intertable_dependencies = runtime_results.intertable_dependencies

    def summarize_for_debugging(self):
        return self.intertable_dependencies, self.dom


def merge_options(option_definitions, user_options):
    """Merge/compare options specified by end-user to those declared in YAML file.

    Takes options passed in from the command line or a config file and
    compare them to the options declared by the Generator YAML file.

    The options from the Generator YAML should be dictionaries with keys of
    "options" and "default" as described in the user documentation.

    The options from the user should be a dictionary of key/value pairs.

    The output is a pair, options, extra_options. The options are the values
    to be fed into the process after applying defaults.

    extra_options are options that the user specified which do not match
    anything in the YAML generator file. The caller may want to warn the
    user about them or throw an error.
    """
    options = {}
    for option in option_definitions:
        name = option["option"]
        if user_options.get(name):
            options[name] = user_options.get(name)
        elif option.get("default"):
            options[name] = option["default"]
        else:
            raise DataGenNameError(
                f"No definition supplied for option {name}", None, None
            )

    extra_options = set(user_options.keys()) - set(options.keys())
    return options, extra_options


def generate(open_yaml_file, count=1, cli_options=None, output_stream=None):
    """The main entry point to the package for Python applications."""
    cli_options = cli_options or {}

    # Where are we going to put the rows?
    output_stream = output_stream or DebugOutputStream()

    # parse the YAML and any it refers to
    parse_result = parse_generator(open_yaml_file)

    # figure out how it relates to CLI-supplied generation variables
    options, extra_options = merge_options(parse_result.options, cli_options)

    if extra_options:
        warnings.warn(f"Warning: unknown options: {extra_options}")

    output_stream.create_or_validate_tables(parse_result.tables)

    # now do the output
    runtime_context = output_batches(
        output_stream, parse_result.templates, count, options
    )

    return ExecutionSummary(parse_result, runtime_context)


if __name__ == "__main__":
    from cumulusci.tasks.bulkdata.data_generation.data_generator_cli import generate_cli

    generate_cli()
