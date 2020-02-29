import json
import time
from datetime import datetime

import github3.exceptions

from cumulusci.core.exceptions import GithubException
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.github.base import BaseGithubTask


class CreateRelease(BaseGithubTask):

    task_options = {
        "version": {
            "description": "The managed package version number.  Ex: 1.2",
            "required": True,
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
        tag_name = self.project_config.get_tag_for_version(version)

        # Make sure release doesn't already exist
        try:
            release = repo.release_from_tag(tag_name)
        except github3.exceptions.NotFoundError:
            pass
        else:
            message = "Release {} already exists at {}".format(
                release.name, release.html_url
            )
            self.logger.error(message)
            raise GithubException(message)

        # Build tag message
        message = self.options.get("message", "Release of version {}".format(version))
        dependencies = self.project_config.get_static_dependencies(
            self.options.get("dependencies")
            or self.project_config.project__dependencies
        )
        if dependencies:
            message += "\n\ndependencies: {}".format(json.dumps(dependencies, indent=4))

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

            # Sleep for Github to catch up with the fact that the tag actually exists!
            time.sleep(3)

        prerelease = "Beta" in version

        # Create the Github Release
        release = repo.create_release(
            tag_name=tag_name, name=version, prerelease=prerelease
        )
        self.return_values = {
            "tag_name": tag_name,
            "name": version,
            "dependencies": dependencies,
        }
        self.logger.info(
            "Created release {} at {}".format(release.name, release.html_url)
        )
