from datetime import date, datetime
from pathlib import Path, PosixPath
from typing import NamedTuple


class JSONSerializer(NamedTuple):
    type: type
    to_json: callable
    from_json: callable

    @property
    def name(self):
        return self.type.__name__


# make sure that datetime comes before date
string_serializers = [
    JSONSerializer(
        datetime,
        to_json=lambda x: x.isoformat(),
        from_json=datetime.fromisoformat,
    ),
    JSONSerializer(
        date,
        to_json=lambda x: x.isoformat(),
        from_json=date.fromisoformat,
    ),
    JSONSerializer(
        bytes,
        to_json=lambda x: x.decode("unicode_escape"),
        from_json=lambda x: x.encode("unicode_escape"),
    ),
    JSONSerializer(
        Path,
        to_json=str,
        from_json=Path,
    ),
    JSONSerializer(
        PosixPath,
        to_json=str,
        from_json=PosixPath,
    ),
]


def encode_value(x):
    """Encode a value that JSON does not support natively"""
    for serializer in string_serializers:
        if isinstance(x, serializer.type):
            return {"$type": serializer.name, "$value": serializer.to_json(x)}

    raise TypeError(type(x))  # pragma: no cover


def decode_dict(x: dict):
    """Decode a dict from JSON"""
    assert isinstance(x, dict)
    if "$type" in x:
        return decode_typed_value(x)
    else:
        return x


def decode_nested_dict(x: dict):
    """Decode a dict from JSON"""
    assert isinstance(x, dict)
    for key, value in x.items():
        if "$type" in key:
            x[key] = decode_typed_value(value)
        elif isinstance(value, dict):
            x[key] = decode_nested_dict(value)
        elif isinstance(value, list):
            x[key] = [decode_nested_dict(i) for i in value]
        else:
            x[key] = value
    return x


def decode_typed_value(x: dict):
    """Decode a value that JSON does not support natively"""
    for serializer in string_serializers:
        if x["$type"] == serializer.name:
            return serializer.from_json(x["$value"])

    raise TypeError(f"Unknown $type: {x['$type']}")  # pragma: no cover
