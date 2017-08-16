from cumulusci.tasks.github.base import BaseGithubTask

class PullRequests(BaseGithubTask):
    
    def _run_task(self):
        repo = self.get_repo()
        for pr in repo.iter_pulls(state='open'):
            self.logger.info('#{}: {}'.format(pr.number, pr.title))
