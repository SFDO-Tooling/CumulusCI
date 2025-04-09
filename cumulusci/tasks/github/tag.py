from cumulusci.tasks.base_scm_task import BaseScmTask

class CloneTag(BaseScmTask):
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
        
        tag = self.create_tag()

        self.logger.info(f"Tag {self.options['tag']} created by cloning {src_tag_name}")

        return tag
