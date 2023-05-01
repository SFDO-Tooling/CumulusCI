# for backwards compatibility
from cumulusci.tasks.preflight.licenses import *  # noqa
from cumulusci.utils.deprecation import warn_moved

warn_moved(
    "cumulusci.tasks.preflight.licenses",
    __name__,
)
