from cumulusci.tasks.github.merge import MergeBranch
from cumulusci.tasks.github.pull_request import PullRequests
from cumulusci.tasks.github.release import CreateRelease
from cumulusci.tasks.github.release_report import ReleaseReport
from cumulusci.tasks.github.tag import CloneTag


__all__ = ("MergeBranch", "PullRequests", "CreateRelease", "ReleaseReport", "CloneTag")
