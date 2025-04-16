# Q: get_github_api_for_repo can be part of this module itself!
from cumulusci.core.github import get_github_api_for_repo

from ..source_interface.github.repository import RepositoryAdapter
from .provider import SourceControlProvider


class GitHubProvider(SourceControlProvider):

    _repo: RepositoryAdapter

    def __init__(self, project_config: str):
        self.project_config = project_config
        self.github = get_github_api_for_repo(
            project_config.keychain, project_config.repo_url
        )
        self._repo = None

    @property
    def repo(self):
        return self._repo

    @repo.setter
    def repo(self, repo):
        self._repo = repo

    def get_repository(self) -> RepositoryAdapter:
        if self.repo is None:
            self.repo = RepositoryAdapter(self.github, self.project_config)
        return self.repo
