from cumulusci.tasks.base_source_control_task import BaseSourceControlTask


class CreatePackageDataFromCommitStatus(BaseSourceControlTask):
    task_options = {
        "state": {
            "description": "sha of the commit",
            "required": True,
        },
        "context": {
            "description": "Name of the commit status context",
            "required": True,
        },
        "commit_id": {
            "description": "sha of the commit",
        },
        "description": {
            "description": "Description of the commit status",
        },
        "target_url": {
            "description": "URL to associate with the commit status",
        },
    }

    def _run_task(self):
        repo = self.get_repo()
        commit_sha = self.options["commit_id"] or self.project_config.repo_commit or ""

        commit = repo.create_commit_status(
            commit_sha,
            state=self.options["state"],
            context=self.options["context"],
            description=self.options.get("description"),
            target_url=self.options.get("target_url"),
        )

        self.return_values = {"commit_id": commit.sha}
