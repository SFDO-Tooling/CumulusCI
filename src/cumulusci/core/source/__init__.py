from .github import GitHubSource
from .local_folder import LocalFolderSource


class NullSource:
    frozenspec = None

    def __str__(self):
        return "current folder"


__all__ = ("GitHubSource", "LocalFolderSource", "NullSource")
