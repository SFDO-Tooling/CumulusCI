import warnings

from .data_gen_exceptions import DataGenNameError
from .output_streams import DebugOutputStream
from .parse_factory_yaml import parse_generator
from .data_generator_runtime import output_batches


### This tool is essentially a three stage interpreter.
#
# 1. Yaml parsing into Python data structures.
# 2. Walking the tree, sorting things into groups like macros, file inclusions,
#    etc., and doing the file inclusions (parse_factory_yaml.parse_generator)
# 2 a) merge options informtion from the parse with options from the
#      environment
# 3. Generating the objects top to bottom (including evaluating Jinja) in
#    generate_from_yaml.output_batches
#
# The function generate at the bottom of this file is the entry point to all
# of it.


class ExecutionSummary:
    def __init__(self, parse_results, runtime_results):
        self.tables = parse_results.tables
        self.intertable_dependencies = runtime_results.intertable_dependencies


def merge_options(option_definitions, user_options):
    options = {}
    for option in option_definitions:
        name = option["option"]
        if user_options.get(name):
            options[name] = user_options.get(name)
        elif option["default"]:
            options[name] = option["default"]
        else:
            raise DataGenNameError(f"No definition supplied for option {name}")

    extra_options = set(user_options.keys()) - set(options.keys())
    return options, extra_options


def generate(open_yaml_file, count, cli_options, output_stream, mapping_file):
    # Where are we going to put the rows?
    output_stream = output_stream or DebugOutputStream()

    # parse the YAML and any it refers to
    parse_result = parse_generator(open_yaml_file)

    # figure out how it relates to CLI options
    options, extra_options = merge_options(parse_result.options, cli_options)

    if extra_options:
        warnings.warn(f"Warning: unknown options: {extra_options}")

    output_stream.create_or_validate_tables(parse_result.tables)

    # now do the output
    runtime_context = output_batches(
        output_stream, parse_result.templates, count, options
    )

    return ExecutionSummary(parse_result, runtime_context)
