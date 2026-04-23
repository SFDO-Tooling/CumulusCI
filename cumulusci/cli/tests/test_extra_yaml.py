from cumulusci.cli.extra_yaml import resolve_extra_yaml


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
