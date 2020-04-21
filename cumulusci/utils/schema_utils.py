from typing import Sequence, Dict, Any
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

    def __bool__(self):
        return False


class Properties(UserDict):
    interned_values = {}

    def __init__(self, properties: Dict, defaults: Dict):
        self.defaults = defaults
        self.non_default_properties = {
            self.shrink(k): self.shrink(v)
            for k, v in properties.items()
            if v != defaults.get(k)
        }

    @classmethod
    def shrink(cls, value):
        if isinstance(value, list):
            value = tuple(value)
        try:
            return cls.interned_values.setdefault(value, value)
        except TypeError:
            return value

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

    @staticmethod
    def from_dict(d, defaults, filters):
        if filters.incl_props:
            relevant_properties = {
                k: v for k, v in d.items() if k in filters.incl_props
            }
        else:
            relevant_properties = d
        return Properties(relevant_properties, defaults)

    def __repr__(self):
        return object.__repr__(self)


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
        return {"name": self.name, **self.properties.to_dict()}

    @staticmethod
    def from_dict(d, filters):
        d = d.copy()
        name = d.pop("name")

        properties = Properties.from_dict(d, filters.field_property_defaults, filters)
        return SObjectField(name, properties)


class SObject(UserDict):
    properties: Properties

    def __init__(self, properties: Properties):
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
            **self.properties.to_dict(),
            "fields": [field.to_dict() for field in self.fields.values()],
        }

    @staticmethod
    def from_dict(d, filters):
        props = d.copy()
        props["fields"] = {
            f["name"]: SObjectField.from_dict(f, filters)
            for f in d["fields"]
            if f["name"] in filters.incl_fields
        }

        properties = Properties.from_dict(
            props, filters.sobject_property_defaults, filters
        )
        return SObject(properties)

    def from_api(sf_api, sobject_name, filters):
        sftype = getattr(sf_api, sobject_name)
        d = dict(sftype.describe())
        return SObject.from_dict(d, filters)


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
            "sobjects": [sobject.to_dict() for sobject in self.sobjects.values()],
            "sobject_property_defaults": self.sobject_property_defaults,
            "field_property_defaults": self.field_property_defaults,
        }

    @staticmethod
    def from_dict(
        d,
        incl_objects: Sequence[str] = (),
        incl_fields: Sequence[str] = (),
        incl_props: Sequence[str] = (),
    ):
        filters = Filters(incl_objects, incl_fields, incl_props)
        objs = {
            obj["name"]: SObject.from_dict(obj, filters)
            for obj in d["sobjects"]
            if obj["name"] in filters.incl_objects
        }
        return Schema(
            objs,
            sobject_property_defaults=filters.sobject_property_defaults,
            field_property_defaults=filters.field_property_defaults,
        )

    @classmethod
    def from_api(
        cls,
        sf,
        incl_objects: Sequence[str] = (),
        incl_fields: Sequence[str] = (),
        incl_props: Sequence[str] = (),
        logger=None,
    ):
        logger = logger or getLogger("DescribeSchema")
        filters = Filters(incl_objects, incl_fields, incl_props)
        sobjects = cls._describe_objects(sf, filters, logger=logger)
        return cls(
            sobjects=sobjects,
            sobject_property_defaults=filters.sobject_property_defaults,
            field_property_defaults=filters.field_property_defaults,
        )

    def _describe_objects(sf, filters, logger):
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

        if filters.incl_objects and filters.incl_objects != set(target_sobjects):
            logger.warning(
                f"Could not find {filters.incl_objects - set(target_sobjects)}"
            )

        sobjects = {}

        progress = progress_logger(len(target_sobjects), 10, logger)
        for sobject in target_sobjects:
            sobjects[sobject] = SObject.from_api(sf, sobject, filters)
            next(progress)
        return sobjects


class Filters:
    def __init__(
        self,
        incl_objects: Sequence[str] = (),
        incl_fields: Sequence[str] = (),
        incl_props: Sequence[str] = (),
    ):
        if incl_props:
            incl_props = list(incl_props) + ["fields", "name"]  # always include fields
        self.incl_objects = set(incl_objects) or IncludeEverything()
        self.incl_fields = set(incl_fields) or IncludeEverything()
        self.incl_props = set(incl_props) or IncludeEverything()

        self.sobject_property_defaults = {
            k: v for k, v in SOBJECT_PROPERTY_DEFAULTS.items() if k in self.incl_props
        }
        self.field_property_defaults = {
            k: v for k, v in FIELD_PROPERTY_DEFAULTS.items() if k in self.incl_props
        }


def progress_logger(target_count, report_when, logger):
    last_report = time()
    counter = 0
    while True:
        yield counter
        counter += 1
        if time() - last_report > report_when:
            last_report = time()
            logger.info(f"Completed {counter}/{target_count}")
