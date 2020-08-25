from typing import IO, ContextManager, Text, Tuple, Union
from contextlib import contextmanager
from pathlib import Path
from io import TextIOWrapper, StringIO
import os

import requests
from fs import open_fs, path as fspath, copy, base
from shutil import rmtree

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


def cleanup_org_cache_dirs(keychain, project_config):
    """Cleanup directories that are not associated with a connected/live org."""
    domains = set()
    for org in keychain.list_orgs():
        org_config = keychain.get_org(org)
        domain = org_config.get_domain()
        if domain:
            domains.add(domain)

    assert project_config.project_cache_dir
    assert keychain.global_config_dir

    project_org_directories = (project_config.project_cache_dir / "orginfo").glob("*")
    global_org_directories = (keychain.global_config_dir / "orginfo").glob("*")

    for directory in list(project_org_directories) + list(global_org_directories):
        if directory.name not in domains:
            rmtree(directory)


def proxy(funcname):
    def func(self, *args, **kwargs):
        real_func = getattr(self.fs, funcname)
        return real_func(self.filename, *args, **kwargs)

    func.__doc__ = getattr(base.FS, funcname).__doc__
    return func


class FSResource:
    """Generalization of pathlib.Path to support S3, FTP, etc"""

    def __init__(
        self, resource_url_or_path: Union[str, Path], filesystem: base.FS = None
    ):
        """Create a new fsresource from a URL or path (absolute or relative)"""

        if isinstance(resource_url_or_path, str) and "://" in resource_url_or_path:
            path_type = "url"
        elif isinstance(resource_url_or_path, FSResource):
            path_type = "resource"
        else:
            resource_url_or_path = Path(resource_url_or_path)
            path_type = "path"

        if filesystem:
            assert path_type != "resource"
            fs = filesystem
            filename = resource_url_or_path
        elif path_type == "resource":  # clone a resource reference
            fs = resource_url_or_path.fs
            filename = resource_url_or_path.filename
        elif path_type == "path":
            if resource_url_or_path.is_absolute():
                parent = resource_url_or_path.parent.absolute()
                filename = resource_url_or_path.relative_to(parent).as_posix()
            else:
                parent = Path(".").absolute()
                filename = resource_url_or_path.as_posix()
            fs = open_fs(str(parent))
            if filename[1] == ":":  # windows path with colon
                filename = filename[2:]
        elif path_type == "url":
            path, filename = resource_url_or_path.replace("\\", "/").rsplit("/", 1)
            fs = open_fs(path)

        self.fs = fs
        self.filename = filename

    exists = proxy("exists")
    open = proxy("open")
    unlink = proxy("remove")
    removedir = proxy("removedir")
    removetree = proxy("removetree")
    geturl = proxy("geturl")

    def getospath(self):
        return os.fsdecode(self.fs.getospath(self.filename))

    def joinpath(self, other):
        path = fspath.join(self.filename, other)
        return FSResource(self.fs.geturl(path))

    def copy_to(self, other):
        if isinstance(other, (str, Path)):
            other = FSResource(other)
        copy.copy_file(self.fs, self.filename, other.fs, other.filename)

    def mkdir(self, *, parents=False, exist_ok=False):
        if parents:
            self.fs.makedirs(self.filename, recreate=exist_ok)
        else:
            self.fs.makedir(self.filename, recreate=exist_ok)

    def __contains__(self, other):
        return other in str(self.geturl())

    def __truediv__(self, other):
        return self.joinpath(other)

    def __rtruediv__(self, other):
        return self.joinpath(other)

    def __str__(self):
        return f"<FSResource {self.geturl()}"


@contextmanager
def open_fs_resource(
    resource_url_or_path: Union[str, Path], filesystem: base.FS = None
):
    resource = FSResource(resource_url_or_path, filesystem)
    if not filesystem:
        filesystem = resource.fs
    try:
        yield resource
    finally:
        filesystem.close()


if __name__ == "__main__":  # pragma: no cover
    import doctest

    doctest.testmod(report=True)
