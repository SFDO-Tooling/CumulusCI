"""Repro for SFDO-Tooling/CumulusCI#773 — Document task return values and results.

cdcarter requested that tasks be able to *declare* their ``return_values``
(and ``result``) and that ``cci task info`` / the web docs surface that
declaration.

On ``origin/dev`` (1925a3083):

* ``BaseTask`` exposes a ``task_options`` class attribute that
  ``doc_task()`` walks (``cumulusci/utils/__init__.py:doc_task``) to emit
  an "Options" section.
* ``BaseTask`` exposes a free-form ``task_docs`` string that ``doc_task``
  splices into the output.
* There is **no** declarative analogue for return values: ``self.return_values``
  is an empty dict mutated at runtime, and ``doc_task`` never emits a
  "Return Values" / "Returns" section.

This test pins down the gap by running ``doc_task`` against a task that
sets ``return_values`` at runtime and asserting the rendered RST advertises
those return values. That assertion fails today because the task-info
plumbing has no awareness of return values. Mark xfail until a declarative
schema (e.g. ``return_values_schema``) and matching ``doc_task`` section
are added.
"""

from __future__ import annotations

import pytest

from cumulusci.core.config import BaseProjectConfig, TaskConfig, UniversalConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.tasks.salesforce.package_upload import PackageUpload
from cumulusci.utils import doc_task


def _make_task_config():
    """Build a minimal TaskConfig pointing at PackageUpload — a real shipping
    task that documents (in its docstring / source) that it populates
    ``return_values`` with ``version_number``, ``version_id``, and ``package_id``.
    """
    universal_config = UniversalConfig()
    project_config = BaseProjectConfig(universal_config, config={"noyaml": True})
    project_config.set_keychain(BaseProjectKeychain(project_config, key=None))
    task_config = TaskConfig(
        {
            "class_path": f"{PackageUpload.__module__}.{PackageUpload.__name__}",
            "description": "Uploads a beta release of the metadata currently in the packaging org",
            "options": {},
        }
    )
    return task_config


@pytest.mark.xfail(
    reason="repro for #773 — see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_doc_task_renders_return_values_section():
    """``cci task info`` (via ``doc_task``) should document a task's
    declared return values. Today no declarative mechanism exists, so the
    rendered RST has no "Return Values" section even for tasks whose
    implementation clearly populates ``self.return_values``.
    """
    rendered = doc_task("upload_beta", _make_task_config())

    assert "Return Values" in rendered or "Returns" in rendered, (
        "doc_task output should include a 'Return Values' (or 'Returns') "
        "section sourced from a declarative attribute on the task class "
        "(parallel to task_options / task_docs)."
    )
    for key in ("version_number", "version_id", "package_id"):
        assert key in rendered, (
            f"doc_task output should mention the {key!r} return value populated "
            f"by PackageUpload._set_return_values()."
        )
