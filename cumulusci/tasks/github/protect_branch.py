from cumulusci.tasks.github.base import BaseGithubTask


class ProtectBranch(BaseGithubTask):
    def _run_task(self):
        repo = self.get_repo()
        branches = repo.add_collaborator(username="")
        print(branches)
        # for branch in branches:
        #     if branch._json_data["name"] == "master":
        #         branch
        # for branch in branches:
        #     print(branch)
        # for pr in repo.pull_requests(state="open"):
        #     self.logger.info("#{}: {}".format(pr.number, pr.title))

