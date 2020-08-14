from cumulusci.core.exceptions import DependencyLookupError
import re

from cumulusci.tasks.github.base import BaseGithubTask
from cumulusci.tasks.salesforce.BaseSalesforceApiTask import BaseSalesforceApiTask

VERSION_ID_RE = re.compile(r"version_id: (\S+)")


class GetPackageDataFromCommitStatus(BaseGithubTask, BaseSalesforceApiTask):

    task_options = {
        "context": {
            "description": "Name of the commit status context",
            "required": True,
        },
        "version_id": {"description": "Package version id"},
    }

    def _run_task(self):
        repo = self.get_repo()
        context = self.options["context"]
        commit_sha = self.project_config.repo_commit

        dependencies = []
        version_id = self.options.get("version_id")
        if version_id is None:
            for status in repo.commit(commit_sha).status().statuses:
                if status.state == "success" and status.context == context:
                    match = VERSION_ID_RE.search(status.description)
                    if match:
                        version_id = match.group(1)

        if version_id:
            res = self.tooling.query(
                f"SELECT Dependencies FROM SubscriberPackageVersion WHERE Id='{version_id}'"
            )
            if res["records"]:
                subscriber_version = res["records"][0]
                dependencies = [
                    {"version_id": d["subscriberPackageVersionId"]}
                    for d in subscriber_version["Dependencies"]["ids"]
                ]
        else:
            raise DependencyLookupError(
                f"Could not find package version id in '{context}' commit status."
            )

        self.return_values = {"dependencies": dependencies, "version_id": version_id}


class SetCommitStatus(BaseGithubTask):

    task_options = {
        "context": {"description": "Commit status context", "required": True},
        "state": {"description": "Commit status state", "required": True},
        "description": {"description": "Commit status description"},
        "target_url": {"description": "Commit status target URL"},
    }

    def _run_task(self):
        commit_sha = self.project_config.repo_commit
        context = self.options["context"]
        description = self.options.get("description")
        state = self.options["state"]
        target_url = self.options.get("target_url")

        repo = self.get_repo()
        repo.create_status(commit_sha, state, target_url, description, context)

        self.logger.info(f"Set commit status '{context}' to {state} for {commit_sha}")
