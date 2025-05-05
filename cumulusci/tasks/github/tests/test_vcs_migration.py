from cumulusci.tasks.github import CloneTag, MergeBranch


class TestVCSMigration:
    def test_clone_tag(self):
        assert CloneTag.__module__ == "cumulusci.tasks.github.tag"
        assert CloneTag.__name__ == "CloneTag"

    def test_merge_branch(self):
        assert MergeBranch.__module__ == "cumulusci.tasks.github.merge"
        assert MergeBranch.__name__ == "MergeBranch"
