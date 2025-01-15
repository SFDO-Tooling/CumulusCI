import doctest
import os
import sys
import time
import urllib.request
from io import BytesIO, UnsupportedOperation
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import pytest
import responses
from fs import errors, open_fs

import cumulusci
from cumulusci.utils import fileutils, temporary_dir, update_tree
from cumulusci.utils.fileutils import (
    FSResource,
    load_from_source,
    open_fs_resource,
    view_file,
)


class TestFileutils:
    @responses.activate
    @mock.patch("urllib.request.urlopen")
    def test_docstrings(self, urlopen):
        pretend_html = b"<!DOCTYPE HTML ...blah blah blah"
        responses.add("GET", "http://www.salesforce.com/", body=pretend_html)
        fake_http_stream = BytesIO(pretend_html)
        fake_http_stream.url = "https://www.salesforce.com/"
        urlopen.return_value = fake_http_stream
        try:
            doctest.testmod(fileutils, raise_on_error=True, verbose=True)
        except doctest.DocTestFailure as e:
            print("Got")
            print(str(e.got))
            raise

    def test_binary_becomes_string(self):
        with load_from_source(BytesIO(b"foo")) as (file, path):
            data = file.read()
            assert isinstance(data, str)
            assert data == "foo"

    def test_writable_file_throws(self):
        with temporary_dir():
            with open("writable", "wt") as t:
                with pytest.raises(UnsupportedOperation):
                    with load_from_source(t) as (data, filename):
                        pass

    @responses.activate
    def test_load_from_url(self):
        html = "<!DOCTYPE HTML ..."
        responses.add("GET", "http://www.salesforce.com", body=html)
        with load_from_source("http://www.salesforce.com") as (data, filename):
            assert data.read() == html

    def test_load_from_Path(self):
        p = Path(cumulusci.__file__).parent / "cumulusci.yml"
        with load_from_source(p) as (data, filename):
            assert "tasks:" in data.read()

    def test_load_from_path_string(self):
        p = Path(cumulusci.__file__).parent / "cumulusci.yml"
        with load_from_source(str(p)) as (data, filename):
            assert "tasks:" in data.read()

    def test_load_from_open_file(self):
        p = Path(cumulusci.__file__).parent / "cumulusci.yml"
        with open(p) as f:
            with load_from_source(f) as (data, filename):
                assert "tasks:" in data.read()
                assert str(p) == filename

    def test_load_from_fs_resource(self):
        p = Path(cumulusci.__file__).parent / "cumulusci.yml"
        with open_fs_resource(p) as p2:
            with load_from_source(p2) as (data, filename):
                assert "tasks:" in data.read()

    def test_view_file_str_path(self):
        """Verify view_file works when given a path as a string"""
        with mock.patch("webbrowser.open") as webbrowser_open:
            path = "robot/results/index.html"
            view_file(path)
            url = f"file://{urllib.request.pathname2url(str(Path(path).resolve()))}"
            webbrowser_open.assert_called_once_with(url)

    def test_view_file_Path(self):
        """Verify view_file works when given a path as a Path object"""
        with mock.patch("webbrowser.open") as webbrowser_open:
            path = Path("robot/results/index.html")
            view_file(path)
            url = f"file://{urllib.request.pathname2url(str(path.resolve()))}"
            webbrowser_open.assert_called_once_with(url)


class _TestFSResourceShared:
    file = Path(__file__)

    def test_resource_exists_abspath(self):
        abspath = os.path.abspath(self.file)
        with open_fs_resource(abspath) as resource:
            assert resource.exists()
            assert str(resource.getsyspath()) == abspath

    def test_resource_does_not_exist(self):
        abspath = os.path.abspath(self.file)
        with open_fs_resource(abspath + "xyzzy") as resource:
            assert not resource.exists()
            assert abspath + "xyzzy" in resource

    def test_resource_exists_pathlib_abspath(self):
        abspath = os.path.abspath(self.file)
        with open_fs_resource(Path(abspath)) as resource:
            assert resource.exists()
            assert abspath in resource

    def test_resource_doesnt_exist_pathlib_abspath(self):
        abspath = os.path.abspath(self.file)
        with open_fs_resource(Path(abspath + "xyzzy")) as resource:
            assert not resource.exists()
            assert abspath + "xyzzy" in resource

    def test_resource_exists_url_abspath(self):
        abspath = os.path.abspath(self.file)
        url = f"file://{abspath}"
        with open_fs_resource(url) as resource:
            assert resource.exists()
            assert abspath in resource

    def test_resource_as_str(self):
        abspath = os.path.abspath(self.file)
        with open_fs_resource(Path(abspath)) as resource:
            assert "file://" in repr(resource)

    def test_join_paths(self):
        parent = Path(self.file).parent
        with open_fs_resource(parent) as resource:
            this_file = resource / self.file.name
            assert this_file.exists()

    def test_clone_fsresource(self):
        abspath = os.path.abspath(self.file)
        with open_fs_resource(Path(abspath)) as resource:
            with open_fs_resource(resource) as resource2:
                assert abspath in str(resource2)

    def test_load_from_file_system(self):
        abspath = os.path.abspath(self.file)
        fs = open_fs("/")
        with open_fs_resource(abspath, fs) as f:
            assert abspath in str(f)

    def test_windows_path(self):
        abspath = "c:\\foo\\bar"
        with open_fs_resource(abspath) as f:
            if sys.platform == "win32":
                assert str(f.getsyspath()), str(f.getsyspath()) == r"c:\foo\bar"


class TestFSResource(_TestFSResourceShared):
    def test_resource_exists_relpath(self):
        relpath = os.path.relpath(self.file)
        with open_fs_resource(relpath) as resource:
            assert resource.exists()
            assert (
                str(Path(resource.getsyspath()).relative_to(Path(".").absolute()))
                == relpath
            )

    def test_resource_doesnt_exist_relpath(self):
        relpath = os.path.relpath(self.file)
        with open_fs_resource(relpath + "xyzzy") as resource:
            assert not resource.exists()
            assert relpath + "xyzzy" in resource

    def test_resource_exists_pathlib_relpath(self):
        relpath = os.path.relpath(self.file)
        with open_fs_resource(Path(relpath)) as resource:
            assert resource.exists()
            assert relpath in resource

    def test_resource_exists_url_relpath(self):
        relpath = os.path.relpath(self.file)
        url = f"file://{relpath}"
        with open_fs_resource(url) as resource:
            assert resource.exists()
            assert relpath in resource

    def test_resource_test_resource_doesnt_exist_pathlib_relpath(self):
        relpath = os.path.relpath(self.file)
        with open_fs_resource(Path(relpath + "xyzzy")) as resource:
            assert not resource.exists()
            assert relpath + "xyzzy" in resource


class TestFSResourceTempdir(_TestFSResourceShared):
    def setup_method(self):
        self.tempdir = TemporaryDirectory()
        self.file = Path(self.tempdir.name) / "testfile.txt"
        self.file.touch()

    def teardown(self):
        self.tempdir.cleanup()

    def test_copy_to(self):
        abspath = os.path.abspath(self.file)
        with open_fs_resource(abspath) as f:
            f.copy_to(abspath + ".bak")
            assert Path(abspath + ".bak").exists()
            f.copy_to(Path(abspath + ".bak2"))
            assert Path(abspath + ".bak2").exists()
            f.copy_to(FSResource.new(abspath + ".bak3"))
            assert Path(abspath + ".bak3").exists()

    def test_mkdir_rmdir(self):
        abspath = Path(self.tempdir.name) / "doesnotexist"
        assert not abspath.exists()
        with open_fs_resource(abspath) as f:
            f.mkdir()
            assert abspath.exists()
            f.mkdir(exist_ok=True)
            f.rmdir()

        abspath = abspath / "foo" / "bar" / "baz"
        assert not abspath.exists()
        with open_fs_resource(abspath) as f:
            f.mkdir(parents=True)
            f.mkdir(parents=True, exist_ok=True)
            f.mkdir(parents=False, exist_ok=True)
            assert abspath.exists()

            with pytest.raises(errors.DirectoryExists):
                f.mkdir(parents=False, exist_ok=False)
            f.rmdir()

    def test_open_for_write(self):
        abspath = Path(self.tempdir.name) / "blah"
        with open_fs_resource(abspath) as fs:
            fs.mkdir()
            newfile = fs / "newfile"
            with newfile.open("w") as f:
                f.write("xyzzy")

            with newfile.open("r") as f:
                assert f.read() == "xyzzy"


class TestFSResourceError:
    def test_fs_resource_init_error(self):
        with pytest.raises(NotImplementedError):
            FSResource()


def test_update_tree(tmpdir):
    source_dir = Path(tmpdir.mkdir("source"))
    source_file = source_dir / "testfile.txt"
    source_file.write_text("original content")

    dest_dir = Path(tmpdir.mkdir("dest"))
    dest_file = dest_dir / "testfile.txt"
    dest_file.write_text("modified content")

    # Ensure the source file has an older timestamp
    past_time = time.time() - 100
    os.utime(str(source_file), (past_time, past_time))

    update_tree(source_dir, dest_dir)

    assert dest_file.read_text() == "modified content"

    # Add a new file to source and run update_tree again
    new_source_file = source_dir / "newfile.txt"
    new_source_file.write_text("new file content")
    update_tree(source_dir, dest_dir)

    # Verify that the new file is copied to destination
    new_dest_file = dest_dir / "newfile.txt"
    assert new_dest_file.exists()
    assert new_dest_file.read_text() == "new file content"
