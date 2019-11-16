from numbers import Number
from datetime import date
from contextlib import contextmanager
from collections import namedtuple
from pathlib import Path

import yaml
from yaml.composer import Composer
from yaml.constructor import SafeConstructor

from .data_generator_runtime import (
    SObjectFactory,
    FieldFactory,
    SimpleValue,
    ChildRecordValue,
    StructuredValue,
)
from .data_gen_exceptions import DataGenSyntaxError, DataGenNameError, DataGenError

SHARED_OBJECT = "#SHARED_OBJECT"

###
#   The entry point to this is parse_generator

LineTracker = namedtuple("LineTracker", ["filename", "line_num"])


class ParseContext:
    current_parent_object = None

    def __init__(self):
        self.macros = {}
        self.line_numbers = {}
        self.options = []

    def line_num(self, obj=None):
        if not obj:
            obj = self.current_parent_object
            assert obj

        # dicts should have __line__ keys
        try:
            return obj["__line__"]._asdict()
        except TypeError:
            pass

        # strings (and perhaps some other non-dict objects) should be tracked in
        # the line_numbers system
        try:
            my_line_num = self.line_numbers.get(id(obj))
            if my_line_num and my_line_num != SHARED_OBJECT:
                return my_line_num._asdict()
        except KeyError:
            pass

        assert obj != self.current_parent_object  # check for no infinite loop
        return self.line_num(self.current_parent_object)

    @contextmanager
    def change_current_parent_object(self, obj):
        _old_sobject = self.current_parent_object
        self.current_parent_object = obj
        try:
            yield
        finally:
            self.current_parent_object = _old_sobject


def removeline_numbers(dct):
    return {i: dct[i] for i in dct if i != "__line__"}


def parse_structured_value_args(args, context):
    """Structured values can be dicts or lists containing simple values or further structure."""
    if isinstance(args, dict):
        with context.change_current_parent_object(args):
            return {
                name: parse_field_value(name, arg, context, False)
                for name, arg in args.items()
                if name != "__line__"
            }
    elif isinstance(args, list):
        return [parse_field_value(i, arg, context, False) for i, arg in enumerate(args)]
    else:
        return parse_field_value("", args, context, False)


def parse_structured_value(name, field, context):
    """Parse something that might look like:

    {'choose': ['Option1', 'Option2', 'Option3', 'Option4'], '__line__': 9}

    or

    {'random_number': {'min': 10, 'max': 20, '__line__': 10} , '__line__': 9}
    """
    top_level = removeline_numbers(field).items()
    if not top_level:
        raise DataGenSyntaxError(
            f"Strange datastructure ({field})", **context.line_num(field)
        )
    elif len(top_level) > 1:
        raise DataGenSyntaxError(
            f"Extra keys for field {name} : {top_level}", **context.line_num(field)
        )
    [[function_name, args]] = top_level
    args = parse_structured_value_args(args, context)
    return StructuredValue(function_name, args, **context.line_num(field))


def parse_field_value(name, field, context, allow_structured_values=True):
    assert field is not None
    if isinstance(field, (str, Number, date)):
        return SimpleValue(field, **(context.line_num(field) or context.line_num()))
    elif isinstance(field, dict) and field.get("object"):
        return ChildRecordValue(
            parse_sobject_definition(field, context), **context.line_num(field)
        )
    elif isinstance(field, dict):
        return parse_structured_value(name, field, context)

    elif isinstance(field, list) and len(field) == 1 and isinstance(field[0], dict):
        # unwrap a list of a single item in this context because it is
        # a mistake and we can infer their real meaning
        return parse_field_value(name, field[0], context)
    else:
        raise DataGenSyntaxError(
            f"Unknown field {type(field)} type for {name}. Should be a string or 'object': \n {field} ",
            **(context.line_num(field) or context.line_num()),
        )


def parse_field(name, definition, context):
    assert name, name
    if definition is None:
        raise DataGenSyntaxError(
            f"Field should have a definition: {name}", **context.line_num(name)
        )
    return FieldFactory(
        name,
        parse_field_value(name, definition, context),
        **context.line_num(definition),
    )


def parse_fields(fields, context):
    with context.change_current_parent_object(fields):
        if not isinstance(fields, dict):
            raise DataGenSyntaxError(
                "Fields should be a dictionary (should not start with -) ",
                **context.line_num(),
            )
        return [
            parse_field(name, definition, context)
            for name, definition in fields.items()
            if name != "__line__"
        ]


def parse_friends(friends, context):
    return parse_sobject_list(friends, context)


def parse_count_expression(yaml_sobj, sobj_def, context):
    numeric_expr = yaml_sobj["count"]
    if isinstance(numeric_expr, Number):
        sobj_def["count"] = int(numeric_expr)
    elif isinstance(numeric_expr, str):
        if "<<" in numeric_expr or "=" in numeric_expr:
            sobj_def["count_expr"] = SimpleValue(
                numeric_expr, **context.line_num(numeric_expr)
            )
            sobj_def["count"] = None
        else:
            sobj_def["count"] = int(numeric_expr)
    else:
        raise ValueError(
            f"Expected count of {yaml_sobj['type']} to be a number, not {numeric_expr}"
        )


def include_macro(name, context):
    macro = context.macros.get(name)
    if not macro:
        raise DataGenNameError(f"Cannot find macro named {name}", **context.line_num())
    parsed_macro = parse_element(macro, "macro", {"fields": dict}, {}, context)
    fields = parsed_macro.fields
    return parse_fields(fields, context)


def parse_inclusions(yaml_sobj, fields, context):
    inclusions = [x.strip() for x in yaml_sobj.get("include", "").split(",")]
    inclusions = filter(None, inclusions)
    for inclusion in inclusions:
        fields.extend(include_macro(inclusion, context))


def parse_sobject_definition(yaml_sobj, context):
    parsed_sobject = parse_element(
        yaml_sobj,
        "object",
        {},
        {
            "fields": dict,
            "friends": list,
            "include": str,
            "nickname": str,
            "count": (str, int),
        },
        context,
    )
    assert yaml_sobj
    with context.change_current_parent_object(yaml_sobj):
        sobj_def = {}
        sobj_def["sftype"] = parsed_sobject.object
        sobj_def["fields"] = fields = []
        parse_inclusions(yaml_sobj, fields, context)
        fields.extend(parse_fields(parsed_sobject.fields or {}, context))
        sobj_def["friends"] = parse_friends(parsed_sobject.friends or [], context)
        sobj_def["nickname"] = parsed_sobject.nickname
        sobj_def["line_num"] = parsed_sobject.line_num.line_num
        sobj_def["filename"] = parsed_sobject.line_num.filename

        count_expr = yaml_sobj.get("count")

        if count_expr is not None:
            parse_count_expression(yaml_sobj, sobj_def, context)

        return SObjectFactory(**sobj_def)


def parse_sobject_list(sobjects, context):
    parsed_sobject_definitions = []
    for obj in sobjects:
        assert isinstance(obj, dict), obj
        assert obj["object"], obj
        sobject_factory = parse_sobject_definition(obj, context)
        parsed_sobject_definitions.append(sobject_factory)
    return parsed_sobject_definitions


def yaml_safe_load_withline_numbers(filestream, filename):
    loader = yaml.SafeLoader(filestream)
    line_numbers = {}

    def compose_node(parent, index):
        # the line number where the previous token has ended (plus empty lines)
        line = loader.line
        node = Composer.compose_node(loader, parent, index)
        node.__line__ = line + 1
        return node

    def construct_mapping(node, deep=False):
        mapping = SafeConstructor.construct_mapping(loader, node, deep=deep)
        mapping["__line__"] = LineTracker(filename, node.__line__)
        return mapping

    def construct_scalar(node):
        scalar = SafeConstructor.construct_scalar(loader, node)
        key = id(scalar)
        if not line_numbers.get(key):
            line_numbers[key] = LineTracker(filename, node.__line__)
        else:
            line_numbers[key] = SHARED_OBJECT
        return scalar

    loader.compose_node = compose_node
    loader.construct_mapping = construct_mapping
    loader.construct_scalar = construct_scalar
    return loader.get_single_data(), line_numbers


class DictValuesAsAttrs:
    pass


def parse_element(dct, element_type, mandatory_keys, optional_keys, context):
    expected_keys = {
        **mandatory_keys,
        **optional_keys,
        "__line__": LineTracker,
        element_type: str,
    }
    rc_obj = DictValuesAsAttrs()
    rc_obj.line_num = dct["__line__"]
    with context.change_current_parent_object(dct):
        for key in dct:
            key_definition = expected_keys.get(key)
            if not key_definition:
                raise DataGenError(f"Unexpected key: {key}", **context.line_num(key))
            else:
                value = dct[key]
                if not isinstance(value, key_definition):
                    raise DataGenError(
                        f"Expected `{key}` to be of type {key_definition} instead of {type(value)}.",
                        **context.line_num(dct),
                    )
                else:
                    setattr(rc_obj, key, value)

        missing_keys = set(mandatory_keys) - set(dct.keys())
        if missing_keys:
            raise DataGenError(
                f"Expected to see `{missing_keys}` in `{element_type}``.",
                **context.line_num(dct),
            )
        defaulted_keys = set(optional_keys) - set(dct.keys())
        for key in defaulted_keys:
            setattr(rc_obj, key, None)

        return rc_obj


def relpath_from_inclusion_element(inclusion, context):
    # should be a two-element dict: {'include_file': 'foo.yml', "__line__": 5}
    inclusion_parsed = parse_element(inclusion, "include_file", {}, {}, context)
    relpath = inclusion_parsed.include_file
    linenum = inclusion_parsed.line_num or LineTracker("unknown", -1)
    assert not relpath.startswith("/")  # only relative paths
    return Path(relpath), linenum


def parse_included_file(parent_path: Path, inclusion, context):
    relpath, linenum = relpath_from_inclusion_element(inclusion, context)
    inclusion_path = parent_path.parent / relpath
    # someday add a check that we don't go outside of the project dir
    if not inclusion_path.exists():
        raise DataGenError(
            f"Cannot load include file {inclusion_path}", **linenum._asdict()
        )
    with inclusion_path.open() as f:
        incl_objects = parse_file(f, context)
        return incl_objects


def parse_included_files(path, data, context):
    file_inclusions = [obj for obj in data if obj.get("include_file")]

    templates = []
    for fi in file_inclusions:
        templates.extend(parse_included_file(path, fi, context))
    return templates


def categorize_top_level_objects(data, context):
    """Look at all of the top-level declarations and categorize them"""
    top_level_collections = {
        "option": [],
        "include_file": [],
        "macro": [],
        "object": [],
    }
    assert isinstance(data, list)
    for obj in data:
        if not isinstance(obj, dict):
            raise DataGenSyntaxError(
                f"Top level elements in a data generation template should all be dictionaries, not {obj}",
                **context.line_num(data),
            )
        parent_collection = None
        for collection in top_level_collections:
            if obj.get(collection):
                if parent_collection:
                    raise DataGenError(
                        f"Top level element seems to match two name patterns: {collection, parent_collection}",
                        **context.line_num(obj),
                    )
                parent_collection = collection
        if parent_collection:
            top_level_collections[parent_collection].append(obj)
        else:
            raise DataGenError(f"Unknown object type {obj}", **context.line_num(obj))
    return top_level_collections


def parse_top_level_elements(path, data, context):
    top_level_objects = categorize_top_level_objects(data, context)
    templates = []
    templates.extend(parse_included_files(path, data, context))
    context.options.extend(top_level_objects["option"])
    context.macros.update({obj["macro"]: obj for obj in top_level_objects["macro"]})
    templates.extend(top_level_objects["object"])
    return templates


def parse_file(stream, context: ParseContext):
    stream_name = getattr(stream, "name", None)
    if stream_name:
        path = Path(stream.name).absolute()
    else:
        path = "<stream>"
    data, line_numbers = yaml_safe_load_withline_numbers(stream, str(path))
    context.line_numbers.update(line_numbers)

    if not isinstance(data, list):
        raise DataGenSyntaxError(
            "Generator file should be a list (use '-' on top-level lines)",
            stream_name,
            1,
        )

    templates = parse_top_level_elements(path, data, context)

    return templates


def parse_generator(stream):
    context = ParseContext()
    objects = parse_file(stream, context)
    return context.options, parse_sobject_list(objects, context)
