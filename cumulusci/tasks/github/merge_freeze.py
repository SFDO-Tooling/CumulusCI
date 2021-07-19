from cumulusci.tasks.github.base import BaseGithubTask


class EnableMergeFreeze(BaseGithubTask):

    task_options = {
        "repos": {
            "description": (
                "The list of owner, repo key pairs for which to generate release notes."
                + " Ex: 'owner': SalesforceFoundation 'repo': 'NPSP'"
            ),
            "required": True,
        },
    }

    def _run_task(self):
        for project in self.options["repos"]:
            if project["owner"] and project["repo"]:
                self.logger.info(f'Enabling merge freeze on {project["owner"]}/{project["repo"]}')
                repo = self.github.repository(project["owner"], project["repo"])
                self._restrict_access_on_repo(repo)
                        
   def _restrict_access_on_repo(repo):
       '''Restricts access on a repo so that....'''
       repo.branch("main").protection().update(restrictions={"users": [], "teams": []})
