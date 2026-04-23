import pytest

from cumulusci.cli.extra_yaml import resolve_extra_yaml
from cumulusci.core.exceptions import CumulusCIUsageError


def test_resolve_extra_yaml__none_when_no_input(monkeypatch):
    monkeypatch.delenv("CUMULUSCI_EXTRA_YAML", raising=False)
    assert resolve_extra_yaml(()) is None


def test_resolve_extra_yaml__single_file(tmp_path, monkeypatch):
    monkeypatch.delenv("CUMULUSCI_EXTRA_YAML", raising=False)
    p = tmp_path / "extra.yml"
    p.write_text("tasks:\n  foo:\n    description: from file\n")
    result = resolve_extra_yaml((str(p),))
    assert result is not None
    assert "from file" in result
    assert result.startswith("tasks:")


def test_resolve_extra_yaml__missing_file_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("CUMULUSCI_EXTRA_YAML", raising=False)
    with pytest.raises(CumulusCIUsageError, match="not found"):
        resolve_extra_yaml((str(tmp_path / "does_not_exist.yml"),))


def test_resolve_extra_yaml__multiple_files_deep_merged(tmp_path, monkeypatch):
    """Multiple files are deep-merged; last file wins on scalar conflicts."""
    import yaml

    monkeypatch.delenv("CUMULUSCI_EXTRA_YAML", raising=False)
    a = tmp_path / "a.yml"
    a.write_text("tasks:\n  foo:\n    description: from A\n    group: alpha\n")
    b = tmp_path / "b.yml"
    b.write_text("tasks:\n  foo:\n    description: from B\n")
    result = resolve_extra_yaml((str(a), str(b)))
    assert result is not None
    parsed = yaml.safe_load(result)
    # Later file's scalar wins.
    assert parsed["tasks"]["foo"]["description"] == "from B"
    # Sibling keys from earlier file are preserved (deep merge).
    assert parsed["tasks"]["foo"]["group"] == "alpha"


def test_resolve_extra_yaml__env_var_fallback(tmp_path, monkeypatch):
    p = tmp_path / "env.yml"
    p.write_text("project:\n  name: env-loaded\n")
    monkeypatch.setenv("CUMULUSCI_EXTRA_YAML", str(p))
    result = resolve_extra_yaml(())
    assert result is not None
    assert "env-loaded" in result


def test_resolve_extra_yaml__env_var_multiple_colon_separated(tmp_path, monkeypatch):
    """Env var with multiple paths produces a deep-merged document."""
    import yaml

    a = tmp_path / "a.yml"
    a.write_text("tasks:\n  a:\n    description: from A\n")
    b = tmp_path / "b.yml"
    b.write_text("tasks:\n  b:\n    description: from B\n")
    monkeypatch.setenv("CUMULUSCI_EXTRA_YAML", f"{a}:{b}")
    result = resolve_extra_yaml(())
    assert result is not None
    parsed = yaml.safe_load(result)
    assert parsed["tasks"]["a"]["description"] == "from A"
    assert parsed["tasks"]["b"]["description"] == "from B"


def test_resolve_extra_yaml__flag_overrides_env_var(tmp_path, monkeypatch):
    flag_file = tmp_path / "flag.yml"
    flag_file.write_text("tasks:\n  from: flag\n")
    env_file = tmp_path / "env.yml"
    env_file.write_text("tasks:\n  from: env\n")
    monkeypatch.setenv("CUMULUSCI_EXTRA_YAML", str(env_file))
    result = resolve_extra_yaml((str(flag_file),))
    assert result is not None
    assert "from: flag" in result
    assert "from: env" not in result


def test_resolve_extra_yaml__empty_env_var_segments_ignored(tmp_path, monkeypatch):
    p = tmp_path / "x.yml"
    p.write_text("project: {}\n")
    monkeypatch.setenv("CUMULUSCI_EXTRA_YAML", f"::{p}::")
    result = resolve_extra_yaml(())
    assert result is not None
    assert "project: {}" in result
