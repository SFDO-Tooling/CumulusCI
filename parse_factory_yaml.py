import yaml
from numbers import Number
from functools import partial

from DataGenerator import SObjectFactory, FieldFactory, SimpleValue, ChildRecordValue
from cumulusci.core.template_utils import format_str
from template_funcs import template_funcs


def parse_field_value(field, macros):
    assert field is not None
    if isinstance(field, str) or isinstance(field, Number):
        return SimpleValue(field)
    elif isinstance(field, dict):
        return ChildRecordValue(parse_sobject_definition(field, macros))
    else:
        assert False, "Unknown field type"


def parse_field(name, definition, macros):
    assert name, name
    assert definition is not None, f"Field should have a definition: {name}"
    return FieldFactory(name, parse_field_value(definition, macros))


def parse_fields(fields, macros):
    return [
        parse_field(name, definition, macros) for name, definition in fields.items()
    ]


def parse_friends(friends, macros):
    return parse_sobject_list(friends, macros)


def evaluate(value):
    funcs = {name: partial(func, None) for name, func in template_funcs.items()}

    if isinstance(value, str) and "{" in value:
        return format_str(value, **funcs)
    else:
        return value


def parse_count_expression(yaml_sobj, sobj_def):
    numeric_expr = yaml_sobj["count"]
    if isinstance(numeric_expr, Number):
        sobj_def["count"] = int(numeric_expr)
    elif isinstance(numeric_expr, str):
        if "<<" in numeric_expr or "=" in numeric_expr:
            sobj_def["count_expr"] = SimpleValue(numeric_expr)
            sobj_def["count"] = None
        else:
            sobj_def["count"] = int(numeric_expr)
    else:
        raise ValueError(
            f"Expected count of {yaml_sobj['type']} to be a number, not {numeric_expr}"
        )


def include_macro(macros, name):
    macro = macros.get(name)
    assert macro, f"Cannot find macro named {name}"
    fields = macro.get("fields")
    assert fields, f"Macro {name} does not have fields "
    return parse_fields(fields, macros)


def parse_inclusions(yaml_sobj, fields, macros):
    inclusions = [x.strip() for x in yaml_sobj.get("include", "").split(",")]
    inclusions = filter(None, inclusions)
    for inclusion in inclusions:
        fields.extend(include_macro(macros, inclusion))


def parse_sobject_definition(yaml_sobj, macros):
    assert yaml_sobj
    sobj_def = {}
    sobj_def["sftype"] = yaml_sobj["object"]
    assert isinstance(sobj_def["sftype"], str), sobj_def["sftype"]
    sobj_def["fields"] = []
    parse_inclusions(yaml_sobj, sobj_def["fields"], macros)
    sobj_def["fields"].extend(parse_fields(yaml_sobj.get("fields", {}), macros))
    sobj_def["friends"] = parse_friends(yaml_sobj.get("friends", []), macros)
    sobj_def["nickname"] = yaml_sobj.get("nickname")

    count_expr = yaml_sobj.get("count")
    if count_expr is not None:
        parse_count_expression(yaml_sobj, sobj_def)

    return SObjectFactory(**sobj_def)


def parse_sobject_list(sobjects, macros):
    parsed_sobject_definitions = []
    for obj in sobjects:
        assert obj["object"]
        sobject_factory = parse_sobject_definition(obj, macros)
        parsed_sobject_definitions.append(sobject_factory)
    return parsed_sobject_definitions


def parse_generator(filename, copies):
    data = yaml.safe_load(open(filename, "r"))
    assert isinstance(data, list)
    macros = {obj["macro"]: obj for obj in data if obj.get("macro")}
    objects = [obj for obj in data if obj.get("object")]
    return parse_sobject_list(objects, macros)
