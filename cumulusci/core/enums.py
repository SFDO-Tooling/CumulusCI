import enum


class StrEnum(str, enum.Enum):
    """Shim to preserve pre-Python 3.11 behavior
    for the string values of enum members.

    This can be replaced by enum.StrEnum when 3.11
    is the oldest supported version."""

    __str__ = str.__str__  # type: ignore
