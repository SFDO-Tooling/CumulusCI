from cumulusci.tasks.github import (
    CloneTag,
    CreateRelease,
    GetPackageDataFromCommitStatus,
    MergeBranch,
    PublishSubtree,
    PullRequests,
    ReleaseReport,
)


class TestVCSMigration:
    def test_clone_tag(self):
        assert CloneTag.__module__ == "cumulusci.tasks.github.tag"
        assert CloneTag.__name__ == "CloneTag"

    def test_merge_branch(self):
        assert MergeBranch.__module__ == "cumulusci.tasks.github.merge"
        assert MergeBranch.__name__ == "MergeBranch"

    def test_get_package_data_from_commit_status(self):
        assert (
            GetPackageDataFromCommitStatus.__module__
            == "cumulusci.tasks.github.commit_status"
        )
        assert (
            GetPackageDataFromCommitStatus.__name__ == "GetPackageDataFromCommitStatus"
        )

    def test_publish_subtree(self):
        assert PublishSubtree.__module__ == "cumulusci.tasks.github.publish"
        assert PublishSubtree.__name__ == "PublishSubtree"

    def test_pull_requests(self):
        assert PullRequests.__module__ == "cumulusci.tasks.github.pull_request"
        assert PullRequests.__name__ == "PullRequests"

    def test_release(self):
        assert CreateRelease.__module__ == "cumulusci.tasks.github.release"
        assert CreateRelease.__name__ == "CreateRelease"

    def test_release_report(self):
        assert ReleaseReport.__module__ == "cumulusci.tasks.github.release_report"
        assert ReleaseReport.__name__ == "ReleaseReport"
