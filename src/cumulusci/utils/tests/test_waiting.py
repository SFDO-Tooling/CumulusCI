from unittest import mock

import pytest

from cumulusci.utils.waiting import poll, retry


def test_retry(caplog):
    func = mock.Mock(side_effect=[Exception, 42])
    assert retry(func) == 42
    assert "Sleeping for 5 seconds before retry..." in caplog.text
    assert "Retrying (4 attempts remaining)" in caplog.text


def test_retry__limit():
    func = mock.Mock(side_effect=Exception)
    with pytest.raises(Exception):
        retry(func, retries=0)
    assert func.call_count == 1


def test_poll():
    func = mock.Mock(side_effect=[False, False, False, True])
    poll(func)
    assert func.call_count == 4
