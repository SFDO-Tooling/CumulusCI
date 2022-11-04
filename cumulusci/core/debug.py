from contextlib import contextmanager
from contextvars import ContextVar


class DebugMode(int):
    """A bool-like object that represents the debug mode.

    Over time it will have sub-flags like debug.http_tracing,
    debug.save_intermediate_load_files etc."""

    def __repr__(self):
        return f"<Debug mode: {'enabled' if self else 'disabled'}>"


_DEBUG_MODE = ContextVar("debug_mode", default=DebugMode(False))


def get_debug_mode() -> DebugMode:
    """Get a bool-like object specifying debug state."""
    return _DEBUG_MODE.get()


@contextmanager
def set_debug_mode(enable: bool):
    """Set debug state for the context scoped by this context manager."""
    token = _DEBUG_MODE.set(DebugMode(enable))
    try:
        yield
    finally:
        _DEBUG_MODE.reset(token)


__all__ = ("get_debug_mode", "set_debug_mode")
