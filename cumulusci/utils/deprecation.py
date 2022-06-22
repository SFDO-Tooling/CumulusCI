import os
from warnings import warn


def warn_moved(new, old):
    msg = f"Deprecation warning: Please import from {new} rather than {old}"

    # this is a hard-error if encountered in testing context
    if "PYTEST_CURRENT_TEST" in os.environ:
        assert 0, msg

    # otherwise warning
    warn(msg)
