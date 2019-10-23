from .github import GitHubSource
from .local_folder import LocalFolderSource


class NullSource:
    frozenspec = None


__all__ = ("GitHubSource", "LocalFolderSource", "NullSource")
