# For backwards-compatibility
import cumulusci.tasks.vcs.tag as CloneTagTask
from cumulusci.utils.deprecation import warn_moved

warn_moved(
    "cumulusci.tasks.vcs.tag",
    __name__,
)

CloneTag = CloneTagTask.CloneTag
