from cumulusci.tasks.github import CloneTag, MergeBranch
from cumulusci.tasks.github.commit_status import GetPackageDataFromCommitStatus


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
