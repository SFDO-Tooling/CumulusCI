import os
import shutil

from cumulusci.core.exceptions import DependencyResolutionError
from cumulusci.core.github import get_github_api_for_repo
from cumulusci.core.github import find_latest_release
from cumulusci.core.github import find_previous_release
from cumulusci.utils import download_extract_github


class GitHubSource:
    def __init__(self, project_config, spec):
        self.project_config = project_config
        self.spec = spec
        self.url = spec["github"]
        if self.url.endswith(".git"):
            self.url = self.url[:-4]

        repo_owner, repo_name = self.url.split("/")[-2:]
        self.repo_owner = repo_owner
        self.repo_name = repo_name

        self.gh = get_github_api_for_repo(
            project_config.keychain, repo_owner, repo_name
        )
        self.repo = self.gh.repository(self.repo_owner, self.repo_name)
        self.resolve()

    def __repr__(self):
        return f"<GitHubSource {str(self)}>"

    def __str__(self):
        s = f"GitHub: {self.repo_owner}/{self.repo_name}"
        if self.description:
            s += f" @ {self.description}"
        if self.commit != self.description:
            s += f" ({self.commit})"
        return s

    def __hash__(self):
        return hash((self.url, self.commit))

    def resolve(self):
        """Resolve a github source into a specific commit.

        The spec must include:
        - github: the URL of the github repository

        The spec may include one of:
        - commit: a commit hash
        - ref: a git ref
        - branch: a git branch
        - tag: a git tag
        - release: "latest" | "previous" | "latest_beta"

        If none of these are specified, CumulusCI will look for the latest release.
        If there is no release, it will use the default branch.
        """
        ref = None
        if "commit" in self.spec:
            self.commit = self.description = self.spec["commit"]
            return
        elif "ref" in self.spec:
            ref = self.spec["ref"]
        elif "tag" in self.spec:
            ref = "tags/" + self.spec["tag"]
        elif "branch" in self.spec:
            ref = "heads/" + self.spec["branch"]
        elif "release" in self.spec:
            release_spec = self.spec["release"]
            if release_spec == "latest":
                release = find_latest_release(self.repo, include_beta=False)
            elif release_spec == "latest_beta":
                release = find_latest_release(self.repo, include_beta=True)
            elif release_spec == "previous":
                release = find_previous_release(self.repo)
            else:
                raise DependencyResolutionError(f"Unknown release: {release_spec}")
            if release is None:
                raise DependencyResolutionError(
                    f"Could not find release: {release_spec}"
                )
            ref = "tags/" + release.tag_name
        if ref is None:
            release = find_latest_release(self.repo, include_beta=False)
            if release:
                ref = "tags/" + release.tag_name
            else:
                ref = "heads/" + self.repo.default_branch
        self.description = ref[6:] if ref.startswith("heads/") else ref
        self.commit = self.repo.ref(ref).object.sha

    def fetch(self, path=None):
        """Fetch the archive of the specified commit and construct its project config."""
        # To do: copy this from a shared cache
        if path is None:
            path = os.path.join(".cci", "projects", self.repo_name, self.commit)
        if not os.path.exists(path):
            os.makedirs(path)
            zf = download_extract_github(
                self.gh, self.repo_owner, self.repo_name, ref=self.commit
            )
            try:
                zf.extractall(path)
            except Exception:
                # make sure we don't leave an incomplete cache
                shutil.rmtree(path)
                raise

        project_config = self.project_config.construct_subproject_config(
            repo_info={
                "root": os.path.realpath(path),
                "owner": self.repo_owner,
                "name": self.repo_name,
                "url": self.url,
                "commit": self.commit,
            }
        )
        return project_config

    @property
    def frozenspec(self):
        """Return a spec to reconstruct this source at the current commit"""
        return {
            "github": self.url,
            "commit": self.commit,
            "description": self.description,
        }
