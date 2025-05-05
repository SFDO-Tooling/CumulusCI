# For backwards-compatibility
import cumulusci.tasks.vcs.tag as CloneTagTask
from cumulusci.utils.deprecation import warn_moved


class CloneTag(CloneTagTask.CloneTag):
    """Deprecated: use cumulusci.tasks.vcs.tag.CloneTag instead"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        warn_moved("cumulusci.tasks.vcs.tag", __name__)
