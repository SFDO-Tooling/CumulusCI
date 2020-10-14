from unittest import mock
import io
import sys

import pytest

from cumulusci.core.exceptions import SfdxOrgException
from cumulusci.core.sfdx import get_default_devhub_username
from cumulusci.core.sfdx import sfdx


class TestSfdx:
    @pytest.mark.skipif(
        sys.platform.startswith("win"), reason="This tests quoting on POSIX systems"
    )
    @mock.patch("sarge.Command")
    def test_posix_quoting(self, Command):
        sfdx("cmd", args=["a'b"])
        cmd = Command.call_args[0][0]
        assert cmd == r"sfdx cmd 'a'\''b'"

    @pytest.mark.skipif(
        not sys.platform.startswith("win"),
        reason="This tests quoting on Windows systems",
    )
    @mock.patch("sarge.Command")
    def test_windows_quoting(self, Command):
        sfdx("cmd", args=['a"b'], access_token="token")
        cmd = Command.call_args[0][0]
        assert cmd == r'sfdx cmd "a\"b" -u token'

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
