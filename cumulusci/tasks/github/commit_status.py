from cumulusci.core.exceptions import DependencyLookupError
from cumulusci.core.github import get_version_id_from_commit
from cumulusci.tasks.github.base import BaseGithubTask
from cumulusci.tasks.salesforce.BaseSalesforceApiTask import BaseSalesforceApiTask


class GetPackageDataFromCommitStatus(BaseGithubTask, BaseSalesforceApiTask):

    api_version = "50.0"

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
            version_id = get_version_id_from_commit(repo, commit_sha, context)

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
