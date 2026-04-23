"""Resolve ``--extra-yaml`` CLI flag and ``CUMULUSCI_EXTRA_YAML`` env var.

The returned string is passed as ``BaseProjectConfig``'s ``additional_yaml``
kwarg, which already merges into the project config via the existing YAML
merge stack.
"""
import os
from typing import Optional, Tuple

import click

from cumulusci.core.exceptions import CumulusCIUsageError

ENV_VAR = "CUMULUSCI_EXTRA_YAML"


def resolve_extra_yaml(paths: Tuple[str, ...]) -> Optional[str]:
    """Read extra-yaml paths from the CLI flag (preferred) or env var (fallback).

    Args:
        paths: Tuple of paths from Click's ``multiple=True`` option. Empty
            means the flag was not supplied; fall back to
            ``CUMULUSCI_EXTRA_YAML`` (colon-separated paths).

    Returns:
        Concatenated YAML content with ``\\n---\\n`` separators between files,
        or ``None`` if no paths were resolved.

    Raises:
        CumulusCIUsageError: If any listed path does not exist or is unreadable.
    """
    effective_paths = paths
    if not effective_paths:
        env_value = os.environ.get(ENV_VAR)
        if env_value:
            effective_paths = tuple(p for p in env_value.split(":") if p)

    if not effective_paths:
        return None

    click.echo(
        f"Loading extra YAML from: {', '.join(effective_paths)}. "
        "Extra YAML can redefine task class_path entries and run arbitrary "
        "Python code; only load files you trust.",
        err=True,
    )

    contents = []
    for path in effective_paths:
        if not os.path.isfile(path):
            raise CumulusCIUsageError(f"--extra-yaml file not found: {path}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                contents.append(f.read())
        except OSError as e:
            raise CumulusCIUsageError(f"--extra-yaml could not read {path}: {e}")
    return "\n---\n".join(contents)
