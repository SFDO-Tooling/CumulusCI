import time
from datetime import datetime

import github3.exceptions

from cumulusci.core.exceptions import GithubException
from cumulusci.tasks.github.base import BaseGithubTask


class CreateRelease(BaseGithubTask):

    task_options = {
        "version": {
            "description": "The managed package version number.  Ex: 1.2",
            "required": True,
        },
        "message": {"description": "The message to attach to the created git tag"},
        "commit": {
            "description": "Override the commit used to create the release.  Defaults to the current local HEAD commit"
        },
    }

    def _run_task(self):
        repo = self.get_repo()

        version = self.options["version"]
        self.tag_name = self.project_config.get_tag_for_version(version)

        for release in repo.releases():
            if release.tag_name == self.tag_name:
                message = "Release {} already exists at {}".format(
                    release.name, release.html_url
                )
                self.logger.error(message)
                raise GithubException(message)

        commit = self.options.get("commit", self.project_config.repo_commit)
        if not commit:
            message = "Could not detect the current commit from the local repo"
            self.logger.error(message)
            raise GithubException(message)

        try:
            ref = repo.ref("tags/{}".format(self.tag_name))
        except github3.exceptions.NotFoundError:
            # Create the annotated tag
            tag = repo.create_tag(
                tag=self.tag_name,
                message="Release of version {}".format(version),
                sha=commit,
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
            tag_name=self.tag_name, name=version, prerelease=prerelease
        )
        self.return_values = {"tag_name": self.tag_name, "name": version}
        self.logger.info(
            "Created release {} at {}".format(release.name, release.html_url)
        )
