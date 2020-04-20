from typing import Sequence, Dict, Any, NamedTuple, Set

from pydantic import BaseModel, Field as PydanticField


from cumulusci.utils._describe_defaults import (
    SOBJECT_PROPERTY_DEFAULTS,
    FIELD_PROPERTY_DEFAULTS,
)


class IncludeEverything(set):
    def __contains__(self, other):
        return True


class Properties(BaseModel):
    data: Dict[str, Any]

    def __init__(self, properties: Dict, defaults: Dict):
        BaseModel.__init__(self, data=properties)
        self.__dict__["defaults"] = defaults

    def __getitem__(self, item):
        if item in self.data:
            return self.data[item]
        else:
            return self.__dict__["defaults"][item]

    def __getattr__(self, name):
        try:
            return getattr(self.data, name)
        except AttributeError:
            raise AttributeError(self.__class__.__name__, name)

    def __contains__(self, name):
        return name in self.data or name in self.__dict__["defaults"]

    def __len__(self):
        return len(self.keys())

    def keys(self):
        return list(set(self.data).union(self.__dict__["defaults"]))

    def dict(self, **kwargs):
        return self.data


class SObjectField(BaseModel):
    name: str
    properties: Properties

    def __getattr__(self, attr):
        if attr in self.properties:
            return self.properties[attr]
        else:
            raise AttributeError(self.name, attr)


class SObject(BaseModel):
    name: str
    fields_: Dict[str, SObjectField] = PydanticField(..., alias="fields")
    properties: Properties

    def __getattr__(self, attr):
        if attr in self.properties:
            return self.properties[attr]
        else:
            raise AttributeError(self.name, attr)

    def _alias_for_field(self, name):
        "Find the name that we renamed a field to, to avoid Pydantic name clash"
        for field in self.__fields__.values():
            if field.alias == name:
                return field.name

    def dict(self, **kwargs):
        return super().dict(**{"by_alias": True, **kwargs})

    @property
    def fields(self):
        "Override deprecated Pydantic behaviour"
        fields_alias = self._alias_for_field("fields")
        if fields_alias:
            return getattr(self, fields_alias)
        else:
            raise AttributeError

    def __getitem__(self, name: str):
        return self.fields_[name]

    def __contains__(self, name):
        print("CONTAINS", name, self.properties.keys())
        return name in self.fields_


# Problem: defaults and filtering probably don't play nicely together


class Schema(BaseModel):
    sobjects: Dict[str, SObject]
    sobject_property_defaults: Dict[str, Any] = None
    field_property_defaults: Dict[str, Any] = None

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.sobjects.values()[item]
        elif isinstance(item, str):
            return self.sobjects[item]
        else:
            raise TypeError(item)


class Filters(NamedTuple):
    incl_objects: Set[str]
    incl_fields: Set[str]
    incl_props: Set[str]


IncludeEverything = IncludeEverything()


def describe_objects(
    sf,
    incl_objects: Sequence[str] = (),
    incl_fields: Sequence[str] = (),
    incl_props: Sequence[str] = (),
):
    filters = Filters(
        incl_objects=set(incl_objects) or IncludeEverything,
        incl_fields=set(incl_fields) or IncludeEverything,
        incl_props=set(incl_props) or IncludeEverything,
    )
    sobjects = _describe_objects_uncompressed(sf, filters)

    # don't combine defaulting behaviour and filtering behaviour or else
    # defaults will be swapped in for filtered properties
    field_prop_defaults = {} if incl_props else FIELD_PROPERTY_DEFAULTS
    schema_prop_defaults = {} if incl_props else SOBJECT_PROPERTY_DEFAULTS

    for sobject in sobjects.values():
        _compress_sobject(sobject, field_prop_defaults, schema_prop_defaults)

    return Schema(
        sobjects=sobjects,
        sobject_property_defaults=SOBJECT_PROPERTY_DEFAULTS,
        field_property_defaults=FIELD_PROPERTY_DEFAULTS,
    )


def _describe_objects_uncompressed(sf, filters):
    global_describe = sf.describe()
    sobjects = {
        sobject["name"]: _describe_object(sf, sobject["name"], filters)
        for sobject in global_describe["sobjects"]
        if sobject["name"] in filters.incl_objects
    }

    return sobjects


def _describe_object(sf_api, sobject_name, filters):
    path = f"sobjects/{sobject_name}/describe"
    props = dict(sf_api.restful(method="GET", path=path))
    fields = props["fields"]
    del props["fields"]
    fields = _describe_fields(fields, filters)
    props = _filter_props(props, filters.incl_props)
    properties = Properties(props, {})  # defaults will be added later
    return SObject(name=sobject_name, fields=fields, properties=properties)


def _describe_fields(fields, filters):
    return {
        field["name"]: SObjectField(
            name=field["name"],
            properties=Properties(
                _filter_props(field, filters.incl_props), FIELD_PROPERTY_DEFAULTS
            ),
        )
        for field in fields
        if field["name"] in filters.incl_fields
    }


def _filter_props(data, incl_props):
    return {key: value for (key, value) in data.items() if key in incl_props}


def _compress_sobject(sobject, field_defaults, sobject_defaults):
    for field in sobject.fields.values():
        _compress_props(field, field_defaults)
    _compress_props(sobject, sobject_defaults)


def _compress_props(thing, defaults):
    thing.properties = Properties(
        {
            key: value
            for (key, value) in thing.properties.items()
            if defaults.get(key) != value
        },
        defaults,
    )
