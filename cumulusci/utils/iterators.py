import itertools
import typing as T
from itertools import filterfalse, tee


def iterate_in_chunks(n: int, iterable: T.Iterable) -> T.Iterable[T.Tuple]:
    """Split an iterable into chunks of size 'n'."""
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, n))
        if not chunk:
            return
        yield chunk


# From https://docs.python.org/3/library/itertools.html
def partition(pred, iterable):
    "Use a predicate to partition entries into false entries and true entries"
    # partition(is_odd, range(10)) --> 0 2 4 6 8   and  1 3 5 7 9
    t1, t2 = tee(iterable)
    return filterfalse(pred, t1), filter(pred, t2)
