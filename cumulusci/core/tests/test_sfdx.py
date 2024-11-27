import io
from unittest import mock
from zipfile import ZipFile

import pytest

from cumulusci.core.exceptions import SfdxOrgException
from cumulusci.core.sfdx import (
    SourceFormat,
    convert_sfdx_source,
    get_default_devhub_username,
    get_source_format_for_path,
    get_source_format_for_zipfile,
    sfdx,
    shell_quote,
)
from cumulusci.utils import temporary_dir, touch


class TestSfdx:
    @mock.patch("platform.system", mock.Mock(return_value="Linux"))
    @mock.patch("sarge.Command")
    def test_posix_quoting(self, Command):
        sfdx("cmd", args=["a'b"])
        cmd = Command.call_args[0][0]
        assert cmd == r"sf cmd 'a'\''b'"

    @mock.patch("platform.system", mock.Mock(return_value="Windows"))
    @mock.patch("sarge.Command")
    def test_windows_quoting(self, Command):
        sfdx("cmd", args=['a"b'], access_token="token")
        cmd = Command.call_args[0][0]
        print(cmd)
        assert cmd == r'sf cmd "a\"b" -o token'

    @mock.patch("platform.system", mock.Mock(return_value="Windows"))
    def test_shell_quote__str_with_space(self):
        actual = shell_quote("pkg-name Managed Feature Test")
        assert '"pkg-name Managed Feature Test"' == actual

    @mock.patch("sarge.Command")
    def test_check_return(self, Command):
        Command.return_value.returncode = 1
        Command.return_value.stderr = io.BytesIO(b"Egads!")
        with pytest.raises(Exception) as exc_info:
            sfdx("cmd", check_return=True)
        assert str(exc_info.value) == "Command exited with return code 1:\nEgads!"


@mock.patch("sarge.Command")
def test_get_default_devhub_username(Command):
    Command.return_value.returncode = 0
    Command.return_value.stdout = io.BytesIO(
        b'{"result": [{"value": "devhub@example.com"}]}'
    )
    result = get_default_devhub_username()
    assert result == "devhub@example.com"


@mock.patch("sarge.Command")
def test_get_default_devhub_username__no_result(Command):
    Command.return_value.returncode = 0
    Command.return_value.stdout = io.BytesIO(b"{}")
    with pytest.raises(SfdxOrgException):
        get_default_devhub_username()


def test_get_source_format_for_path():
    with temporary_dir(chdir=True) as td:
        assert get_source_format_for_path(td) is SourceFormat.SFDX

        touch("package.xml")
        assert get_source_format_for_path(td) is SourceFormat.MDAPI


def test_get_source_format_for_zipfile():
    zf = ZipFile(io.BytesIO(), "w")

    zf.writestr("package.xml", "test")
    zf.writestr("src/package.xml", "test")
    zf.writestr("force-app/foo.txt", "test")

    assert get_source_format_for_zipfile(zf, None) is SourceFormat.MDAPI
    assert get_source_format_for_zipfile(zf, "src") is SourceFormat.MDAPI
    assert get_source_format_for_zipfile(zf, "force-app") is SourceFormat.SFDX


def test_convert_sfdx():
    logger = mock.Mock()
    with temporary_dir() as path:
        touch("README.md")  # make sure there's something in the directory
        with mock.patch("cumulusci.core.sfdx.sfdx") as sfdx:
            with convert_sfdx_source(path, "Test Package", logger) as p:
                assert p is not None

    sfdx.assert_called_once_with(
        "project convert source",
        args=["-d", mock.ANY, "-r", path, "-n", "Test Package"],
        capture_output=True,
        check_return=True,
    )


def test_convert_sfdx__cwd():
    logger = mock.Mock()
    with temporary_dir(chdir=True):
        touch("README.md")  # make sure there's something in the directory
        with mock.patch("cumulusci.core.sfdx.sfdx") as sfdx:
            with convert_sfdx_source(None, "Test Package", logger) as p:
                assert p is not None

    sfdx.assert_called_once_with(
        "project convert source",
        args=["-d", mock.ANY, "-n", "Test Package"],
        capture_output=True,
        check_return=True,
    )


def test_convert_sfdx__mdapi():
    logger = mock.Mock()
    with temporary_dir() as path:
        touch("package.xml")  # make sure there's something in the directory
        with mock.patch("cumulusci.core.sfdx.sfdx") as sfdx:
            with convert_sfdx_source(path, "Test Package", logger) as p:
                assert p == path

    sfdx.assert_not_called()


def test_convert_sfdx__skipped_if_directory_empty():
    logger = mock.Mock()
    with temporary_dir() as path:
        with mock.patch("cumulusci.core.sfdx.sfdx") as sfdx:
            with convert_sfdx_source(path, "Test Package", logger):
                pass

    sfdx.assert_not_called()
