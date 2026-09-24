import textwrap
from contextlib import contextmanager

import pytest

from cumulusci.cli.extra_yaml import resolve_extra_yaml
from cumulusci.cli.runtime import CliRuntime
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


def test_resolve_extra_yaml__env_var_multiple_comma_separated(tmp_path, monkeypatch):
    """Env var with multiple paths produces a deep-merged document."""
    import yaml

    a = tmp_path / "a.yml"
    a.write_text("tasks:\n  a:\n    description: from A\n")
    b = tmp_path / "b.yml"
    b.write_text("tasks:\n  b:\n    description: from B\n")
    monkeypatch.setenv("CUMULUSCI_EXTRA_YAML", f"{a},{b}")
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
    monkeypatch.setenv("CUMULUSCI_EXTRA_YAML", f",,{p},,")
    result = resolve_extra_yaml(())
    assert result is not None
    assert "project: {}" in result


@contextmanager
def _minimal_project(tmp_path, monkeypatch):
    """Create a minimal cci project dir and chdir into it."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / "cumulusci.yml").write_text(
        textwrap.dedent(
            """\
            minimum_cumulusci_version: '3.0.0'
            project:
                name: extra_yaml_test
                package:
                    name: ExtraYamlTest
                    api_version: '58.0'
                git:
                    default_branch: main
            tasks:
                existing_task:
                    description: From cumulusci.yml
                    class_path: cumulusci.tasks.util.Sleep
                    options:
                        seconds: 1
            """
        )
    )
    yield tmp_path


def test_extra_yaml__overrides_existing_task_option(tmp_path, monkeypatch):
    monkeypatch.delenv("CUMULUSCI_EXTRA_YAML", raising=False)
    with _minimal_project(tmp_path, monkeypatch):
        extra = tmp_path / "extra.yml"
        extra.write_text("tasks:\n  existing_task:\n    options:\n      seconds: 99\n")
        runtime = CliRuntime(load_keychain=False)
        runtime.reload_project_config(additional_yaml=resolve_extra_yaml((str(extra),)))
        assert runtime.project_config is not None
        task_cfg = runtime.project_config.get_task("existing_task")
        assert task_cfg.options["seconds"] == 99
        # Description from cumulusci.yml still present (deep merge).
        assert task_cfg.description == "From cumulusci.yml"


def test_extra_yaml__multi_file_last_wins(tmp_path, monkeypatch):
    monkeypatch.delenv("CUMULUSCI_EXTRA_YAML", raising=False)
    with _minimal_project(tmp_path, monkeypatch):
        a = tmp_path / "a.yml"
        a.write_text("tasks:\n  existing_task:\n    options:\n      seconds: 10\n")
        b = tmp_path / "b.yml"
        b.write_text("tasks:\n  existing_task:\n    options:\n      seconds: 20\n")
        runtime = CliRuntime(load_keychain=False)
        runtime.reload_project_config(
            additional_yaml=resolve_extra_yaml((str(a), str(b)))
        )
        assert runtime.project_config is not None
        task_cfg = runtime.project_config.get_task("existing_task")
        assert task_cfg.options["seconds"] == 20


def test_extra_yaml__defines_new_task(tmp_path, monkeypatch):
    monkeypatch.delenv("CUMULUSCI_EXTRA_YAML", raising=False)
    with _minimal_project(tmp_path, monkeypatch):
        extra = tmp_path / "extra.yml"
        extra.write_text(
            "tasks:\n"
            "  brand_new_task:\n"
            "    description: defined in extra\n"
            "    class_path: cumulusci.tasks.util.Sleep\n"
            "    options:\n"
            "      seconds: 0\n"
        )
        runtime = CliRuntime(load_keychain=False)
        runtime.reload_project_config(additional_yaml=resolve_extra_yaml((str(extra),)))
        assert runtime.project_config is not None
        task_cfg = runtime.project_config.get_task("brand_new_task")
        assert task_cfg.description == "defined in extra"


def test_extra_yaml__class_path_override_imports_new_class(tmp_path, monkeypatch):
    """Extra YAML can swap class_path to any importable class.

    Demonstrates (rather than prevents) the documented trust posture.
    """
    monkeypatch.delenv("CUMULUSCI_EXTRA_YAML", raising=False)
    with _minimal_project(tmp_path, monkeypatch):
        extra = tmp_path / "extra.yml"
        extra.write_text(
            "tasks:\n  existing_task:\n    class_path: cumulusci.tasks.util.LogLine\n"
        )
        runtime = CliRuntime(load_keychain=False)
        runtime.reload_project_config(additional_yaml=resolve_extra_yaml((str(extra),)))
        assert runtime.project_config is not None
        task_cfg = runtime.project_config.get_task("existing_task")
        assert task_cfg.class_path == "cumulusci.tasks.util.LogLine"
