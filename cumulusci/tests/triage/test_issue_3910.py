"""Repro for SFDO-Tooling/CumulusCI#3910.

The JSON schema (and underlying Pydantic model) for a ``ScratchOrg``
incorrectly declares ``namespaced`` as ``str`` when both the
documentation and the actual runtime code path (e.g.
``BaseProjectKeychain.create_scratch_org`` and
``ScratchOrgConfig._build_org_create_args``) treat it as a boolean.

This test demonstrates the bug from two angles:

1. The exported JSON schema must declare ``namespaced`` as ``boolean``.
2. The Pydantic model must preserve a YAML-style boolean rather than
   silently coercing it to the strings ``"True"``/``"False"``.

PR #3911 (OPEN as of 2026-05-14) fixes ``cumulusci_yml.py`` (changing
``namespaced: str = None`` to ``bool = None``) and the regenerated
``cumulusci.jsonschema.json``. Once that lands the assertions below
will all pass.
"""

import json
from pathlib import Path

import pytest

from cumulusci.utils.yaml.cumulusci_yml import ScratchOrg


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "cumulusci/schema/cumulusci.jsonschema.json"


def _scratch_org_namespaced_schema() -> dict:
    with SCHEMA_PATH.open() as fh:
        schema = json.load(fh)
    return schema["definitions"]["ScratchOrg"]["properties"]["namespaced"]


@pytest.mark.xfail(
    reason="repro for #3910 - see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_jsonschema_namespaced_is_boolean():
    assert _scratch_org_namespaced_schema()["type"] == "boolean"


@pytest.mark.xfail(
    reason="repro for #3910 - see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_pydantic_model_namespaced_is_boolean():
    schema = ScratchOrg.schema()
    assert schema["properties"]["namespaced"]["type"] == "boolean"


@pytest.mark.xfail(
    reason="repro for #3910 - see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_pydantic_does_not_stringify_boolean_namespaced():
    parsed = ScratchOrg.parse_obj({"namespaced": True})
    assert parsed.namespaced is True
    assert not isinstance(parsed.namespaced, str)


@pytest.mark.xfail(
    reason="repro for #3910 - see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_pydantic_does_not_stringify_boolean_namespaced_false():
    parsed = ScratchOrg.parse_obj({"namespaced": False})
    assert parsed.namespaced is False
    assert not isinstance(parsed.namespaced, str)
