"""Regression repro for #3585.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (no_reverify_needed).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: When ``update_package_xml`` runs against an ``objects/``
folder where a ``.object`` file contains an element using the
``xsi:nil="true"`` shorthand without declaring ``xmlns:xsi``,
``PackageXmlGenerator`` invokes ``MetadataXmlElementParser`` parsers
(metadata_map.yml maps ``objects:`` to parsers for ListView,
CustomField, etc.) that call ``elementtree_parse_file``
(cumulusci/utils/xml/__init__.py:10), and Python's ``xml.etree``
raises ``ParseError: unbound prefix`` because ``xsi:`` is undeclared.

Salesforce's Metadata API often emits this shorthand, so users who
retrieve metadata and feed it back through ``update_package_xml`` hit
a hard failure they cannot fix by editing the file (it round-trips
this way).

The fix is to either (a) add an ``xmlns:xsi`` shim before parsing, or
(b) pre-strip ``xsi:nil`` attributes / use a tolerant lxml parser.

This test writes a tiny ``objects/Foo__c.object`` with an unbound
``xsi:nil`` attribute and asserts ``PackageXmlGenerator`` does not
raise; on dev it fails with an ``unbound prefix`` parse error.
"""

import os
import tempfile

import pytest

from cumulusci.tasks.metadata.package import PackageXmlGenerator


XSI_NIL_OBJECT = """<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <customTabListAdditionalFields xsi:nil="true"/>
    <listViews>
        <fullName>All</fullName>
        <label>All</label>
    </listViews>
</CustomObject>
"""


@pytest.mark.xfail(
    reason="repro for #3585 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3585():
    with tempfile.TemporaryDirectory() as tmp:
        objects_dir = os.path.join(tmp, "objects")
        os.makedirs(objects_dir)
        with open(os.path.join(objects_dir, "Foo__c.object"), "w") as f:
            f.write(XSI_NIL_OBJECT)

        gen = PackageXmlGenerator(directory=tmp, api_version="58.0")

        raised = None
        try:
            gen()
        except BaseException as e:
            raised = e

        msg = str(raised) if raised else ""
        is_unbound = raised is not None and (
            "unbound prefix" in msg or "not well-formed" in msg or "xsi" in msg
        )
        assert not is_unbound, (
            f"PackageXmlGenerator still raises XML parse error on .object files "
            f"using unbound xsi:nil; got: {raised!r}"
        )
