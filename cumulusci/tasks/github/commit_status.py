# For backwards-compatibility
import cumulusci.tasks.vcs.commit_status as GetPackageDataFromCommitStatusTask
from cumulusci.utils.deprecation import warn_moved


class GetPackageDataFromCommitStatus(
    GetPackageDataFromCommitStatusTask.GetPackageDataFromCommitStatus
):
    """Deprecated: use cumulusci.tasks.vcs.commit_status.GetPackageDataFromCommitStatus instead"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        warn_moved("cumulusci.tasks.vcs.commit_status", __name__)
