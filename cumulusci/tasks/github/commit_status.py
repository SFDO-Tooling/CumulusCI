from cumulusci.core.exceptions import DependencyLookupError
import re

import github3

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
            try:
                commit = repo.commit(commit_sha)
            except github3.exceptions.NotFoundError:
                raise DependencyLookupError(
                    f"Could not find commit {commit_sha} on github"
                )
            for status in commit.status().statuses:
                if status.state == "success" and status.context == context:
                    match = VERSION_ID_RE.search(status.description)
                    if match:
                        version_id = match.group(1)

        if version_id:
            dependencies = self._get_dependencies(version_id)
        else:
            raise DependencyLookupError(
                f"Could not find package version id in '{context}' commit status."
            )

        self.return_values = {"dependencies": dependencies, "version_id": version_id}

    def _get_dependencies(self, version_id):
        res = self.tooling.query(
            f"SELECT Dependencies FROM SubscriberPackageVersion WHERE Id='{version_id}'"
        )
        if res["records"]:
            subscriber_version = res["records"][0]
            dependencies = subscriber_version["Dependencies"] or {"ids": []}
            dependencies = [
                {"version_id": d["subscriberPackageVersionId"]}
                for d in dependencies["ids"]
            ]
            return dependencies
        else:
            raise DependencyLookupError(
                f"Could not look up dependencies of {version_id}"
            )
