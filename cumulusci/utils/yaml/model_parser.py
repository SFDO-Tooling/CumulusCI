from typing import Union, IO
from pathlib import Path, Sequence

from yaml import safe_load

from pydantic import BaseModel, ValidationError
from pydantic.error_wrappers import ErrorWrapper

from cumulusci.utils.fileutils import load_from_source


class CCIModel(BaseModel):
    """Base class for CumulusCI's Pydantic models"""

    _magic_fields = ["fields"]

    @classmethod
    def parse_from_yaml(cls, source: Union[str, Path, IO]):
        "Parse from a path, url, path-like or file-like"
        with load_from_source(source) as (path, file):
            data = safe_load(file)
            return cls.parse_obj(data, path).__root__

    @classmethod
    def parse_obj(cls, data: [dict, list], path: str = None):
        "Parse a structured dict or list into Model objects"
        try:
            return super().parse_obj(data)
        except ValidationError as e:
            _add_filenames(e, path)
            raise e

    @classmethod
    def validate_data(
        cls, data: Union[dict, list], context: str = None, on_error: callable = None,
    ):
        """Validate data which has already been loaded into a dictionary or list.

        context is a string that will be used to give context to error messages.
        on_error will be called for any validation errors with a dictionary in Pydantic error format

        https://pydantic-docs.helpmanual.io/usage/models/#error-handling
        """
        try:
            cls.parse_obj(data, context)
            return True
        except ValidationError as e:
            if on_error:
                for error in e.errors():
                    on_error(error)

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


def _add_filenames(e: ValidationError, filename):
    def _recursively_add_filenames(l):
        processed = False
        if isinstance(l, Sequence):
            for e in l:
                _recursively_add_filenames(e)
            processed = True
        elif isinstance(l, ErrorWrapper):
            l._loc = (filename, l._loc)

            processed = True
        assert processed, f"Should have processed by now {l}, {repr(l)}"

    _recursively_add_filenames(e.raw_errors)
