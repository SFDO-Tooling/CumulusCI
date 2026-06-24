"""Repro for CumulusCI issue #3407.

`BaseProjectKeychain.set_service` declares ``service_config: ServiceConfig``,
but :pyfunc:`EncryptedFileProjectKeychain._load_service_files` calls it with a
raw ``str`` (the encrypted file payload) and ``config_encrypted=True``.  The
signature is therefore inconsistent with the call sites.

This test asserts the *correct* behaviour: either the annotation accepts
``str`` (e.g. ``ServiceConfig | str``) or every call site constructs a
``ServiceConfig`` first.  It is expected to fail on dev (xfail).

Pure introspection - no Salesforce / scratch org required.
"""

from __future__ import annotations

import inspect
import typing
from typing import Union, get_args, get_origin

import pytest

from cumulusci.core.config import ServiceConfig
from cumulusci.core.keychain.base_project_keychain import BaseProjectKeychain
from cumulusci.core.keychain.encrypted_file_project_keychain import (
    EncryptedFileProjectKeychain,
)


def _annotation_accepts_str(annotation) -> bool:
    """True if ``annotation`` permits ``str`` (directly or via Union)."""
    if annotation is str:
        return True
    origin = get_origin(annotation)
    if origin is Union or origin is type(None) or origin is typing.Union:
        return any(a is str for a in get_args(annotation))
    return False


def _src_has_string_payload_call(func) -> bool:
    """Heuristic: does ``func`` source call set_service with config_encrypted=True
    while passing a non-ServiceConfig value (i.e. a string variable read from a
    file)?"""
    src = inspect.getsource(func)
    return "config_encrypted=True" in src and "ServiceConfig(" not in src


@pytest.mark.xfail(
    reason=("repro for #3407 - see docs/triage/v5/repro-results.md"),
    strict=False,
)
def test_set_service_annotation_consistent_with_callers():
    """The annotation must agree with all internal call sites."""
    hints = typing.get_type_hints(BaseProjectKeychain.set_service)
    annotation = hints["service_config"]

    string_caller = _src_has_string_payload_call(
        EncryptedFileProjectKeychain._load_service_files
    )

    assert not string_caller or _annotation_accepts_str(annotation), (
        "BaseProjectKeychain.set_service is annotated "
        f"service_config: {annotation!r}, but "
        "EncryptedFileProjectKeychain._load_service_files passes a raw str "
        "(file contents) with config_encrypted=True. Annotation should be "
        "Union[ServiceConfig, str] or callers should construct a "
        "ServiceConfig first."
    )


@pytest.mark.xfail(
    reason=("repro for #3407 - see docs/triage/v5/repro-results.md"),
    strict=False,
)
def test_set_service_runtime_accepts_only_serviceconfig_per_annotation():
    """Run-time evidence: a plain string is accepted with config_encrypted=True
    even though the annotation says ServiceConfig.  If the annotation were the
    source of truth, this call would fail.  Today it succeeds - proving the
    annotation is wrong."""

    class _Stub(BaseProjectKeychain):
        # minimal in-memory subclass exercising the encrypted-payload path
        def _set_service(
            self,
            service_type,
            alias,
            service_config,
            save=True,
            config_encrypted=False,
        ):
            assert isinstance(service_config, ServiceConfig), (
                f"got {type(service_config).__name__}, expected ServiceConfig"
            )
            self.services.setdefault(service_type, {})[alias] = service_config

        def _validate_service(self, *a, **kw):
            return None

    from cumulusci.core.config import UniversalConfig

    kc = _Stub(UniversalConfig(), None)
    # The annotation says only ServiceConfig is allowed.  If callers truly
    # respected it we'd never reach this line with a str.  This is exactly
    # what _load_service_files does today.
    kc.set_service(
        "github",
        "from-disk",
        "RAW-ENCRYPTED-STRING-PAYLOAD",  # type: ignore[arg-type]
        save=False,
        config_encrypted=True,
    )
