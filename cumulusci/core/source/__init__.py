from .github import GitHubSource, GitHubEnterpriseSource
from .local_folder import LocalFolderSource


class NullSource:
    """Source for the root project."""

    frozenspec = None
    allow_remote_code = True
    location = None

    def __str__(self):
        return "current folder"


__all__ = ("GitHubSource", "GitHubEnterpriseSource", "LocalFolderSource", "NullSource")
