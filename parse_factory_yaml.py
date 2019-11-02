import yaml
import sys
from numbers import Number
from DataGenerator import (
    SObjectFactory,
    FieldFactory,
    SimpleValue,
    ChildRecordValue,
    DebugOutputEngine,
)


def parse_field_value(field):
    if isinstance(field, str):
        return SimpleValue(field)
    elif isinstance(field, Number):
        return SimpleValue(field)
    else:
        return ChildRecordValue(parse_sobject_definition(field))


def parse_fields(fields):
    return [
        FieldFactory(name, parse_field_value(definition))
        for name, definition in fields.items()
    ]


def parse_friends(friends):
    return [parse_sobject_definition(obj["object"]) for obj in friends]


def parse_sobject_definition(sobject):
    print(sobject)
    sobject_type = sobject["type"]
    sobject_fields = parse_fields(sobject.get("fields", {}))
    sobject_friends = parse_friends(sobject.get("friends", {}))
    return SObjectFactory(sobject_type, fields=sobject_fields, friends=sobject_friends)


def parse_data(filename, copies):
    data = yaml.safe_load(open(filename, "r"))
    assert isinstance(data, list)

    db = DebugOutputEngine()

    for obj in data:
        assert obj["object"]
        sobject = obj["object"]
        sobject_factory = parse_sobject_definition(sobject)
        db.output_batches(sobject_factory, copies)


if __name__ == "__main__":
    _, yamlfile, repetitions = sys.argv
    parse_data(yamlfile, int(repetitions))
