import os
import shutil
import urllib.request
import webbrowser
from contextlib import contextmanager
from io import StringIO, TextIOWrapper
from pathlib import Path
from typing import IO, ContextManager, Text, Tuple, Union
from urllib.parse import unquote, urlparse

import requests

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
    """Local filesystem resource wrapper (pyfilesystem2-compatible subset).

    This class is a minimal, local-only replacement for the small portion of
    the PyFilesystem2 API that CumulusCI used. It exposes a pathlib-like
    interface with a few methods that match prior usage patterns, allowing us
    to remove the external "fs" dependency while keeping existing call sites
    working.

    Scope and behavior:
    - Only local filesystem operations are supported. Remote backends (e.g.,
      S3/FTP/ZIP) and non-"file" schemes are not supported and will raise
      ValueError when passed as URLs.
    - Supported operations include: exists, open, unlink, rmdir, removetree,
      mkdir(parents, exist_ok), copy_to, joinpath, geturl, getsyspath,
      __fspath__, and path-style division ("/").
    - "file://" URLs are supported for both absolute and relative paths;
      other URL schemes are rejected.
    - getsyspath returns an absolute path without resolving symlinks so that
      macOS paths under "/var" vs "/private/var" remain textually stable in
      comparisons.
    - close() is a no-op in this implementation.

    Create instances via the open_fs_resource() context manager or the
    FSResource.new() classmethod when you don't need context management.
    """

    def __init__(self):
        raise NotImplementedError("Please use open_fs_resource context manager")

    @classmethod
    def new(
        cls,
        resource_url_or_path: Union[str, Path, "FSResource"],
        filesystem=None,
    ):
        """Directly create a new FSResource from a URL or path (absolute or relative)

        The `filesystem` parameter is ignored in this implementation and exists only
        for backward compatibility with callers. This FSResource operates solely on
        the local filesystem using pathlib and shutil.
        """
        self = cls.__new__(cls)

        if isinstance(resource_url_or_path, FSResource):
            self._path = Path(resource_url_or_path.getsyspath())
            return self

        # Handle string inputs, including file:// URLs
        if isinstance(resource_url_or_path, str):
            if "://" in resource_url_or_path:
                parsed = urlparse(resource_url_or_path)
                if parsed.scheme != "file":
                    raise ValueError(
                        f"Unsupported URL scheme for FSResource: {parsed.scheme}"
                    )
                # Support non-standard relative file URLs like file://relative/path
                if parsed.netloc:
                    combined = (parsed.netloc or "") + (parsed.path or "")
                    # Remove a single leading slash that urlparse keeps before the path segment
                    if combined.startswith("/"):
                        combined = combined[1:]
                    path_str = unquote(combined)
                else:
                    path_str = unquote(parsed.path or "")
                # On Windows, file URLs may begin with a leading slash before drive
                if (
                    os.name == "nt"
                    and path_str.startswith("/")
                    and len(path_str) > 3
                    and path_str[2] == ":"
                ):
                    path_str = path_str[1:]
                self._path = Path(path_str)
            else:
                self._path = Path(resource_url_or_path)
        else:
            # Path-like
            self._path = Path(resource_url_or_path)

        return self

    def exists(self):
        # Use os.path.exists to avoid interference from patched Path.exists in tests
        return os.path.exists(str(self.getsyspath()))

    def open(self, *args, **kwargs):
        return self.getsyspath().open(*args, **kwargs)

    def unlink(self):
        self.getsyspath().unlink(missing_ok=True)

    def rmdir(self):
        self.getsyspath().rmdir()

    def removetree(self):
        shutil.rmtree(self.getsyspath(), ignore_errors=True)

    def geturl(self):
        p = self.getsyspath()
        # Path.as_uri requires absolute path
        if not p.is_absolute():
            p = p.resolve()
        return p.as_uri()

    def getsyspath(self):
        # Return absolute path without resolving symlinks to preserve /var vs /private/var semantics on macOS
        return Path(os.path.abspath(str(self._path)))

    def joinpath(self, other):
        """Create a new FSResource based on an existing one

        Note that calling .close() on either one (or exiting the
        context of the original) will close the filesystem that both use.

        In practice, if you use the new one within the open context
        of the old one, you'll be fine.
        """
        return FSResource.new(self.getsyspath() / other)

    def copy_to(self, other):
        """Create a new FSResource by copying the underlying resource

        Note that calling .close() on either one (or exiting the
        context of the original) will close the filesystem that both use.

        In practice, if you use the new one within the open context
        of the old one, you'll be fine.
        """
        if isinstance(other, (str, Path)):
            other = FSResource.new(other)
        src = self.getsyspath()
        dst = other.getsyspath()
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)

    def mkdir(self, *, parents=False, exist_ok=False):
        p = self.getsyspath()
        if parents:
            p.mkdir(parents=True, exist_ok=exist_ok)
        else:
            # Emulate pyfilesystem's behavior: raise if exists and exist_ok is False
            if p.exists() and not exist_ok:
                raise FileExistsError(str(p))
            p.mkdir(exist_ok=exist_ok)

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
            return rc[7:] if rc.startswith("file:///") else rc[6:]
        return rc

    def __fspath__(self):
        return str(self.getsyspath())

    def close(self):
        # No-op for local filesystem-backed resource
        return None

    @staticmethod
    @contextmanager
    def open_fs_resource(
        resource_url_or_path: Union[str, Path, "FSResource"], filesystem=None
    ):
        """Create a context-managed FSResource (local filesystem only).

        - Accepts a path (absolute or relative), a "file://" URL, or an
          existing FSResource, and yields a compatible FSResource instance.
        - Non-"file" URL schemes are not supported.
        - The optional ``filesystem`` argument is ignored and kept only for
          backward compatibility with older call sites.

        Examples:

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
        try:
            yield resource
        finally:
            # No underlying remote filesystem to close in this implementation
            pass


open_fs_resource = FSResource.open_fs_resource

if __name__ == "__main__":  # pragma: no cover
    import doctest

    doctest.testmod(report=True)
