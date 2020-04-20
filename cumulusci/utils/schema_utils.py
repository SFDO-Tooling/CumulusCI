from typing import Sequence, Dict, Any, NamedTuple, Set, List
from logging import getLogger
from time import time
from collections import UserDict

from cumulusci.utils._describe_defaults import (
    SOBJECT_PROPERTY_DEFAULTS,
    FIELD_PROPERTY_DEFAULTS,
)


# Backport of cached_property
class cached_property(object):
    """
    A property that is only computed once per instance and then replaces itself
    with an ordinary attribute. Deleting the attribute resets the property.
    Source: https://github.com/pydanny/cached-property/blob/master/cached_property.py
    """  # noqa

    def __init__(self, func):
        self.func = func

    def __get__(self, obj, cls):
        if obj is None:
            return self

        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


class IncludeEverything(set):
    def __contains__(self, other):
        return True


class Properties(UserDict):
    def __init__(self, properties: Dict, defaults: Dict):
        self.defaults = defaults
        self.non_default_properties = properties

    @cached_property
    def data(self):
        return {**self.defaults, **self.non_default_properties}

    def __getattr__(self, name):
        try:
            return getattr(self.data, name)
        except AttributeError:
            raise AttributeError(self.__class__.__name__, name)

    def __setitem__(self, name):
        raise TypeError("'Properties' object does not support item assignment")

    def __delitem__(self, name):
        raise TypeError("'Properties' object does not support item assignment")

    def to_dict(self):
        return self.non_default_properties

    def __repr__(self):
        return object.__repr__(self)

    # from_data would be the same as __init__


class SObjectField:
    name: str
    properties: Properties

    def __init__(self, name: str, properties: Properties):
        self.name = name
        self.properties = properties

    def __getattr__(self, attr):
        if attr in self.properties:
            return self.properties[attr]
        else:
            raise AttributeError(self.name, attr)

    def to_dict(self):
        return {"name": self.name, "properties": self.properties.to_dict()}

    @staticmethod
    def from_dict(d, field_property_defaults):
        properties = Properties(d["properties"], field_property_defaults)
        return SObjectField(d["name"], properties)


class SObject(UserDict):
    name: str
    fields: Dict[str, SObjectField]
    properties: Properties

    def __init__(
        self, name: str, fields: Dict[str, SObjectField], properties: Properties
    ):
        self.name = name
        self.fields = fields
        self.properties = properties

    def __getattr__(self, attr):
        if attr in self.properties:
            return self.properties[attr]
        else:
            raise AttributeError(self.__class__.__name__, attr)

    @property
    def data(self):
        return self.fields

    def to_dict(self):
        return {
            "name": self.name,
            "fields": {field.name: field.to_dict() for field in self.fields.values()},
            "properties": self.properties.to_dict(),
        }

    @staticmethod
    def from_dict(d, sobject_property_defaults, field_property_defaults):
        fields = {
            name: SObjectField.from_dict(f, field_property_defaults)
            for name, f in d["fields"].items()
        }
        properties = Properties(d["properties"], sobject_property_defaults)
        return SObject(d["name"], fields, properties)


class Schema(UserDict):
    sobjects: Dict[str, SObject]
    sobject_property_defaults: Dict[str, Any] = None
    field_property_defaults: Dict[str, Any] = None

    def __init__(
        self,
        sobjects: Dict[str, SObject],
        sobject_property_defaults: Dict[str, Any] = None,
        field_property_defaults: Dict[str, Any] = None,
    ):
        self.sobjects = sobjects
        self.sobject_property_defaults = sobject_property_defaults
        self.field_property_defaults = field_property_defaults

    @property
    def data(self):
        return self.sobjects

    def to_dict(self):
        return {
            "sobjects": {
                sobject.name: sobject.to_dict() for sobject in self.sobjects.values()
            },
            "sobject_property_defaults": self.sobject_property_defaults,
            "field_property_defaults": self.field_property_defaults,
        }

    @staticmethod
    def from_dict(d):
        objs = {
            name: SObject.from_dict(
                obj, d["sobject_property_defaults"], d["field_property_defaults"]
            )
            for name, obj in d["sobjects"].items()
        }
        return Schema(
            objs,
            sobject_property_defaults=d["sobject_property_defaults"],
            field_property_defaults=d["field_property_defaults"],
        )

    @staticmethod
    def from_api(
        sf,
        incl_objects: Sequence[str] = (),
        incl_fields: Sequence[str] = (),
        incl_props: Sequence[str] = (),
        logger=None,
    ):
        sobjects = _describe_objects(
            sf,
            incl_objects=incl_objects,
            incl_fields=incl_fields,
            incl_props=incl_props,
            logger=logger,
        )
        return Schema(
            sobjects=sobjects,
            sobject_property_defaults=SOBJECT_PROPERTY_DEFAULTS,
            field_property_defaults=FIELD_PROPERTY_DEFAULTS,
        )


class Filters(NamedTuple):
    incl_objects: Set[str]
    incl_fields: Set[str]
    incl_props: Set[str]


IncludeEverything = IncludeEverything()


def _describe_objects(
    sf,
    incl_objects: Sequence[str] = (),
    incl_fields: Sequence[str] = (),
    incl_props: Sequence[str] = (),
    logger=None,
):
    logger = logger or getLogger("DescribeSchema")
    filters = Filters(
        incl_objects=set(incl_objects) or IncludeEverything,
        incl_fields=set(incl_fields) or IncludeEverything,
        incl_props=set(incl_props) or IncludeEverything,
    )
    sobjects = _describe_objects_uncompressed(sf, filters, logger)

    # don't combine defaulting behaviour and filtering behaviour or else
    # defaults will be swapped in for filtered properties
    field_prop_defaults = {} if incl_props else FIELD_PROPERTY_DEFAULTS
    schema_prop_defaults = {} if incl_props else SOBJECT_PROPERTY_DEFAULTS

    for sobject in sobjects.values():
        _compress_sobject(sobject, field_prop_defaults, schema_prop_defaults)

    return sobjects


def test_time():
    from wsgiref.handlers import format_date_time
    from datetime import datetime
    from time import mktime

    now = datetime.now()
    stamp = mktime(now.timetuple())
    return format_date_time(stamp)  # --> Wed, 22 Oct 2008 10:52:40 GMT


def _describe_objects_uncompressed(sf, filters, logger):
    logger.info("Fetching SObject list")
    # TODO: Attempt to cache using If-Modified-Since-Header
    # Breadcrumb:
    #   https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/intro_rest_conditional_requests.htm
    #   sf.describe(headers={"If-Modified-Since": "Mon, 20 Apr 2020 10:00:16 GMT"})
    #   formattting dates: https://stackoverflow.com/questions/225086/rfc-1123-date-representation-in-python
    #   exception thrown is simple_saleforce.SalesforceGeneralError
    #   Seems to work well
    global_describe = sf.describe()
    logger.info("Fetching detailed SObject descriptions")

    target_sobjects = [
        sobject["name"]
        for sobject in global_describe["sobjects"]
        if sobject["name"] in filters.incl_objects
    ]

    if list(filters.incl_objects) and filters.incl_objects != set(target_sobjects):
        logger.warning(f"Could not find {filters.incl_objects - set(target_sobjects)}")

    sobjects = {}

    progress = progress_logger(len(target_sobjects), 10, logger)
    for sobject in target_sobjects:
        sobjects[sobject] = _describe_object(sf, sobject, filters)
        next(progress)
    return sobjects


def progress_logger(target_count, report_when, logger):
    last_report = time()
    counter = 0
    while True:
        yield counter
        counter += 1
        if time() - last_report > report_when:
            last_report = time()
            logger.info(f"Completed {counter}/{target_count}")


def _describe_object(sf_api, sobject_name, filters):
    path = f"sobjects/{sobject_name}/describe"
    props = dict(sf_api.restful(method="GET", path=path))
    fields = props["fields"]
    del props["fields"]
    fields = _describe_fields(fields, filters)
    props = _filter_props(props, filters.incl_props)
    properties = Properties(props, {})  # defaults will be added later
    return SObject(name=sobject_name, fields=fields, properties=properties)


def _describe_fields(fields: List[Dict], filters: Filters):
    return {
        field["name"]: SObjectField(
            name=field["name"],
            properties=Properties(_filter_props(field, filters.incl_props), {}),
        )
        for field in fields
        if field["name"] in filters.incl_fields
    }


def _filter_props(data, incl_props):
    return {key: value for (key, value) in data.items() if key in incl_props}


def _compress_sobject(sobject: SObject, field_defaults: Dict, sobject_defaults: Dict):
    field_objs = sobject.fields.values()
    for field in field_objs:
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
