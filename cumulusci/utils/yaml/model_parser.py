from typing import Union, IO
from pathlib import Path

from pydantic import BaseModel, ValidationError

from cumulusci.utils.yaml.safer_loader import load_from_source, load_yaml_data
from cumulusci.utils.yaml.line_number_annotator import LineNumberAnnotator
from cumulusci.core.exceptions import ConfigValidationError


class CCIModel(BaseModel):
    """Base class for CumulusCI's Pydantic models"""

    _magic_fields = ["fields"]

    @classmethod
    def parse_from_yaml(cls, source: Union[str, Path, IO]):
        """Parse from a path, url, path-like or file-like.py

        Raise an ConfigValidationError on validation error."""
        with load_from_source(source) as (f, path):
            data, linenos = load_yaml_data(f)
            return cls.parse_obj(data, linenos, path).__root__

    @classmethod
    def parse_obj(
        cls, data: [dict, list], linenos: LineNumberAnnotator, path: str = None
    ):
        "Parse a structured dict or list into Model objects"
        assert linenos
        try:
            return super().parse_obj(data)
        except ValidationError as e:
            newerr = linenos.exception_with_line_numbers(e, path)
            raise newerr

    @classmethod
    def validate_data(
        cls,
        data: Union[dict, list],
        linenums: LineNumberAnnotator,
        context: str = None,
        on_error: callable = None,
    ):
        """Validate data which has already been loaded into a dictionary or list.

        context is a string that will be used to give context to error messages.
        on_error will be called for any validation errors with a dictionary in Pydantic error format

        https://pydantic-docs.helpmanual.io/usage/models/#error-handling
        """
        try:
            cls.parse_obj(data, linenums, context)
            return True
        except ConfigValidationError as e:
            if on_error:
                on_error(e)

            return False

    def _alias_for_field(self, name):
        "Find the name that we renamed a field to, to avoid Pydantic name clash"
        for field in self.__fields__.values():
            if field.alias == name:
                return field.name

    @property
    def fields(self):
        "Override deprecated Pydantic behaviour"
        fields_alias = self._alias_for_field("fields")
        if fields_alias:
            return getattr(self, fields_alias)
        else:
            raise AttributeError

    # @property.setter does not work because baseclass.__setattr__
    # takes precedence (shrug emoji)
    def __setattr__(self, name, value):
        "Override deprecated Pydantic behaviour for .fields"
        if name in self._magic_fields:
            name = self._alias_for_field(name)
        return super().__setattr__(name, value)

    def copy(self, *args, **kwargs):
        """Copy with a default behaviour similar to Python's.

        If you supply arguments, you get Pydantic copy behaviour.
        https://pydantic-docs.helpmanual.io/usage/exporting_models/#modelcopy
        """
        if not args and not kwargs:
            return self.__class__(**self.__dict__)
        else:
            return super().copy(self, *args, **kwargs)

    class Config:
        """Pydantic Config

        If you replace this config class in a sub-class, make sure you replace
        the parameter below too.

        https://pydantic-docs.helpmanual.io/usage/model_config/
        """

        extra = "forbid"


class CCIDictModel(CCIModel):
    """A base class that acts as both a model and a dict. For transitioning from
    one to the other."""

    def __getitem__(self, name):
        """Pretend to a do my_dict[name]"""
        try:
            return getattr(self, name)
        except AttributeError:
            raise IndexError(name)

    def __setitem__(self, name, value):
        """Pretend to a do my_dict[name] = X"""
        setattr(self, name, value)

    def __contains__(self, name):
        "Support 'x in my_dict' syntax."
        if name not in self._magic_fields:
            return name in self.__dict__
        else:
            return self._alias_for_field(name) in self.__dict__

    def get(self, name, default=None):
        "Emulate dict.get()."
        if name in self._magic_fields:
            name = self._alias_for_field(name)

        return self.__dict__.get(name, default)

    def __delitem__(self, name):
        if name in self._magic_fields:
            name = self._alias_for_field(name)
        del self.__dict__[name]
