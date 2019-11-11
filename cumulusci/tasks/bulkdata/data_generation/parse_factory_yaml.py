import yaml
from yaml.composer import Composer
from yaml.constructor import SafeConstructor
from numbers import Number
from functools import partial
from contextlib import contextmanager

from .data_generator import (
    SObjectFactory,
    FieldFactory,
    SimpleValue,
    ChildRecordValue,
    StructuredValue,
)
from .data_gen_exceptions import DataGenSyntaxError, DataGenNameError
from cumulusci.core.template_utils import format_str
from .template_funcs import template_funcs


SHARED_OBJECT = "#SHARED_OBJECT"


class ParseContext:
    current_sobject = None

    def __init__(self, macros, line_numbers, filename):
        self.macros = macros
        self._line_numbers = line_numbers
        self.filename = filename

    def line_num(self, obj=None):
        if not obj:
            obj = self.current_sobject
            assert obj

        # dicts should have __line__ keys
        try:
            return obj["__line__"]
        except TypeError:
            pass

        # strings (and perhaps some other non-dict objects) should be tracked in
        # the _line_numbers system
        try:
            my_line_num = self._line_numbers.get(id(obj))
            if my_line_num != SHARED_OBJECT:
                return my_line_num
        except KeyError:
            pass

        assert obj != self.current_sobject  # check for no infinite loop
        return self.line_num(self.current_sobject)

    @contextmanager
    def change_current_sobject(self, obj):
        self.current_sobject = obj
        _old_sobject = self.current_sobject
        try:
            yield
        finally:
            self.current_sobject = _old_sobject


def remove_line_numbers(dct):
    return {i: dct[i] for i in dct if i != "__line__"}


def parse_structured_value(name, field, context):
    """Parse something that might look like:

    {'choose': ['Option1', 'Option2', 'Option3', 'Option4'], '__line__': 9}

    or

    {'random_number': {'min': 10, 'max': 20, '__line__': 10} , '__line__': 9}
    """
    top_level = remove_line_numbers(field).items()
    if not top_level:
        raise DataGenSyntaxError(
            f"Strange datastructure ({field})",
            context.filename,
            context.line_num(field),
        )
    elif len(top_level) > 1:
        raise DataGenSyntaxError(
            f"Extra keys for field {name} : {top_level}",
            context.filename,
            context.line_num(field),
        )
    [[function_name, args]] = top_level
    if isinstance(args, dict):
        args = remove_line_numbers(args)

    return StructuredValue(
        function_name, args, context.filename, context.line_num(field)
    )


def parse_field_value(name, field, context):
    assert field is not None
    if isinstance(field, str) or isinstance(field, Number):
        return SimpleValue(
            field, context.filename, context.line_num(field) or context.line_num()
        )
    elif isinstance(field, dict) and field.get("object"):
        return ChildRecordValue(
            parse_sobject_definition(field, context),
            context.filename,
            context.line_num(field),
        )
    elif isinstance(field, dict):
        return parse_structured_value(name, field, context)

    elif isinstance(field, list) and len(field) == 1 and isinstance(field[0], dict):
        # unwrap a list of a single item in this context because it is probably
        # a mistake
        return parse_field_value(name, field[0], context)
    else:
        raise DataGenSyntaxError(
            f"Unknown field type for {name}. Should be a string or 'object': \n {field} ",
            context.filename,
            context.line_num(field) or context.line_num(),
        )


def parse_field(name, definition, context):
    assert name, name
    assert definition is not None, f"Field should have a definition: {name}"
    return FieldFactory(
        name,
        parse_field_value(name, definition, context),
        context.filename,
        context.line_num(definition),
    )


def parse_fields(fields, context):
    if not isinstance(fields, dict):
        raise DataGenSyntaxError(
            "Fields should be a dictionary (should not start with -) ",
            context.filename,
            context.line_num(),
        )
    return [
        parse_field(name, definition, context)
        for name, definition in fields.items()
        if name != "__line__"
    ]


def parse_friends(friends, context):
    return parse_sobject_list(friends, context)


def evaluate(value):
    funcs = {name: partial(func, None) for name, func in template_funcs.items()}

    if isinstance(value, str) and "{" in value:
        return format_str(value, **funcs)
    else:
        return value


def parse_count_expression(yaml_sobj, sobj_def, context):
    numeric_expr = yaml_sobj["count"]
    if isinstance(numeric_expr, Number):
        sobj_def["count"] = int(numeric_expr)
    elif isinstance(numeric_expr, str):
        if "<<" in numeric_expr or "=" in numeric_expr:
            sobj_def["count_expr"] = SimpleValue(
                numeric_expr, context.filename, context.line_num(numeric_expr)
            )
            sobj_def["count"] = None
        else:
            sobj_def["count"] = int(numeric_expr)
    else:
        raise ValueError(
            f"Expected count of {yaml_sobj['type']} to be a number, not {numeric_expr}"
        )


def include_macro(context, name):
    macro = context.macros.get(name)
    if not macro:
        raise DataGenNameError(f"Cannot find macro named {name}")
    fields = macro.get("fields")
    if not fields:
        raise DataGenNameError(f"Macro {name} does not have 'fields'")
    return parse_fields(fields, context)


def parse_inclusions(yaml_sobj, fields, context):
    inclusions = [x.strip() for x in yaml_sobj.get("include", "").split(",")]
    inclusions = filter(None, inclusions)
    for inclusion in inclusions:
        fields.extend(include_macro(context, inclusion))


def parse_sobject_definition(yaml_sobj, context):
    assert yaml_sobj
    with context.change_current_sobject(yaml_sobj):
        sobj_def = {}
        sobj_def["sftype"] = yaml_sobj.get("object")
        assert sobj_def["sftype"], f"Object should have 'object' name {yaml_sobj}"
        assert isinstance(sobj_def["sftype"], str), sobj_def["sftype"]
        sobj_def["fields"] = []
        parse_inclusions(yaml_sobj, sobj_def["fields"], context)
        sobj_def["fields"].extend(parse_fields(yaml_sobj.get("fields", {}), context))
        sobj_def["friends"] = parse_friends(yaml_sobj.get("friends", []), context)
        sobj_def["nickname"] = yaml_sobj.get("nickname")
        sobj_def["line_num"] = context.line_num(yaml_sobj)
        sobj_def["filename"] = context.filename

        count_expr = yaml_sobj.get("count")

        if count_expr is not None:
            parse_count_expression(yaml_sobj, sobj_def, context)

        return SObjectFactory(**sobj_def)


def parse_sobject_list(sobjects, context):
    parsed_sobject_definitions = []
    for obj in sobjects:
        assert obj["object"]
        sobject_factory = parse_sobject_definition(obj, context)
        parsed_sobject_definitions.append(sobject_factory)
    return parsed_sobject_definitions


def yaml_safe_load_with_line_numbers(filestream):
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
        mapping["__line__"] = node.__line__
        return mapping

    def construct_scalar(node):
        scalar = SafeConstructor.construct_scalar(loader, node)
        key = id(scalar)
        if not line_numbers.get(key):
            line_numbers[key] = node.__line__
        else:
            line_numbers[key] = SHARED_OBJECT
        return scalar

    loader.compose_node = compose_node
    loader.construct_mapping = construct_mapping
    loader.construct_scalar = construct_scalar
    return loader.get_single_data(), line_numbers


def parse_generator(stream):
    data, line_numbers = yaml_safe_load_with_line_numbers(stream)
    if not isinstance(data, list):
        raise DataGenSyntaxError(
            "Generator file should be a list (use - on top-level lines)"
        )
    options = [obj for obj in data if obj.get("option")]
    macros = {obj["macro"]: obj for obj in data if obj.get("macro")}
    objects = [obj for obj in data if obj.get("object")]
    context = ParseContext(macros, line_numbers, getattr(stream, "name", "<stream>"))
    return options, parse_sobject_list(objects, context)
