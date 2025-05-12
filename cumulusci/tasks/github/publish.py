# For backwards-compatibility
import cumulusci.tasks.vcs.publish as PublishSubtreeTask
from cumulusci.utils.deprecation import warn_moved


class PublishSubtree(PublishSubtreeTask.PublishSubtree):
    """Deprecated: use cumulusci.tasks.vcs.publish.PublishSubtree instead"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        warn_moved("cumulusci.tasks.vcs.publish", __name__)
