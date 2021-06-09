import io
import pytest

from unittest import mock

from cumulusci.core.exceptions import SfdxOrgException
from cumulusci.core.sfdx import get_default_devhub_username
from cumulusci.core.sfdx import shell_quote
from cumulusci.core.sfdx import sfdx


class TestSfdx:
    @mock.patch("platform.system", mock.Mock(return_value="Linux"))
    @mock.patch("sarge.Command")
    def test_posix_quoting(self, Command):
        sfdx("cmd", args=["a'b"])
        cmd = Command.call_args[0][0]
        assert cmd == r"sfdx cmd 'a'\''b'"

    @mock.patch("platform.system", mock.Mock(return_value="Windows"))
    @mock.patch("sarge.Command")
    def test_windows_quoting(self, Command):
        sfdx("cmd", args=['a"b'], access_token="token")
        cmd = Command.call_args[0][0]
        assert cmd == r'sfdx cmd "a\"b" -u token'

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
