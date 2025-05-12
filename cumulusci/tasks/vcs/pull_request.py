from cumulusci.tasks.base_source_control_task import BaseSourceControlTask
from cumulusci.vcs.models import AbstractRepo


class PullRequests(BaseSourceControlTask):
    def _run_task(self):
        repo: AbstractRepo = self.get_repo()
        for pr in repo.pull_requests(state="open"):
            self.logger.info("#{}: {}".format(pr.number, pr.title))
