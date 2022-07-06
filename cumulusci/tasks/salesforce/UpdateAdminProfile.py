# for backwards compatibility
from cumulusci.tasks.salesforce.update_profile import *  # noqa
from cumulusci.utils.deprecation import warn_moved

warn_moved(
    "cumulusci.tasks.salesforce.update_profile",
    __name__,
)
