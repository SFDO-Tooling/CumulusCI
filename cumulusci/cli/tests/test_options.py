from cumulusci.cli import options
from cumulusci.core.config import BaseGlobalConfig


def test_no_prompt_callback_env(monkeypatch):
    monkeypatch.setenv(options.NO_PROMPT_ENV, "true")
    selected_val = options.no_prompt_callback(None, None, False)
    assert selected_val == "true"


def test_no_prompt_callback_global(monkeypatch):
    monkeypatch.setattr(BaseGlobalConfig, "config", {"cli": {"no_prompt": True}})
    selected_val = options.no_prompt_callback(None, None, False)
    assert selected_val is True


def test_no_prompt_callback_local(monkeypatch):
    monkeypatch.setattr(BaseGlobalConfig, "config", {"cli": {"no_prompt": None}})
    selected_val = options.no_prompt_callback(None, None, True)
    assert selected_val is True


def test_plain_output_callback_env(monkeypatch):
    monkeypatch.setenv(options.PLAIN_OUTPUT_ENV, "true")
    selected_val = options.plain_output_callback(None, None, False)
    assert selected_val == "true"


def test_plain_output_callback_global(monkeypatch):
    monkeypatch.setattr(BaseGlobalConfig, "config", {"cli": {"plain_output": True}})
    selected_val = options.plain_output_callback(None, None, False)
    assert selected_val is True


def test_plain_output_callback_local(monkeypatch):
    monkeypatch.setattr(BaseGlobalConfig, "config", {"cli": {"plain_output": None}})
    selected_val = options.plain_output_callback(None, None, True)
    assert selected_val is True


def test_select_val_env(monkeypatch):
    monkeypatch.setenv("TEST", "expected")
    selected_val = options._select_value("TEST", None, "fail")
    assert selected_val == "expected"


def test_select_val_global(monkeypatch):
    monkeypatch.delenv("TEST", raising=False)
    selected_val = options._select_value("TEST", "expected", "fail")
    assert selected_val == "expected"


def test_select_val_local(monkeypatch):
    monkeypatch.delenv("TEST", raising=False)
    selected_val = options._select_value("TEST", None, "expected")
    assert selected_val == "expected"
