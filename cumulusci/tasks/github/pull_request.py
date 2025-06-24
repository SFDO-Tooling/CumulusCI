# For backwards-compatibility
import cumulusci.tasks.vcs.pull_request as PullRequestsTask
from cumulusci.utils.deprecation import warn_moved


class PullRequests(PullRequestsTask.PullRequests):
    """Deprecated: use cumulusci.tasks.vcs.pull_request.PullRequests instead"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        warn_moved("cumulusci.tasks.vcs.pull_request", __name__)
