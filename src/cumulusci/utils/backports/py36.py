from contextlib import contextmanager

try:
    from contextlib import nullcontext  # Python 3.7+
except ImportError:

    @contextmanager
    def nullcontext(enter_result=None):
        yield enter_result
