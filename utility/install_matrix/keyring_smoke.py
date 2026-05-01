"""Keyring round-trip smoke test for the install matrix.

Imports keyring, writes a test value to a dedicated service/username pair,
reads it back, asserts equality, and cleans up. Exits non-zero on any failure.

This script does not import cumulusci. Its purpose is to prove the keyring
and cryptography wheels load and function on whichever python-build-standalone
interpreter uv selected for the tool install.
"""

from __future__ import annotations

import sys

SERVICE = "cumulusci-install-matrix-smoke"
USERNAME = "smoke-user"
VALUE = "smoke-value-42"


def main() -> int:
    try:
        import keyring
    except Exception as exc:
        print(f"FAIL: could not import keyring: {exc!r}", file=sys.stderr)
        return 1

    try:
        keyring.set_password(SERVICE, USERNAME, VALUE)
    except Exception as exc:
        print(f"FAIL: keyring.set_password raised: {exc!r}", file=sys.stderr)
        return 1

    try:
        got = keyring.get_password(SERVICE, USERNAME)
    except Exception as exc:
        print(f"FAIL: keyring.get_password raised: {exc!r}", file=sys.stderr)
        return 1

    if got != VALUE:
        print(
            f"FAIL: read-back mismatch: got={got!r} expected={VALUE!r}", file=sys.stderr
        )
        return 1

    try:
        keyring.delete_password(SERVICE, USERNAME)
    except Exception as exc:
        print(f"WARN: cleanup failed: {exc!r}", file=sys.stderr)

    print("OK: keyring round-trip succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
