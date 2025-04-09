from datetime import datetime

import cumulusci.core.github as scm
from cumulusci.core.tasks import BaseTask

class BaseGithubTask(BaseTask):
    def _init_task(self):
        super()._init_task()
        self.github_config = self.project_config.keychain.get_service("github")
        self.github = scm.get_github_api_for_repo(
            self.project_config.keychain, self.project_config.repo_url
        )

    def get_repo(self):
        return self.github.repository(
            self.project_config.repo_owner, self.project_config.repo_name
        )
        
    def get_tag_by_name(self, repo, src_tag_name):
        return scm.get_tag_by_name(repo, src_tag_name)
        
    def create_tag(self):
        src_tag_name = self.options["src_tag"]
        repo = self.get_repo()
        src_tag = self.get_tag_by_name(repo, src_tag_name)
        tag = repo.create_tag(
            tag=self.options["tag"],
            message=f"Cloned from {src_tag_name}",
            sha=src_tag.sha,
            obj_type="commit",
            tagger={
                "name": self.github_config.username,
                "email": self.github_config.email,
                "date": f"{datetime.utcnow().isoformat()}Z",
            },
        )
        return tag
