from cumulusci.tasks.github import (
    CloneTag,
    GetPackageDataFromCommitStatus,
    MergeBranch,
    PublishSubtree,
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
