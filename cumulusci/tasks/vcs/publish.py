import copy
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from cumulusci.core.exceptions import TaskOptionsError, VcsException, VcsNotFoundError
from cumulusci.core.utils import process_bool_arg, process_list_arg
from cumulusci.tasks.base_source_control_task import BaseSourceControlTask
from cumulusci.utils import download_extract_vcs_from_repo, filter_namelist
from cumulusci.vcs.base import VCSService
from cumulusci.vcs.bootstrap import get_service_for_repo_url, get_tag_by_name
from cumulusci.vcs.models import AbstractGitTag, AbstractRelease, AbstractRepo

if TYPE_CHECKING:
    from cumulusci.vcs.utils import AbstractCommitDir


class PublishSubtree(BaseSourceControlTask):
    task_options = {  # TODO: should use `class Options instead`
        "repo_url": {"description": "The url to the public repo", "required": True},
        "branch": {
            "description": "The branch to update in the target repo",
            "required": True,
        },
        "version": {
            "description": "(Deprecated >= 3.42.0) Only the values of 'latest' and 'latest_beta' are acceptable. "
            "Required if 'ref' or 'tag_name' is not set. This will override tag_name if it is provided."
        },
        "tag_name": {
            "description": "The name of the tag that should be associated with this release. "
            "Values of 'latest' and 'latest_beta' are also allowed. "
            "Required if 'ref' or 'version' is not set."
        },
        "ref": {
            "description": "The git reference to publish.  Takes precedence over 'version' and 'tag_name'. "
            "Required if 'tag_name' is not set."
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

        if "version" in self.options:  # pragma: no cover
            self.logger.warning(
                "The `version` option is deprecated. Please use the `tag_name` option instead."
            )
            if self.options["version"] not in ("latest", "latest_beta"):
                raise TaskOptionsError(
                    f"Only `latest` and `latest_beta` are valid values for the `version` option. Found: {self.options['version']}"
                )

        if (
            "ref" not in self.options
            and "tag_name" not in self.options
            and "version" not in self.options
        ):
            raise TaskOptionsError("Either `ref` or `tag_name` option is required.")

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

    def _get_target_repo_api(self) -> AbstractRepo:
        target_vcs_service: VCSService = get_service_for_repo_url(
            self.project_config, self.options["repo_url"]
        )
        target_vcs_service.logger = self.logger
        repo_options = copy.deepcopy(self.options)
        repo_options.update({"repository_url": self.options["repo_url"]})
        return target_vcs_service.get_repository(options=repo_options)

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
        from cumulusci.vcs.utils import get_ref_from_options

        self.ref = get_ref_from_options(self.project_config, self.options)
        self.tag_name = self.ref[5:] if self.ref.startswith("tags/") else None

    def _download_repo_and_extract(self, path):
        zf = download_extract_vcs_from_repo(self.get_repo(), ref=self.ref)
        included_members = filter_namelist(
            includes=self.options["include"], namelist=zf.namelist()
        )
        zf.extractall(path=path, members=included_members)

    def _rename_files(self, zip_dir):
        for local_name, target_name in self.options["renames"].items():
            local_path = Path(zip_dir, local_name)
            if local_path.exists():
                target_path = Path(zip_dir, target_name)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.replace(target_path)

    def _create_commit(self, path):
        committer: AbstractCommitDir = self.vcs_service.get_committer(self.target_repo)
        message = f"Published content from ref {self.ref}"
        if "tag_name" in self.options:
            message += f"\n\nTag {self.tag_name}"
        return committer(
            path,
            self.options["branch"],
            repo_dir="",
            commit_message=message,
            dry_run=self.options["dry_run"],
        )

    def _create_release(self, path, commit):
        repo: AbstractRepo = self.get_repo()
        tag: AbstractGitTag = get_tag_by_name(repo, self.tag_name)

        # Get the release
        release: AbstractRelease = repo.release_from_tag(self.tag_name)
        release_body: str = release.body if self.options["release_body"] else ""

        # Check for tag in target repo
        try:
            self.target_repo.get_ref_for_tag(self.tag_name)
        except VcsNotFoundError:
            pass
        else:
            message = f"Ref for tag {self.tag_name} already exists in target repo"
            raise VcsException(message)

        # Create the tag
        self.target_repo.create_tag(
            tag_name=self.tag_name,
            message=tag.message,
            sha=commit,
            obj_type="commit",
            lightweight=False,
        )

        # Create the release
        self.target_repo.create_release(
            tag_name=self.tag_name,
            name=self.project_config.get_version_for_tag(self.tag_name),
            prerelease=release.prerelease,
            body=release_body,
        )
