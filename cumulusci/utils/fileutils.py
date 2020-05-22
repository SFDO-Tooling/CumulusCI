from typing import IO, ContextManager, Text, Tuple, Union
from contextlib import contextmanager
from pathlib import Path
from io import TextIOWrapper
import requests
from io import StringIO

"""Utilities for working with files"""


def _get_path_from_stream(stream):
    "Try to infer a name from an open stream"
    stream_name = getattr(stream, "name", None)
    if isinstance(stream_name, str):
        path = Path(stream_name).absolute()
    else:
        path = getattr(stream, "url", "<stream>")
    return str(path)


@contextmanager
def load_from_source(
    source: Union[str, IO, Path]
) -> ContextManager[Tuple[Text, IO[Text]]]:
    """Normalize potential data sources into uniform tuple

     Take as input a file-like, path-like, or URL-like
     and convert to an file-file and a string representing
     where it came from. Pass the open file to the loader
     to load the data and then return the result.

    For example:

    >>> from yaml import safe_load
    >>> with load_from_source("cumulusci.yml") as (path, file):
    ...      print(path)
    ...      print(safe_load(file).keys())
    ...
    cumulusci.yml
    dict_keys(['project', 'tasks', 'flows', 'orgs'])

    >>> with load_from_source('http://www.salesforce.com') as (path, file):
    ...     print(path)
    ...     print(file.read(10).strip())
    ...
    http://www.salesforce.com
    <!DOCTYPE

    >>> from urllib.request import urlopen
    >>> with urlopen("https://www.salesforce.com") as f:
    ...     with load_from_source(f) as (path, file):
    ...         print(path)
    ...         print(file.read(10).strip())  #doctest: +ELLIPSIS
    ...
    https://www.salesforce.com/...
    <!DOCTYPE...

    >>> from pathlib import Path
    >>> p = Path(".") / "cumulusci.yml"
    >>> with load_from_source(p) as (path, file):
    ...     print(path)
    ...     print(file.readline().strip())
    ...
    cumulusci.yml
    project:
    """
    if (
        hasattr(source, "read") and hasattr(source, "readable") and source.readable()
    ):  # open file-like
        path = _get_path_from_stream(source)
        if not hasattr(source, "encoding"):  # not decoded yet
            source = TextIOWrapper(source, "utf-8")
        yield path, source
    elif hasattr(source, "open"):  # pathlib.Path-like
        with source.open("rt") as f:
            path = str(source)
            yield path, f
    elif "://" in source:  # URL string-like
        url = source
        resp = requests.get(url)
        resp.raise_for_status()
        yield url, StringIO(resp.text)
    else:  # path-string-like
        path = source
        with open(path, "rt") as f:
            yield path, f


if __name__ == "__main__":  # pragma: no cover
    import doctest

    doctest.testmod(report=True)
