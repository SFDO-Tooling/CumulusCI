import pytest
from cumulusci.cli import options
from cumulusci.core.config import BaseGlobalConfig


@pytest.fixture
def param_mock():
    class ParameterMock:
        envvar = None

    return ParameterMock()


def test_no_prompt_callback_global(monkeypatch, param_mock):
    monkeypatch.setattr(BaseGlobalConfig, "config", {"cli": {"always_recreate": True}})
    param_mock.envvar = options.NO_PROMPT_ENV
    selected_val = options.global_option_lookup(None, param_mock, False)
    assert selected_val is True


def test_no_prompt_callback_local(monkeypatch, param_mock):
    monkeypatch.setattr(BaseGlobalConfig, "config", {"cli": {"always_recreate": None}})
    param_mock.envvar = options.NO_PROMPT_ENV
    selected_val = options.global_option_lookup(None, param_mock, True)
    assert selected_val is True


def test_plain_output_callback_global(monkeypatch, param_mock):
    monkeypatch.setattr(BaseGlobalConfig, "config", {"cli": {"plain_output": True}})
    param_mock.envvar = options.PLAIN_OUTPUT_ENV
    selected_val = options.global_option_lookup(None, param_mock, False)
    assert selected_val is True


def test_plain_output_callback_local(monkeypatch, param_mock):
    monkeypatch.setattr(BaseGlobalConfig, "config", {"cli": {"plain_output": None}})
    param_mock.envvar = options.PLAIN_OUTPUT_ENV
    selected_val = options.global_option_lookup(None, param_mock, True)
    assert selected_val is True
