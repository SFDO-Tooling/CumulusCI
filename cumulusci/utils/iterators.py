import itertools
import typing


def iterate_in_chunks(n: int, iterable: typing.Iterable):
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, n))
        if not chunk:
            return
        yield chunk
