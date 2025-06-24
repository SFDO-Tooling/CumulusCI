# For backwards-compatibility
import cumulusci.tasks.vcs.merge as MergeTask
from cumulusci.utils.deprecation import warn_moved


class MergeBranch(MergeTask.MergeBranch):
    """Deprecated: use cumulusci.tasks.vcs.merge.MergeBranch instead"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        warn_moved("cumulusci.tasks.vcs.merge", __name__)
