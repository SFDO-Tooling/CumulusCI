# For backwards-compatibility
import cumulusci.tasks.vcs as CreateReleaseTask
from cumulusci.utils.deprecation import warn_moved


class CreateRelease(CreateReleaseTask.CreateRelease):
    """Deprecated: use cumulusci.tasks.vcs.release.CreateRelease instead"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        warn_moved("cumulusci.tasks.vcs.release", __name__)
