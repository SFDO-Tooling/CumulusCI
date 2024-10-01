import yaml
from cumulusci.utils.serialization import encode_nested, encode_keys


# Custom dumper to use block style (|) for multi-line strings
class LiteralStr(str):
    pass


def str_representer(dumper, data):
    # This will use block style | for multi-line strings
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    else:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)


# Add custom representer to handle LiteralStr
yaml.add_representer(LiteralStr, str_representer)


# Function to recursively apply LiteralStr to all multi-line strings in the dict
def make_multiline_strings_literal(data):
    if isinstance(data, dict):
        return {k: make_multiline_strings_literal(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [make_multiline_strings_literal(v) for v in data]
    elif isinstance(data, str) and "\n" in data:
        return LiteralStr(data)
    else:
        return data


def dump_yaml(
    data,
    stream=None,
    indent: int = 4,
    include_types: bool = True,
):

    import pdb

    pdb.set_trace()
    # Convert data types
    data = encode_keys(data)
    data = encode_nested(data, value_only=not include_types)
    # Apply LiteralStr to multi-line strings before dumping
    data = make_multiline_strings_literal(data)
    return yaml.dump(
        data,
        stream,
        default_flow_style=False,
        sort_keys=False,
        indent=indent,
    )
