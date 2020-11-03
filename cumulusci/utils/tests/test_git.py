from pathlib import Path
from tempfile import TemporaryDirectory

from cumulusci.utils.git import git_path, current_branch


class TestGitUtils:
    def test_git_path(self):
        with TemporaryDirectory() as d:
            (Path(d) / ".git").mkdir()

            assert git_path(d, "HEAD") == (Path(d) / ".git" / "HEAD")

    def test_git_path__no_dot_git(self):
        with TemporaryDirectory() as d:
            assert git_path(d, "HEAD") == None

    def test_current_branch(self):
        with TemporaryDirectory() as d:
            (Path(d) / ".git").mkdir()
            (Path(d) / ".git" / "HEAD").write_text("ref: refs/heads/feature/test")

            assert current_branch(d) == "feature/test"
