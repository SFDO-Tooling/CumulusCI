import os
import shutil
from datetime import datetime
import github3.exceptions

from cumulusci.core.exceptions import GithubException
from cumulusci.core.github import get_github_api_for_repo
from cumulusci.core.utils import process_bool_arg
from cumulusci.core.utils import process_list_arg
from cumulusci.tasks.github.base import BaseGithubTask
from cumulusci.tasks.github.util import CommitDir
from cumulusci.utils import cd
from cumulusci.utils import download_extract_github_from_repo
from cumulusci.utils import temporary_dir


class PublishRelease(BaseGithubTask):
    task_options = {
        "repo_url": {"description": "The url to the public repo", "required": True,},
        "branch": {
            "description": "The branch to update in the target repo",
            "required": True,
        },
        "version": {
            "description": "The version number to release.  Also supports latest and latest_beta to look up the latest releases.",
            "required": True,
        },
        "exclude": {"description": "A list of paths from repo root to exclude",},
        "release_body": {
            "description": "If True, the entire release body will be published to the public repo.  Defaults to False",
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.options["exclude"] = process_list_arg(self.options.get("exclude", []))
        self.options["release_body"] = process_bool_arg(
            self.options.get("release_body", False)
        )
        if self.options["version"] == "latest":
            self.options["version"] = str(self.project_config.get_latest_version())
        elif self.options["version"] == "latest_beta":
            self.options["version"] = str(
                self.project_config.get_latest_version(beta=True)
            )

    def _get_target_repo_api(self):
        gh = self.project_config.get_github_api(
            self._target_repo_info["owner"], self._target_repo_info["name"],
        )
        return gh.repository(
            self._target_repo_info["owner"], self._target_repo_info["name"],
        )

    def _run_task(self):
        self._target_repo_info = self.project_config._split_repo_url(
            self.options["repo_url"]
        )
        self.target_repo = self._get_target_repo_api()

        with temporary_dir(chdir=False) as target:
            self._download_repo(target)
            self._exclude_files(target)
            commit = self._create_commit(target)
            self._create_release(target, commit)

    def _download_repo(self, path):
        zf = download_extract_github_from_repo(
            self.get_repo(),
            ref="tags/{}".format(
                self.project_config.get_tag_for_version(self.options["version"])
            ),
        )
        with cd(path):
            zf.extractall()

    def _exclude_files(self, path):
        with cd(path):
            for path in self.options["exclude"]:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                elif os.path.isfile(path):
                    os.remove(path)

    def _create_commit(self, path):
        committer = CommitDir(self.target_repo)
        message = f"Publishing release {self.options['version']}"
        commit = committer(path, self.options["branch"], commit_message=message)
        return commit.sha

    def _create_release(self, path, commit):
        # Get current release info
        tag_name = self.project_config.get_tag_for_version(self.options["version"])
        repo = self.get_repo()
        # Get the ref
        try:
            ref = repo.ref(f"tags/{tag_name}")
        except github3.exceptions.NotFoundError:
            message = f"Ref not found for tag {tag_name}"
            self.logger.error(message)
            raise GithubException(message)
        # Get the tag
        try:
            tag = repo.tag(ref.object.sha)
        except github3.exceptions.NotFoundError:
            message = f"Tag {tag_name} not found"
            self.logger.error(message)
            raise GithubException(message)
        # Get the release
        try:
            release = repo.release_from_tag(tag_name)
        except github3.exceptions.NotFoundError:
            message = f"Release for {tag_name} not found"
            self.logger.error(message)
            raise GithubException(message)

        # Check for tag in target repo
        target_ref = None
        try:
            target_ref = self.target_repo.ref(f"tags/{tag_name}")
        except github3.exceptions.NotFoundError:
            pass
        if target_ref:
            message = "Ref for tag {tag_name} already exists in target repo"
            raise GithubException(message)

        # Create the tag
        target_tag = self.target_repo.create_tag(
            tag=tag_name,
            message=tag.message,
            sha=commit,
            obj_type="commit",
            tagger={
                "name": self.github_config.username,
                "email": self.github_config.email,
                "date": "{}Z".format(datetime.utcnow().isoformat()),
            },
            lightweight=False,
        )

        # Create the release
        body = release.body if self.options["release_body"] else ""
        target_release = self.target_repo.create_release(
            tag_name=tag_name,
            name=self.options["version"],
            prerelease=release.prerelease,
        )

