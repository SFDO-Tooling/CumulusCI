"""Resolve ``--extra-yaml`` CLI flag and ``CUMULUSCI_EXTRA_YAML`` env var.

The returned string is passed as ``BaseProjectConfig``'s ``additional_yaml``
kwarg, which already merges into the project config via the existing YAML
merge stack.
"""

import os
from pathlib import Path
from typing import Optional, Tuple

import click
import yaml

from cumulusci.core.exceptions import CumulusCIUsageError
from cumulusci.core.utils import dictmerge, process_list_arg

ENV_VAR = "CUMULUSCI_EXTRA_YAML"


def resolve_extra_yaml(paths: Tuple[str, ...]) -> Optional[str]:
    """Read extra-yaml paths from the CLI flag (preferred) or env var (fallback).

    Args:
        paths: Tuple of paths from Click's ``multiple=True`` option. Empty
            means the flag was not supplied; fall back to
            ``CUMULUSCI_EXTRA_YAML`` (comma-separated paths).

    Returns:
        A single YAML document representing the deep-merge of all input files
        (later files override earlier files), or ``None`` if no paths were
        resolved. The returned string is a valid single-document YAML stream
        suitable for ``BaseProjectConfig(additional_yaml=...)``.

    Raises:
        CumulusCIUsageError: If any listed path does not exist or is unreadable.
    """
    effective_paths = paths
    if not effective_paths:
        env_value = os.environ.get(ENV_VAR)
        if env_value:
            effective_paths = tuple(p for p in (process_list_arg(env_value) or []) if p)

    if not effective_paths:
        return None

    click.echo(
        f"Loading extra YAML from: {', '.join(effective_paths)}. "
        "Extra YAML can redefine task class_path entries and run arbitrary "
        "Python code; only load files you trust.",
        err=True,
    )

    merged: dict = {}
    for path in effective_paths:
        file_path = Path(path)
        if not file_path.is_file():
            raise CumulusCIUsageError(f"--extra-yaml file not found: {path}")
        try:
            raw = file_path.read_text(encoding="utf-8")
        except OSError as e:
            raise CumulusCIUsageError(f"--extra-yaml could not read {path}: {e}")
        try:
            parsed = yaml.safe_load(raw) or {}
        except yaml.YAMLError as e:
            raise CumulusCIUsageError(f"--extra-yaml could not parse {path}: {e}")
        if not isinstance(parsed, dict):
            raise CumulusCIUsageError(
                f"--extra-yaml expects a YAML mapping at the top level in {path}"
            )
        merged = dictmerge(merged, parsed)
    return yaml.safe_dump(merged, default_flow_style=False)
