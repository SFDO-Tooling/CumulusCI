from typing import Union, IO
from pathlib import Path, Sequence
from urllib.request import urlopen

from yaml import safe_load

from pydantic import BaseModel, ValidationError
from pydantic.error_wrappers import ErrorWrapper


class CCIBaseModel(BaseModel):
    def __getitem__(self, name):
        if name != "fields":
            return getattr(self, name)
        else:
            field_rename = self.field_rename()
            if field_rename:
                return getattr(self, field_rename)
            else:
                raise IndexError(name)

    def field_rename(self):
        for field in self.__fields__.values():
            if field.alias == "fields":
                return field.name

    def __setitem__(self, name, value):
        setattr(self, name, value)

    def __contains__(self, name):
        if name != "fields":
            return name in self.__dict__
        else:
            return self.field_rename() in self.__dict__

    def get(self, name, default=None):
        if name != "fields":
            return self.__dict__.get(name, default)
        else:
            field_rename = self.field_rename()
            return self.get(field_rename, default)

    def __delitem__(self, name):
        del self.__dict__[name]

    @classmethod
    def parse_from_yaml(cls, data):
        return parse_from_yaml(cls, data)

    def __getattr__(self, name):
        return getattr(self.__dict__, name)

    class Config:
        extra = "forbid"


MappingBaseModel = CCIBaseModel


def parse_from_yaml(model, source: Union[str, Path, IO]):
    if hasattr(source, "read"):
        data = safe_load(source)
        path = _get_path_from_stream(source)
    elif "://" in source:
        with urlopen(source) as f:
            data = safe_load(f)
    else:
        path = source
        with open(path) as f:
            data = safe_load(f)
    try:
        return model(__root__=data)
    except ValidationError as e:
        _add_filenames(e, path)
        raise e


def _get_path_from_stream(stream):
    stream_name = getattr(stream, "name", None)
    if stream_name:
        path = Path(stream.name).absolute()
    else:
        path = "<stream>"
    return str(path)


# THIS DOESN'T WORK! It doesn't hurt anything but it doesn't add line numbers.
def _add_filenames(e: ValidationError, filename):
    def _recursively_add_filenames(l):
        print("Z", type(l))
        processed = False
        if isinstance(l, Sequence):
            for e in l:
                _recursively_add_filenames(e)
            processed = True
        elif isinstance(l, ValidationError) and l.exc:
            _add_filenames(l.exc)
            processed = True
        elif isinstance(l, ErrorWrapper):
            if isinstance(l._loc, tuple):
                l._loc = (filename, *l._loc)
            else:
                l._loc = (filename, l._loc)

            processed = True
            print("QQQ", l._loc)
        else:
            print("ZZZ", type(l), l)
        assert processed, f"Should have processed by now {l}"

    _recursively_add_filenames(e.raw_errors)
