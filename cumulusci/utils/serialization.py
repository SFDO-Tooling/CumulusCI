import json
from datetime import date, datetime
from pathlib import Path, PosixPath
from typing import NamedTuple
from pydantic import BaseModel, AnyUrl
from enum import Enum
from cumulusci.utils.version_strings import LooseVersion, StepVersion


class JSONSerializer(NamedTuple):
    type: type
    from_json: callable
    to_key: callable = str
    to_json: callable = str

    @property
    def name(self):
        return self.type.__name__


string_serializers = [
    JSONSerializer(
        datetime,
        to_key=lambda x: x.isoformat(),
        to_json=lambda x: x.isoformat(),
        from_json=datetime.fromisoformat,
    ),
    JSONSerializer(
        date,
        to_key=lambda x: x.isoformat(),
        to_json=lambda x: x.isoformat(),
        from_json=date.fromisoformat,
    ),
    JSONSerializer(
        bytes,
        to_key=lambda x: x.decode("unicode_escape"),
        to_json=lambda x: x.decode("unicode_escape"),
        from_json=lambda x: x.encode("unicode_escape"),
    ),
    JSONSerializer(
        Path,
        from_json=Path,
    ),
    JSONSerializer(
        PosixPath,
        from_json=PosixPath,
    ),
    JSONSerializer(
        BaseModel,
        to_json=lambda x: x.dict(exclude_defaults=True),
        from_json=lambda x: x.__class__.parse_obj(x),
    ),
    JSONSerializer(
        AnyUrl,
        from_json=lambda x: AnyUrl(x),
    ),
    JSONSerializer(
        Enum,
        to_key=lambda x: x.value,
        to_json=lambda x: x.value,
        from_json=lambda x: x,  # This will be handled in decode_typed_value
    ),
    JSONSerializer(
        LooseVersion,
        to_key=lambda x: x.vstring,
        to_json=lambda x: x.vstring,
        from_json=StepVersion,
    ),
    JSONSerializer(
        StepVersion,
        from_json=StepVersion,
    ),
]


def encode_value(
    x,
    to_key: bool = False,
    value_only: bool = False,
):
    """Encode a value that JSON does not support natively"""
    for serializer in string_serializers:
        if isinstance(x, serializer.type):
            if to_key:
                return serializer.to_key(x)
            value = serializer.to_json(x)
            if value_only:
                return value
            return {"$type": serializer.name, "$value": serializer.to_json(x)}
    if isinstance(x, Enum):
        return {
            "$type": "Enum",
            "$value": {"name": x.__class__.__name__, "value": x.value},
        }

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
        if isinstance(value, dict):
            if "$type" in value:
                x[key] = decode_typed_value(value)
            else:
                x[key] = decode_nested_dict(value)
        elif isinstance(value, list):
            x[key] = [
                decode_nested_dict(i) if isinstance(i, dict) else i for i in value
            ]
    return x


def encode_nested(data: dict | list, to_key=False, value_only=False):
    """Encode a dict or list that JSON does not support natively"""
    encoder = CumulusJSONEncoder()
    if isinstance(data, list):
        new_list = []
        for value in data:
            try:
                encoded_value = encode_value(
                    value,
                    to_key=to_key,
                    value_only=value_only,
                )
            except TypeError:
                encoded_value = value
            new_list.append(encoded_value)
        return new_list

    if not isinstance(data, dict):
        return data
    new_dict = {}
    for key, value in data.items():
        new_key = (
            encode_value(
                key,
                to_key=to_key,
                value_only=value_only,
            )
            if key and not isinstance(key, str)
            else key
        )
        try:
            new_value = encode_value(value, to_key=to_key, value_only=value_only)
        except TypeError:
            new_value = value

        new_dict[new_key] = new_value
    return new_dict


def decode_typed_value(x: dict):
    """Decode a value that JSON does not support natively"""
    for serializer in string_serializers:
        if x["$type"] == serializer.name:
            return serializer.from_json(x["$value"])
    if x["$type"] == "Enum":
        enum_class = globals()[x["$value"]["name"]]
        return enum_class(x["$value"]["value"])
    raise TypeError(f"Unknown $type: {x['$type']}")  # pragma: no cover


class CumulusJSONEncoder(json.JSONEncoder):
    def default(self, obj, to_key=False, value_only=False):
        try:
            return encode_value(obj, to_key=to_key, value_only=value_only)
        except TypeError:
            # Let the base class default method raise the TypeError
            return super().default(obj)


def encode_keys(obj):
    if isinstance(obj, list):
        return [encode_keys(i) for i in obj]
    if not isinstance(obj, dict):
        return obj
    new_obj = {}
    for k, v in obj.items():
        key = encode_value(k, to_key=True) if not isinstance(k, str) else k
        new_obj[key] = encode_keys(v)
    return new_obj


def json_dumps(obj, **kwargs):
    obj = encode_keys(obj)
    return json.dumps(obj, cls=CumulusJSONEncoder, **kwargs)


def loads(s, **kwargs):
    return json.loads(s, object_hook=decode_nested_dict, **kwargs)
