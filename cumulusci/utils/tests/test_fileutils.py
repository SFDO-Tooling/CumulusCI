import doctest
from io import BytesIO, UnsupportedOperation
from pathlib import Path
from unittest import mock

import pytest
import responses

from cumulusci.utils import fileutils, temporary_dir
from cumulusci.utils.fileutils import load_from_source


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
        with load_from_source(BytesIO(b"foo")) as (path, file):
            data = file.read()
            assert isinstance(data, str)
            assert data == "foo"

    def test_writable_file_throws(self):
        with temporary_dir():
            with open("writable", "wt") as t:
                with pytest.raises(UnsupportedOperation):
                    with load_from_source(t) as (filename, data):
                        pass

    @responses.activate
    def test_load_from_url(self):
        html = "<!DOCTYPE HTML ..."
        responses.add("GET", "http://www.salesforce.com", body=html)
        with load_from_source("http://www.salesforce.com") as (filename, data):
            assert data.read() == html

    @responses.activate
    def test_load_from_Path(self):
        import cumulusci

        p = Path(cumulusci.__file__).parent / "cumulusci.yml"
        with load_from_source(p) as (filename, data):
            assert "tasks:" in data.read()

    @responses.activate
    def test_load_from_path_string(self):
        import cumulusci

        p = Path(cumulusci.__file__).parent / "cumulusci.yml"
        with load_from_source(str(p)) as (filename, data):
            assert "tasks:" in data.read()
