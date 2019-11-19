from unittest import mock


def test_main():
    with mock.patch("cumulusci.cli.cci.main") as main:
        from cumulusci import __main__

        __main__
    assert main.called_once
