# For backwards-compatibility
import cumulusci.tasks.vcs.release_report as ReleaseReportTask
from cumulusci.utils.deprecation import warn_moved


class ReleaseReport(ReleaseReportTask.ReleaseReport):
    """Deprecated: use cumulusci.tasks.vcs.release_report.ReleaseReport instead"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        warn_moved("cumulusci.tasks.vcs.release_report", __name__)
