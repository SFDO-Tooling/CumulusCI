from cumulusci.core.github import get_github_api_for_repo
from cumulusci.core.tasks import BaseTask


class BaseGithubTask(BaseTask):
    def _init_task(self):
        super()._init_task()
        self.github_config = self.project_config.keychain.get_service("github")
        self.github = get_github_api_for_repo(
            self.project_config.keychain,
            self.project_config.repo_owner,
            self.project_config.repo_name,
        )

    def get_repo(self, owner=None,repo=None):
        if owner and repo:
            return self.github.repository(owner,repo)
        else:
            return self.github.repository(
                self.project_config.repo_owner, self.project_config.repo_name
            )
