import yaml
from numbers import Number
from functools import partial

from DataGenerator import SObjectFactory, FieldFactory, SimpleValue, ChildRecordValue
from cumulusci.core.template_utils import format_str
from template_funcs import template_funcs


def parse_field_value(field):
    assert field
    if isinstance(field, str):
        return SimpleValue(field)
    elif isinstance(field, Number):
        return SimpleValue(field)
    elif isinstance(field, dict):
        return ChildRecordValue(parse_sobject_definition(field))
    else:
        assert False, "Unknown field type"


def parse_field(name, definition):
    assert name, name
    assert definition, f"Field should have a definition: {name}"
    return FieldFactory(name, parse_field_value(definition))


def parse_fields(fields):
    return [parse_field(name, definition) for name, definition in fields.items()]


def parse_friends(friends):
    return parse_sobject_list(friends)


def evaluate(value):
    funcs = {name: partial(func, None) for name, func in template_funcs.items()}

    if isinstance(value, str) and "{" in value:
        return format_str(value, **funcs)
    else:
        return value


def parse_sobject_definition(sobject):
    assert sobject
    sobj = {}
    sobj["sftype"] = sobject["type"]
    sobj["fields"] = parse_fields(sobject.get("fields", {}))
    sobj["friends"] = parse_friends(sobject.get("friends", []))
    sobj["nickname"] = sobject.get("nickname")
    sobj["count"] = int(float(evaluate(sobject.get("count", 1))))
    return SObjectFactory(**sobj)


def parse_sobject_list(sobjects):
    parsed_sobject_definitions = []
    for obj in sobjects:
        assert obj["object"]
        sobject = obj["object"]
        sobject_factory = parse_sobject_definition(sobject)
        parsed_sobject_definitions.append(sobject_factory)
    return parsed_sobject_definitions


def parse_generator(filename, copies):
    data = yaml.safe_load(open(filename, "r"))
    assert isinstance(data, list)
    return parse_sobject_list(data)
