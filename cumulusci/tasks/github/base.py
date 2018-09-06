from cumulusci.core.github import get_github_api
from cumulusci.core.tasks import BaseTask


class BaseGithubTask(BaseTask):
    def _init_task(self):
        self.github_config = self.project_config.keychain.get_service("github")
        self.github = get_github_api(
            username=self.github_config.username, password=self.github_config.password
        )

    def get_repo(self):
        return self.github.repository(
            self.project_config.repo_owner, self.project_config.repo_name
        )
