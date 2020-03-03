from typing import Union, IO
from pathlib import Path

from yaml import safe_load

from pydantic import BaseModel, ValidationError


class CCIModel(BaseModel):
    """Base class with convenience features"""

    _magic_fields = ["fields"]

    @classmethod
    def parse_from_yaml(cls, data):
        return parse_from_yaml(cls, data)

    def _alias_for_field(self, name):
        "Find the name that we renamed a field to, to avoid Pydantic name clash"
        for field in self.__fields__.values():
            print(field.alias)
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

    class Config:
        """If you replace this config class, make sure you replace
           the parameter below too"""

        extra = "forbid"


class CCIDictModel(CCIModel):
    """A base class that acts as both a model and a dict. For transitioning from
       one to the other."""

    def __getitem__(self, name):
        """Pretend to a do my_dict[name]"""
        if name != "fields":
            return getattr(self, name)
        else:
            _fields_alias = self._alias_for_field(name)
            if _fields_alias:
                return getattr(self, _fields_alias)
            else:
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
        if name not in self._magic_fields:
            return self.__dict__.get(name, default)
        else:
            _fields_alias = self._alias_for_field(name)
            return self.get(_fields_alias, default)

    def __delitem__(self, name):
        del self.__dict__[name]


def parse_from_yaml(model, source: Union[str, Path, IO]):
    if hasattr(source, "read"):
        data = safe_load(source)
        path = _get_path_from_stream(source)
    else:
        path = source
        with open(path) as f:
            data = safe_load(f)
    try:
        return model(__root__=data).__root__
    except ValidationError as e:
        # _add_filenames(e, path)
        raise e


def _get_path_from_stream(stream):
    stream_name = getattr(stream, "name", None)
    if stream_name:
        path = Path(stream.name).absolute()
    else:
        path = "<stream>"
    return str(path)


def _add_filenames(e: ValidationError, filename):
    for lst in e.raw_errors:
        for err in lst:
            err._loc = (filename, *err._loc)
