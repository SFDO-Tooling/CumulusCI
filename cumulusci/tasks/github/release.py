import json
import time
from datetime import datetime

import github3.exceptions
from github3.repos.repo import Repository

from cumulusci.core.dependencies.dependencies import parse_dependencies
from cumulusci.core.dependencies.resolvers import get_static_dependencies
from cumulusci.core.exceptions import GithubException, TaskOptionsError
from cumulusci.core.github import get_commit
from cumulusci.tasks.github.base import BaseGithubTask


class CreateRelease(BaseGithubTask):

    task_options = {
        "version": {
            "description": "The managed package version number.  Ex: 1.2",
            "required": True,
        },
        "version_id": {
            "description": "The SubscriberPackageVersionId (04t) associated with this release.",
            "required": False,
        },
        "message": {"description": "The message to attach to the created git tag"},
        "dependencies": {
            "description": "List of dependencies to record in the tag message."
        },
        "commit": {
            "description": (
                "Override the commit used to create the release. "
                "Defaults to the current local HEAD commit"
            )
        },
        "resolution_strategy": {
            "description": "The name of a sequence of resolution_strategy (from project__dependency_resolutions) to apply to dynamic dependencies. Defaults to 'production'."
        },
        "package_type": {
            "description": "The package type of the project (either 1GP or 2GP)",
            "required": True,
        },
        "tag_prefix": {
            "description": "The prefix to use for the release tag created in github.",
            "required": True,
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        self.commit = self.options.get("commit", self.project_config.repo_commit)
        if not self.commit:
            message = "Could not detect the current commit from the local repo"
            self.logger.error(message)
            raise GithubException(message)
        if len(self.commit) != 40:
            raise TaskOptionsError("The commit option must be exactly 40 characters.")

    def _run_task(self):
        repo = self.get_repo()
        version = self.options["version"]
        tag_prefix = self.options.get("tag_prefix")
        tag_name = self.project_config.get_tag_for_version(tag_prefix, version)

        self._verify_release(repo, tag_name)
        self._verify_commit(repo)

        # Build tag message
        message = self.options.get("message", "Release of version {}".format(version))
        if self.options.get("version_id"):
            message += f"\n\nversion_id: {self.options['version_id']}"
        if self.options.get("package_type"):
            message += f"\n\npackage_type: {self.options['package_type']}"
        dependencies = get_static_dependencies(
            self.project_config,
            dependencies=parse_dependencies(
                self.options.get("dependencies")
                or self.project_config.project__dependencies,
            ),
            resolution_strategy=self.options.get("resolution_strategy") or "production",
        )
        if dependencies:
            dependencies = [d.dict(exclude_none=True) for d in dependencies]
            message += "\n\ndependencies: {}".format(json.dumps(dependencies, indent=4))

        try:
            repo.ref(f"tags/{tag_name}")
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
                    "date": f"{datetime.utcnow().isoformat()}Z",
                },
                lightweight=False,
            )

            # Sleep for Github to catch up with the fact that the tag actually exists!
            time.sleep(3)

        prerelease = tag_name.startswith(self.project_config.project__git__prefix_beta)

        # Create the Github Release
        release = repo.create_release(
            tag_name=tag_name, name=version, prerelease=prerelease
        )
        self.return_values = {
            "tag_name": tag_name,
            "name": version,
            "dependencies": dependencies,
        }
        self.logger.info(f"Created release {release.name} at {release.html_url}")

    def _verify_release(self, repo: Repository, tag_name: str) -> None:
        """Make sure release doesn't already exist"""
        try:
            release = repo.release_from_tag(tag_name)
        except github3.exceptions.NotFoundError:
            pass
        else:
            message = f"Release {release.name} already exists at {release.html_url}"
            self.logger.error(message)
            raise GithubException(message)

    def _verify_commit(self, repo: Repository) -> None:
        """Verify that the commit exists on the remote."""
        get_commit(repo, self.commit)
