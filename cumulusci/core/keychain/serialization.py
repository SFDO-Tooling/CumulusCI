import json
import os
import pickle
from datetime import date, datetime
from logging import Logger
from typing import NamedTuple, Optional

# Delay saving as JSON for a few CumulusCI releases because
# people might downgrade a release and then their
# CCI can't parse their JSON orgfiles
#
# Thus we roll out the ability to parse JSON configs a bit
# ahead of the write behaviour.
SHOULD_SAVE_AS_JSON = os.environ.get("SHOULD_SAVE_AS_JSON", "False") != "False"


def load_config_from_json_or_pickle(b: bytes) -> dict:
    """Input should be plaintext JSON or Pickle"""
    assert isinstance(b, bytes)

    try:
        data = try_load_config_from_json_or_pickle(b)
    except pickle.PickleError as e:
        # we use ValueError because Pickle and Crypto both do too
        raise ValueError(str(e)) from e

    return data


class JSONSerializer(NamedTuple):
    type: str
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
        from_json=lambda x: datetime.fromisoformat(x),
    ),
    JSONSerializer(
        date, to_json=lambda x: x.isoformat(), from_json=lambda x: date.fromisoformat(x)
    ),
    JSONSerializer(
        bytes,
        to_json=lambda x: x.decode("unicode_escape"),
        from_json=lambda x: x.encode("unicode_escape"),
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


def decode_typed_value(x: dict):
    """Decode a value that JSON does not support natively"""
    for serializer in string_serializers:
        if x["$type"] == serializer.name:
            return serializer.from_json(x["$value"])

    raise TypeError(f"Unknown $type: {x['$type']}")  # pragma: no cover


def try_load_config_from_json_or_pickle(data: bytes) -> dict:
    """Load JSON or Pickle into a dict"""
    try:
        config = json.loads(data.decode("utf-8"), object_hook=decode_dict)
        # remove this debugging tool after transition
        config["serialization_format"] = "json"
        return config
    except ValueError as e1:
        try:
            # first byte in a Pickle must be part of
            # OPCODE Proto == \x80 == 128
            # https://github.com/python/cpython/blob/1b293b60067f6f4a95984d064ce0f6b6d34c1216/Lib/pickletools.py#L2124
            if data[0] != 128:
                raise ValueError("Decryption error")
            config = pickle.loads(data, encoding="bytes")
            # remove this debugging tool after transition
            config["serialization_format"] = "pickle"
            return config
        except pickle.UnpicklingError as e2:
            raise ValueError(f"{e1}\n{e2}")


def report_error(msg: str, e: Exception, logger: Logger):
    logger.error(
        "\n".join(
            (
                msg,
                str(e),
                "Please report it to the CumulusCI team.",
                "For now this is just a warning. By January 2023 it may become a real error.",
                "When you report it to the CumulusCI team, they will investigate",
                "whether the error is in your config or in CumulusCI",
            )
        )
    )


def check_round_trip(data: dict, logger: Logger) -> Optional[bytes]:
    """Return JSON bytes if possible, else None"""
    try:
        as_json_text = json.dumps(data, default=encode_value).encode("utf-8")
    except Exception as e:
        report_error("CumulusCI found an unusual datatype in your config:", e, logger)
        return None
    try:
        test_load = load_config_from_json_or_pickle(as_json_text)
        assert _simplify_config(test_load) == _simplify_config(
            data
        ), f"JSON did not round-trip-cleanly {test_load}, {data}"
    except Exception as e:  # pragma: no cover
        report_error("CumulusCI found a problem saving your config:", e, logger)
        return None
    assert isinstance(as_json_text, bytes)
    return as_json_text


def _simplify_config(config: dict):
    return {k: v for k, v in config.items() if k != "serialization_format"}


def serialize_config_to_json_or_pickle(config: dict, logger: Logger) -> bytes:
    """Serialize a dict to JSON if possible or Pickle otherwise"""
    as_json_text = check_round_trip(config, logger)
    if as_json_text and SHOULD_SAVE_AS_JSON:
        assert isinstance(as_json_text, bytes)
        return as_json_text
    else:
        return pickle.dumps(config, protocol=2)
