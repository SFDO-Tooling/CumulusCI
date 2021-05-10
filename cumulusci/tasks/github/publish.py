from cumulusci.utils.git import split_repo_url
import tempfile
from datetime import datetime
from pathlib import Path

import github3.exceptions
from cumulusci.core.exceptions import GithubException, TaskOptionsError
from cumulusci.core.utils import process_bool_arg, process_list_arg
from cumulusci.tasks.github.base import BaseGithubTask
from cumulusci.tasks.github.util import CommitDir
from cumulusci.utils import download_extract_github_from_repo


class PublishSubtree(BaseGithubTask):
    task_options = {
        "repo_url": {"description": "The url to the public repo", "required": True},
        "branch": {
            "description": "The branch to update in the target repo",
            "required": True,
        },
        "version": {
            "description": "The version number to release. "
            "Also supports latest and latest_beta to look up the latest releases. "
            "Required if 'ref' is not set."
        },
        "ref": {
            "description": "The git reference to publish.  Takes precedence over 'version'."
        },
        "include": {
            "description": "A list of paths from repo root to include. Directories must end with a trailing slash."
        },
        "renames": {
            "description": "A list of paths to rename in the target repo, given as `local:` `target:` pairs."
        },
        "create_release": {
            "description": "If True, create a release in the public repo.  Defaults to False"
        },
        "release_body": {
            "description": "If True, the entire release body will be published to the public repo.  Defaults to False"
        },
        "dry_run": {
            "description": "If True, skip creating Github data.  Defaults to False"
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.options["include"] = process_list_arg(
            self.options.get(
                "include", ["datasets/", "documentation/", "tasks/", "unpackaged/"]
            )
        )

        self.options["renames"] = self._process_renames(self.options.get("renames", []))

        if self.options.get("version") in ("latest", "latest_beta"):
            get_beta = self.options["version"] == "latest_beta"
            self.options["version"] = str(
                self.project_config.get_latest_version(beta=get_beta)
            )
        if "ref" not in self.options and "version" not in self.options:
            raise TaskOptionsError("Either `ref` or `version` option is required")

        self.options["create_release"] = process_bool_arg(
            self.options.get("create_release", False)
        )
        self.options["release_body"] = process_bool_arg(
            self.options.get("release_body", False)
        )
        self.options["dry_run"] = process_bool_arg(self.options.get("dry_run", False))

    def _process_renames(self, renamed_paths):
        """
        For each entry in renames, any renames and store them
        in self.local_to_target_paths.
        """
        if not renamed_paths:
            return {}

        is_list_of_dicts = all(isinstance(pair, dict) for pair in renamed_paths)
        dicts_have_correct_keys = is_list_of_dicts and all(
            {"local", "target"} == pair.keys() for pair in renamed_paths
        )

        ERROR_MSG = (
            "Renamed paths must be a list of dicts with `local:` and `target:` keys."
        )
        if not dicts_have_correct_keys:
            raise TaskOptionsError(ERROR_MSG)

        local_to_target_paths = {}

        for rename in renamed_paths:
            local_path = rename.get("local")
            target_path = rename.get("target")

            if local_path and target_path:
                local_to_target_paths[local_path] = target_path
            else:
                raise TaskOptionsError(ERROR_MSG)

        return local_to_target_paths

    def _get_target_repo_api(self):
        owner, name = split_repo_url(self.options["repo_url"])
        gh = self.project_config.get_github_api(owner, name)
        return gh.repository(owner, name)

    def _run_task(self):
        self.target_repo = self._get_target_repo_api()
        self._set_ref()

        with tempfile.TemporaryDirectory() as target:
            self._download_repo_and_extract(target)
            self._rename_files(target)
            commit = self._create_commit(target)
            if commit and self.options["create_release"]:
                self._create_release(target, commit.sha)

    def _set_ref(self):
        if "ref" in self.options:
            self.ref = self.options["ref"]
        else:
            self.tag_name = self.project_config.get_tag_for_version(
                self.options["version"]
            )
            self.ref = f"tags/{self.tag_name}"

    def _download_repo_and_extract(self, path):
        zf = download_extract_github_from_repo(self.get_repo(), ref=self.ref)
        included_members = self._filter_namelist(
            includes=self.options["include"], namelist=zf.namelist()
        )
        zf.extractall(path=path, members=included_members)

    def _filter_namelist(self, includes, namelist):
        """
        Filter a zipfile namelist, handling any included directory filenames missing
        a trailing slash.
        """
        included_dirs = []
        zip_dirs = [
            filename.rstrip("/") for filename in namelist if filename.endswith("/")
        ]

        for name in includes:
            if name.endswith("/"):
                included_dirs.append(name)
            elif name in zip_dirs:
                # append a trailing slash to avoid partial matches
                included_dirs.append(name + "/")

        return list(
            {
                name
                for name in namelist
                if name.startswith(tuple(included_dirs)) or name in includes
            }
        )

    def _rename_files(self, zip_dir):
        for local_name, target_name in self.options["renames"].items():
            local_path = Path(zip_dir, local_name)
            if local_path.exists():
                target_path = Path(zip_dir, target_name)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.replace(target_path)

    def _create_commit(self, path):
        committer = CommitDir(self.target_repo, logger=self.logger)
        message = f"Published content from ref {self.ref}"
        if "version" in self.options:
            message += f'\n\nVersion {self.options["version"]}'
        return committer(
            path,
            self.options["branch"],
            repo_dir="",
            commit_message=message,
            dry_run=self.options["dry_run"],
        )

    def _create_release(self, path, commit):
        # Get current release info
        repo = self.get_repo()
        # Get the ref
        try:
            ref = repo.ref(f"tags/{self.tag_name}")
        except github3.exceptions.NotFoundError:
            message = f"Ref not found for tag {self.tag_name}"
            raise GithubException(message)
        # Get the tag
        try:
            tag = repo.tag(ref.object.sha)
        except github3.exceptions.NotFoundError:
            message = f"Tag {self.tag_name} not found"
            raise GithubException(message)
        # Get the release
        try:
            release = repo.release_from_tag(self.tag_name)
            release_body = release.body if self.options["release_body"] else ""
        except github3.exceptions.NotFoundError:
            message = f"Release for {self.tag_name} not found"
            raise GithubException(message)

        # Check for tag in target repo
        try:
            self.target_repo.ref(f"tags/{self.tag_name}")
        except github3.exceptions.NotFoundError:
            pass
        else:
            message = f"Ref for tag {self.tag_name} already exists in target repo"
            raise GithubException(message)

        # Create the tag
        self.target_repo.create_tag(
            tag=self.tag_name,
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
        self.target_repo.create_release(
            tag_name=self.tag_name,
            name=self.options["version"],
            prerelease=release.prerelease,
            body=release_body,
        )
