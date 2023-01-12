import os
import urllib.request
import webbrowser
from contextlib import contextmanager
from io import StringIO, TextIOWrapper
from pathlib import Path
from typing import IO, ContextManager, Text, Tuple, Union

import requests
from fs import base, copy, open_fs
from fs import path as fspath

"""Utilities for working with files"""

DataInput = Union[str, IO, Path, "FSResource"]


def _get_path_from_stream(stream):
    "Try to infer a name from an open stream"
    stream_name = getattr(stream, "name", None)
    if isinstance(stream_name, str):
        path = Path(stream_name).absolute()
    else:
        path = getattr(stream, "url", "<stream>")
    return str(path)


@contextmanager
def load_from_source(source: DataInput) -> ContextManager[Tuple[IO[Text], Text]]:
    """Normalize potential data sources into uniform tuple

    Take as input a file-like, path-like, or URL-like
    and convert to a file-like and a string representing
    where it came from. Pass the open file to the loader
    to load the data and then return the result.

    Think of this function as similar to "curl".
    Get data from anywhere easily.

    For example:

    >>> from yaml import safe_load
    >>> with load_from_source("cumulusci.yml") as (file, path):
    ...      print(path)
    ...      print(safe_load(file).keys())
    ...
    cumulusci.yml
    dict_keys(['project', 'sources', 'tasks', 'flows', 'orgs'])

    >>> with load_from_source('http://www.salesforce.com') as (file, path):
    ...     print(path)
    ...     print(file.read(10).strip())
    ...
    http://www.salesforce.com
    <!DOCTYPE

    >>> from urllib.request import urlopen
    >>> with urlopen("https://www.salesforce.com") as f:
    ...     with load_from_source(f) as (file, path):
    ...         print(path)
    ...         print(file.read(10).strip())  #doctest: +ELLIPSIS
    ...
    https://www.salesforce.com/...
    <!DOCTYPE...

    >>> from pathlib import Path
    >>> p = Path(".") / "cumulusci.yml"
    >>> with load_from_source(p) as (file, path):
    ...     print(path)
    ...     print(file.readline().strip())
    ...
    cumulusci.yml
    # yaml-language-server: $schema=cumulusci/schema/cumulusci.jsonschema.json
    """
    if (
        hasattr(source, "read") and hasattr(source, "readable") and source.readable()
    ):  # open file-like
        path = _get_path_from_stream(source)
        if not hasattr(source, "encoding"):  # not decoded yet
            source = TextIOWrapper(source, "utf-8")
        yield source, path
    elif hasattr(source, "open"):  # pathlib.Path-like
        with source.open("rt", encoding="utf-8") as f:
            path = str(source)
            yield f, path
    elif "://" in source:  # URL string-like
        url = source
        resp = requests.get(url)
        resp.raise_for_status()
        yield StringIO(resp.text), url
    else:  # path-string-like
        path = source
        with open(path, "rt", encoding="utf-8") as f:
            yield f, path


def proxy(funcname):
    def func(self, *args, **kwargs):
        real_func = getattr(self.fs, funcname)
        return real_func(self.filename, *args, **kwargs)

    return func


def view_file(path):
    """Open the given file in a webbrowser or whatever

    This uses webbrowser.open which might open the file in something other
    than a web browser (eg: a spreadsheet app if you open a .csv file)
    """
    if not isinstance(path, Path):
        path = Path(path)
    url = f"file://{urllib.request.pathname2url(str(path.resolve()))}"
    webbrowser.open(url)


class FSResource:
    """Generalization of pathlib.Path to support S3, FTP, etc

    Create them through the open_fs_resource module function or static
    function which will create a context manager that generates an FSResource.

    If you don't need the resource management aspects of the context manager,
    you can call the `new()` classmethod."""

    def __init__(self):
        raise NotImplementedError("Please use open_fs_resource context manager")

    @classmethod
    def new(
        cls,
        resource_url_or_path: Union[str, Path, "FSResource"],
        filesystem: base.FS = None,
    ):
        """Directly create a new FSResource from a URL or path (absolute or relative)

        You can call this to bypass the context manager in contexts where closing isn't
        important (e.g. interactive repl experiments)."""
        self = cls.__new__(cls)

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
            filename = str(resource_url_or_path)
        elif path_type == "resource":  # clone a resource reference
            fs = resource_url_or_path.fs
            filename = resource_url_or_path.filename
        elif path_type == "path":
            if resource_url_or_path.is_absolute():
                if resource_url_or_path.drive:
                    root = resource_url_or_path.drive + "/"
                else:
                    root = resource_url_or_path.root
                filename = resource_url_or_path.relative_to(root).as_posix()
            else:
                root = Path("/").absolute()
                filename = (
                    (Path(".") / resource_url_or_path)
                    .absolute()
                    .relative_to(root)
                    .as_posix()
                )
            fs = open_fs(str(root))
        elif path_type == "url":
            path, filename = resource_url_or_path.replace("\\", "/").rsplit("/", 1)
            fs = open_fs(path)

        self.fs = fs
        self.filename = filename
        return self

    exists = proxy("exists")
    open = proxy("open")
    unlink = proxy("remove")
    rmdir = proxy("removedir")
    removetree = proxy("removetree")
    geturl = proxy("geturl")

    def getsyspath(self):
        return Path(os.fsdecode(self.fs.getsyspath(self.filename)))

    def joinpath(self, other):
        """Create a new FSResource based on an existing one

        Note that calling .close() on either one (or exiting the
        context of the original) will close the filesystem that both use.

        In practice, if you use the new one within the open context
        of the old one, you'll be fine.
        """
        path = fspath.join(self.filename, other)
        return FSResource.new(self.fs.geturl(path))

    def copy_to(self, other):
        """Create a new FSResource by copying the underlying resource

        Note that calling .close() on either one (or exiting the
        context of the original) will close the filesystem that both use.

        In practice, if you use the new one within the open context
        of the old one, you'll be fine.
        """
        if isinstance(other, (str, Path)):
            other = FSResource.new(other)
        copy.copy_file(self.fs, self.filename, other.fs, other.filename)

    def mkdir(self, *, parents=False, exist_ok=False):
        if parents:
            self.fs.makedirs(self.filename, recreate=exist_ok)
        else:
            self.fs.makedir(self.filename, recreate=exist_ok)

    def __contains__(self, other):
        return other in str(self.geturl())

    @property
    def suffix(self):
        return Path(self).suffix

    def __truediv__(self, other):
        return self.joinpath(other)

    def __repr__(self):
        return f"<FSResource {self.geturl()}>"

    def __str__(self):
        rc = self.geturl()
        if rc.startswith("file://"):
            return rc[6:]

    def __fspath__(self):
        return self.fs.getsyspath(self.filename)

    def close(self):
        self.fs.close()

    @staticmethod
    @contextmanager
    def open_fs_resource(
        resource_url_or_path: Union[str, Path, "FSResource"], filesystem: base.FS = None
    ):
        """Create a context-managed FSResource

        Input is a URL, path (absolute or relative) or FSResource

        The function should be used in a context manager. The
        resource's underlying filesystem will be closed automatically
        when the context ends and the data will be saved back to the
        filesystem (local, remote, zipfile, etc.)

        Think of it as a way of "mounting" a filesystem, directory or file.

        For example:

        >>> from tempfile import TemporaryDirectory
        >>> with TemporaryDirectory() as tempdir:
        ...     abspath = Path(tempdir) / "blah"
        ...     with open_fs_resource(abspath) as fs:
        ...         fs.mkdir()
        ...     newfile = fs / "newfile"
        ...     with newfile.open("w") as f:
        ...         _ = f.write("xyzzy")
        ...     with newfile.open("r") as f:
        ...         print(f.read())
        xyzzy

        >>> with open_fs_resource("cumulusci.yml") as cumulusci_yml:
        ...      with cumulusci_yml.open() as c:
        ...          print(c.read(5))
        # yam

        """
        resource = FSResource.new(resource_url_or_path, filesystem)
        if not filesystem:
            filesystem = resource
        try:
            yield resource
        finally:
            filesystem.close()


open_fs_resource = FSResource.open_fs_resource

if __name__ == "__main__":  # pragma: no cover
    import doctest

    doctest.testmod(report=True)
