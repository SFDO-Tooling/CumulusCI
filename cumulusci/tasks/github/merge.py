# For backwards-compatibility
import cumulusci.tasks.vcs.merge as MergeTask
from cumulusci.utils.deprecation import warn_moved

warn_moved(
    "cumulusci.tasks.vcs.merge",
    __name__,
)

MergeBranch = MergeTask.MergeBranch
