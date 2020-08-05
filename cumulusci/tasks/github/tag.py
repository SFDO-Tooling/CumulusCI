from datetime import datetime
import json
import re

import github3.exceptions

from cumulusci.core.exceptions import GithubException
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.github.base import BaseGithubTask
from cumulusci.tasks.github.util import build_package_tag_message


class CreateTag(BaseGithubTask):

    task_options = {
        "tag": {"description": "The tag to create", "required": True},
        "message": {"description": "The message to attach to the git tag"},
        "dependencies": {
            "description": "List of dependencies to record in the tag message."
        },
        "version_id": {
            "description": "Package version id to record in the tag message."
        },
        "commit": {
            "description": (
                "Override the commit used to create the release. "
                "Defaults to the current local HEAD commit"
            )
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        self.commit = self.options.get("commit", self.project_config.repo_commit)
        if not self.commit:
            message = "Could not detect the current commit from the local repo"
            raise GithubException(message)
        if len(self.commit) != 40:
            raise TaskOptionsError("The commit option must be exactly 40 characters.")

    def _run_task(self):
        repo = self.get_repo()
        tag_name = self.options["tag"]
        message = build_package_tag_message(self.options)

        try:
            repo.ref("tags/{}".format(tag_name))
        except github3.exceptions.NotFoundError:
            # Create the annotated tag
            repo.create_tag(
                tag=tag_name,
                message=message,
                sha=self.commit,
                obj_type="commit",
                tagger={
                    "name": self.github_config.username,
                    "email": self.github_config.email,
                    "date": "{}Z".format(datetime.utcnow().isoformat()),
                },
                lightweight=False,
            )

        self.logger.info(f"Created tag {tag_name}")


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
        repo = self.get_repo()
        ref = repo.ref("tags/{}".format(self.options["src_tag"]))
        try:
            src_tag = repo.tag(ref.object.sha)
        except github3.exceptions.NotFoundError:
            message = "Tag {} not found".format(self.options["src_tag"])
            self.logger.error(message)
            raise GithubException(message)

        tag = repo.create_tag(
            tag=self.options["tag"],
            message="Cloned from {}".format(self.options["src_tag"]),
            sha=src_tag.sha,
            obj_type="commit",
            tagger={
                "name": self.github_config.username,
                "email": self.github_config.email,
                "date": "{}Z".format(datetime.utcnow().isoformat()),
            },
        )
        self.logger.info(
            "Tag {} created by cloning {}".format(
                self.options["tag"], self.options["src_tag"]
            )
        )

        return tag


class GetTagData(BaseGithubTask):
    DATA_RE = re.compile(r"^data: (\{.*\})$", re.M | re.S)

    task_options = {"tag": {"description": "Tag name", "required": True}}

    def _run_task(self):
        repo = self.get_repo()
        tag_name = self.options["tag"]
        ref = repo.ref(f"tags/{tag_name}")
        tag = repo.tag(ref.object.sha)
        data = {}
        match = self.DATA_RE.search(tag.message)
        if match:
            data = json.loads(match.group(1))
        self.return_values = data
