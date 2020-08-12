import re
import json
from typing import Tuple
from pathlib import Path

from faker import Faker
from faker.providers import BaseProvider
import yaml

fake = Faker()
ONLY_RELEVANT = True
INCLUDED_STANDARD_SOBJECTS = ["Account", "Contact", "Opportunity"]


class SObjectRelevanceChecker:
    def __init__(self, excluded_sobjects):
        self.excluded_sobjects = excluded_sobjects

    def __contains__(self, name):
        return (
            name in INCLUDED_STANDARD_SOBJECTS
            or name.endswith("__c")
            and not any(
                re.match(exclusion, name) for exclusion in self.excluded_sobjects
            )
        )


IGNORED_FIELDS = [
    ("*", "jigsaw"),
    ("*", "CleanStatus"),
    ("*", "npe01__Contact_Id_for_Role__c"),
]


def with_defaults(field, defaults):
    return {**defaults, **field}


def versioned_file(path):
    path = Path(path)
    index = 1
    new_path = path
    while new_path.exists():
        new_path = Path(f"{path.stem}_{index}{path.suffix}")
        index += 1
    return new_path


def schema2factory(filename, relevant_sobjects, out_macro_yml, out_wrapper_yml):
    with open(filename) as file:
        schema = json.load(file)

    defaults, objects = schema["field_property_defaults"], schema["sobjects"]

    chosen_objects = {
        objname: obj
        for objname, obj in objects.items()
        if objname in relevant_sobjects and ONLY_RELEVANT
    }
    out_macro_versioned = versioned_file(out_macro_yml)
    render_macro_file(chosen_objects, out_macro_versioned, defaults)
    out_wrapper_versioned = versioned_file(out_wrapper_yml)
    render_wrapper_file(chosen_objects, out_wrapper_versioned, out_macro_versioned)


def render_macro_file(objects, out_macro_versioned, defaults):

    objs = [render_macro(obj, defaults, objects) for objname, obj in objects.items()]

    with open(out_macro_versioned, "w") as f:
        yaml.dump(objs, f, sort_keys=False)


def render_wrapper_file(objects, out_wrapper_versioned, out_macro_yml):
    objs = [render_reference(objname) for objname in objects]

    with open(out_wrapper_versioned, "w") as f:
        out = [{"include_file": str(out_macro_yml)}] + objs
        yaml.dump(out, f, sort_keys=False)


def render_reference(objname):
    return {"object": objname, "include": f"incl_{objname}", "fields": {}}


def should_render(obj, field):
    field_name = field["name"]

    return (
        field["createable"]
        and ((not field["defaultedOnCreate"]) or field["name"] == "Name")
        and field_name != "Id"
        and (obj["name"], field_name) not in IGNORED_FIELDS
        and ("*", field_name) not in IGNORED_FIELDS
    )


def render_macro(obj, defaults, objects):
    rc = {}
    rc["macro"] = f"incl_{obj['name']}"
    fields = {
        field_name: with_defaults(field["properties"], defaults)
        for field_name, field in obj["fields"].items()
    }
    rc["fields"] = dict(
        render_field(field_name, field, defaults, objects)
        for field_name, field in fields.items()
        if should_render(obj, field)
    )
    rc["fields"] = {k: v for k, v in rc["fields"].items() if v is not None}
    if not rc["fields"]:
        del rc["fieldss"]
    return rc


def simple_fake(faketype):
    def callback(**args):
        return {"fake": faketype}

    return callback


class KnownType:
    func: callable
    xsd_types: Tuple[str]

    def __init__(self, func, xsd_types):
        self.func = func
        assert isinstance(xsd_types, (str, tuple))
        if isinstance(xsd_types, str):
            xsd_types = (xsd_types,)
        self.xsd_types = xsd_types

    def __bool__(self):
        return bool(self.func)

    def conformsTo(self, other_type):
        return other_type in self.xsd_types


known_types = {
    "phone": KnownType(simple_fake("phone_number"), "string"),
    "state/province": KnownType(simple_fake("state"), "string"),
    "street": KnownType(simple_fake("street_address"), "string"),
    "zip": KnownType(simple_fake("postalcode"), "string"),
    "datetime": KnownType(lambda **args: "<<fake.date>>T<<fake.time>>Z", "datetime"),
    "binary": KnownType(
        lambda length=20, **args: {"fake.text": {"max_nb_chars": min(length, 100)}},
        "binary",
    ),
    "string": KnownType(
        lambda length=20, **args: {"fake.text": {"max_nb_chars": min(length, 100)}}
        if length > 5
        else {
            "fake.pystr": {"min_chars": min(length, 100), "max_chars": min(length, 100)}
        },
        "string",
    ),
    "currency": KnownType(
        lambda **args: {"random_number": {"min": 1, "max": 100000}},
        ("int", "float", "currency"),
    ),
    "date": KnownType(
        lambda **args: {"date_between": {"start_date": "-1y", "end_date": "today"}},
        "date",
    ),
    "Year Started": KnownType(simple_fake("year"), "string"),
    "code": KnownType(simple_fake("postalcode"), "string"),
    "double": KnownType(
        lambda precision=3, scale=0, **args: {
            "random_number": {"min": 1, "max": 10 ** (precision - scale)}
        },
        ("float", "double"),
    ),
    "int": KnownType(
        lambda **args: {"random_number": {"min": 1, "max": 100000}}, ("int")
    ),
    "percent": KnownType(
        lambda **args: {"random_number": {"min": 1, "max": 100}}, ("int")
    ),
    "textarea": KnownType(
        lambda length=20, **args: {"fake.text": {"max_nb_chars": min(length, 100)}},
        ("textarea"),
    ),
    "year": KnownType(simple_fake("year"), ("string", "int")),
    "Installment Frequency": KnownType(
        lambda **args: {"random_number": {"min": 1, "max": 4}}, "int"
    ),
    "latitude": KnownType(simple_fake("latitude"), ("string", "int", "double")),
    "longitude": KnownType(simple_fake("longitude"), ("string", "int", "double")),
    "4": KnownType(
        lambda **args: {"fake.random_number": {"digits": 4, "fix_len": True}}, "string"
    )
    # "Geolocation__Latitude__s": KnownType(
    #     simple_fake("latitude"), ("string", "int", "double")
    # ),
    # "Geolocation__Longitude__s": KnownType(
    #     simple_fake("longitude"), ("string", "int", "double")
    # ),
}


def is_faker_provider_function(func):
    return isinstance(func.__self__, BaseProvider)


def lookup_known_type(name):
    if known_types.get(name):
        return known_types[name]

    faker_func = getattr(fake, name, None)
    if faker_func and is_faker_provider_function(faker_func):
        return KnownType(simple_fake(name), "string")
    return KnownType(None, "")


def render_field(name, field, defaults, objects):
    field_type = field["type"]

    # picklists
    if field_type in ("picklist", "multipicklist"):
        picklistValues = field["picklistValues"]
        if picklistValues:
            values = []
            for value in picklistValues:
                if value["active"]:
                    values.append(value["value"])
            return (name, {"random_choice": values})
        else:
            return (name, "Empty Picklist")

    # known types

    # look for a known type based on the label,
    # which is often more precise than the type
    known_type = lookup_known_type(field["label"])

    # The last word in the label is often indicative as well.
    if not known_type:
        last_word = field["label"].split(" ")[-1]
        type_hint = last_word.lower().strip("()")
        known_type = lookup_known_type(type_hint)

    # try again based on the type's name
    if not known_type or not known_type.conformsTo(field_type):
        known_type = lookup_known_type(field_type)

    if known_type:
        return (name, known_type.func(**field))

    # references
    if field["type"] == "reference":
        targets = field["referenceTo"]
        if not field["nillable"]:
            assert isinstance(targets, list)
            target = targets[0]
            return (
                name,
                {"reference": [render_reference(target)]},
            )
        elif len(targets) == 1:
            return (
                f"__{name}__disabled",
                f"OPTIONAL REFERENCE SKIPPED: {field['referenceTo']}",
            )

        else:
            return (
                f"__{name}__disabled",
                f"OPTIONAL REFERENCE SKIPPED: {field['referenceTo']}",
            )

    return (f"__{name}", f"SKIPPED: UNKNOWN TYPE: {field['type']}")


schema2factory(
    "org_schema.json",
    SObjectRelevanceChecker(
        [
            "npsp__Schedulable__c",
            ".*Trigger_Handler__c",
            ".*Settings.*",
            "npsp__Level__c",
            ".*Error.*",
            "npsp__Batch__c",
            "npsp__Relationship_Sync_Excluded_Fields__c",
            "npsp__DataImport__c",
        ]
    ),
    "generated_macros.yml",
    "generated_file.yml",
)
