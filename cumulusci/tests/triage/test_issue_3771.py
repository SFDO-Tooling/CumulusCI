"""Regression repro for #3771.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: `transform_xpath()` defined inline in
`FindReplaceTransform.process()` (cumulusci/core/source_transforms/
transforms.py:417-432) splits the user XPath on `/`, wraps each
plain tag in `*[local-name()="<tag>"]`, and re-appends the
predicate verbatim. Tags referenced INSIDE the predicate (e.g.
`price` inside `[price>40]`) keep their default namespace
binding, so on documents with a default xmlns the XPath
predicate matches nothing. PR #3772 (leboff's namespace fix) is
not merged.

We exercise transform_xpath by importing it via inline grab
(it's a closure inside `process`) - instead we just inspect the
source and assert that predicate-internal tags are also wrapped
with `local-name()` (or some equivalent namespace-stripping
machinery). On dev they are not -> XFAIL.
"""

import inspect

import pytest

from cumulusci.core.source_transforms.transforms import FindReplaceTransform


@pytest.mark.xfail(
    reason="repro for #3771 - see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_issue_3771():
    src = inspect.getsource(FindReplaceTransform.process)
    has_predicate_ns_handling = any(
        token in src
        for token in (
            "transform_predicate",
            "predicate_local_name",
            "strip_namespace",
            "register_namespace",
            "xmlns",
        )
    )
    assert has_predicate_ns_handling, (
        "transform_xpath() in FindReplaceTransform still wraps only the "
        "tag name with local-name(); predicate-internal references stay "
        "namespace-bound and never match xmlns'd documents (see #3771)."
    )
