from datetime import datetime

import github3.exceptions

from cumulusci.core.exceptions import GithubException
from cumulusci.tasks.github.base import BaseGithubTask


class CloneTag(BaseGithubTask):

    task_options = {
        "src_tag": {
            "description": "The source tag to clone.  Ex: beta/1.0-Beta_2",
            "required": True,
        },
        "tag": {
            "description": "The new tag to create by cloning the src tag.  Ex: release/1.0",
            "required": True,
        },
    }

    def _run_task(self):
        src_tag_name = self.options["src_tag"]
        repo = self.get_repo()
        ref = repo.ref(f"tags/{src_tag_name}")
        try:
            src_tag = repo.tag(ref.object.sha)
        except github3.exceptions.NotFoundError:
            message = f"Tag {src_tag_name} not found"
            self.logger.error(message)
            raise GithubException(message)

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
        self.logger.info(f"Tag {self.options['tag']} created by cloning {src_tag_name}")

        return tag
