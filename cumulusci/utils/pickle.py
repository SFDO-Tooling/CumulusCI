"""Tools for safely saving and loading pickles using an AllowedList"""

import io
import pickle
import typing as T
import warnings


class Type_Cannot_Be_Used_With_Random_Reference(T.NamedTuple):
    """This type cannot be unpickled."""

    module: str
    name: str


_SAFE_CLASSES = {
    ("decimal", "Decimal"),
    ("datetime", "date"),
    ("datetime", "datetime"),
    ("datetime", "timedelta"),
    ("datetime", "timezone"),
}


class RestrictedUnpickler(pickle.Unpickler):
    """Safe unpickler with an allowed-list"""

    count = 0

    def find_class(self, module, name):
        # Only allow safe classes from builtins.
        if (module, name) in _SAFE_CLASSES:
            return super().find_class(module, name)
        else:
            # Return a "safe" object that does nothing.
            if RestrictedUnpickler.count < 10:
                warnings.warn(f"Cannot save and refer to {module}, {name}")
                RestrictedUnpickler.count += 1
            return lambda *args: Type_Cannot_Be_Used_With_Random_Reference(module, name)


def restricted_loads(data):
    """Helper function analogous to pickle.loads()."""
    return RestrictedUnpickler(io.BytesIO(data)).load()
