from cumulusci.tasks.base_source_control_task import BaseSourceControlTask
from cumulusci.vcs.bootstrap import get_tag_by_name
from cumulusci.vcs.models import AbstractGitTag, AbstractRepo


class CloneTag(BaseSourceControlTask):
    task_options = {  # TODO: should use `class Options instead`
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
        repo: AbstractRepo = self.get_repo()
        src_tag: AbstractGitTag = get_tag_by_name(repo, src_tag_name)

        tag: AbstractGitTag = repo.create_tag(
            tag_name=self.options["tag"],
            message=f"Cloned from {src_tag_name}",
            sha=src_tag.sha,
            obj_type="commit",
        )
        self.logger.info(f"Tag {self.options['tag']} created by cloning {src_tag_name}")

        return tag
