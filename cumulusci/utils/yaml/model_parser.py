from typing import Union, IO
from pathlib import Path

from yaml import safe_load

from pydantic import BaseModel, ValidationError


class MappingBaseModel(BaseModel):
    def __getitem__(self, name):
        return getattr(self, name)

    def __setitem__(self, name, value):
        setattr(self, name, value)

    def __contains__(self, name):
        return name in self.__dict__

    def __delitem__(self, name):
        del self.__dict__[name]

    @classmethod
    def parse_from_yaml(cls, data):
        return parse_from_yaml(cls, data)

    def __getattr__(self, name):
        return getattr(self.__dict__, name)

    class Config:
        extra = "forbid"


def parse_from_yaml(model, source: Union[str, Path, IO]):
    if hasattr(source, "read"):
        data = safe_load(source)
        path = _get_path_from_stream(source)
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


def _add_filenames(e: ValidationError, filename):
    for lst in e.raw_errors:
        for err in lst:
            err._loc = (filename, *err._loc)
