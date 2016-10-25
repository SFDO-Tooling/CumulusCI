from github3 import login
from cumulusci.core.tasks import BaseTask

class BaseGithubTask(BaseTask):

    def _init_task(self):
        github_config = self.project_config.keychain.get_github()
        self.github = login(
            username=github_config.username,
            password=github_config.password,
        )

    def get_repo(self):
        return self.github.repository(
            self.project_config.repo_owner,
            self.project_config.repo_name,
        )

class PullRequests(BaseGithubTask):
    
    def _run_task(self):
        repo = self.get_repo()
        for pr in repo.iter_pulls(state='open'):
            self.logger.info('#{}: {}'.format(pr.number, pr.title))
    
