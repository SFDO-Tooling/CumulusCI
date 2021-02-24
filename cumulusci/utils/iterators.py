import itertools
import typing as T


def iterate_in_chunks(n: int, iterable: T.Iterable) -> T.Iterable[T.Tuple]:
    """Split an iterable into chunks of size 'n'."""
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, n))
        if not chunk:
            return
        yield chunk
