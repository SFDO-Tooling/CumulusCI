from contextlib import contextmanager
from contextvars import ContextVar

_DEBUG_MODE = ContextVar("debug_mode", default=False)


# This may have levels/modes/flags someday
# For now let's discourage anyone from using "DebugMode is True"
class DebugMode:
    """A singleton/proxy that behaves truthy
    when debug mode is not enabled in a context
    and falsy otherwise.

    Debug mode can be set for a context with the
    context manager called `set`."""

    def __bool__(self):
        return _DEBUG_MODE.get()

    @contextmanager
    def set(self, enable: bool):
        token = _DEBUG_MODE.set(enable)
        try:
            yield
        finally:
            _DEBUG_MODE.reset(token)


DebugMode = DebugMode()


__all__ = ("DebugMode",)
