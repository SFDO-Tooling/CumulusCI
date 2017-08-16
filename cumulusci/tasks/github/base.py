from github3 import login

from cumulusci.core.exceptions import GithubException
from cumulusci.core.tasks import BaseTask
from cumulusci.core.utils import process_bool_arg

class BaseGithubTask(BaseTask):

    def _init_task(self):
        self.github_config = self.project_config.keychain.get_service('github')
        self.github = login(
            username=self.github_config.username,
            password=self.github_config.password,
        )

    def get_repo(self):
        return self.github.repository(
            self.project_config.repo_owner,
            self.project_config.repo_name,
        )
