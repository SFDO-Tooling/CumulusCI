import os
import shutil

import fs
from github3.exceptions import NotFoundError

from cumulusci.core.exceptions import DependencyResolutionError
from cumulusci.core.github import (
    catch_common_github_auth_errors,
    find_latest_release,
    find_previous_release,
    get_github_api_for_repo,
)
from cumulusci.utils import download_extract_github
from cumulusci.utils.git import split_repo_url
from cumulusci.utils.yaml.cumulusci_yml import GitHubSourceModel, GitHubSourceRelease


class GitHubSource:
    def __init__(self, project_config, spec: GitHubSourceModel):
        self.project_config = project_config
        self.spec = spec
        self.url = spec.github
        if self.url.endswith(".git"):
            self.url = self.url[:-4]

        self.repo_owner, self.repo_name = split_repo_url(self.url)

        try:
            self.gh = get_github_api_for_repo(project_config.keychain, self.url)
            self.repo = self._get_repository(self.repo_owner, self.repo_name)
        except NotFoundError:
            raise DependencyResolutionError(
                f"We are unable to find the repository at {self.url}. Please make sure the URL is correct, that your GitHub user has read access to the repository, and that your GitHub personal access token includes the “repo” scope."
            )
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

    @catch_common_github_auth_errors
    def _get_repository(self, repo_owner: str, repo_name: str):
        repo = self.gh.repository(repo_owner, repo_name)
        return repo

    def resolve(self):
        """Resolve a GitHub source into a specific commit.

        The spec must include:
        - github: the URL of the GitHub repository

        It's recommended that the source include:
        - resolution_strategy: [production | preproduction | <strategy-name>]

        The spec may instead be specific about the desired ref or release:
        - commit: a commit hash
        - ref: a Git ref
        - branch: a Git branch
        - tag: a Git tag
        - release: "latest" | "previous" | "latest_beta"

        If none of these are specified, CumulusCI will use the resolution strategy "production"
        to locate the appropriate release or ref.
        """
        ref = None
        self.branch = None
        # These branches preserve some existing behavior: when a source is set to
        # a specific tag or release, there's no fallback, as there would be
        # if we were subsumed within the dependency resolution machinery.

        # If the user was _not_ specific, we will use the full resolution stack,
        # including fallback behaviors.
        if self.spec.commit:
            self.commit = self.description = self.spec.commit
            return
        elif self.spec.ref:
            ref = self.spec.ref
        elif self.spec.tag:
            ref = "tags/" + self.spec.tag
        elif self.spec.branch:
            self.branch = self.spec.branch
            ref = "heads/" + self.spec.branch
        elif self.spec.release:
            release = None
            if self.spec.release is GitHubSourceRelease.LATEST:
                release = find_latest_release(self.repo, include_beta=False)
            elif self.spec.release is GitHubSourceRelease.LATEST_BETA:
                release = find_latest_release(self.repo, include_beta=True)
            elif self.spec.release is GitHubSourceRelease.PREVIOUS:
                release = find_previous_release(self.repo)
            if release is None:
                raise DependencyResolutionError(
                    f"Could not find release {self.spec.release}."
                )
            ref = "tags/" + release.tag_name
        else:
            # Avoid circular import issues
            from cumulusci.core.dependencies.dependencies import GitHubDynamicDependency
            from cumulusci.core.dependencies.resolvers import (
                get_resolver_stack,
                resolve_dependency,
            )

            # Use resolution strategies to find the right commit.
            dep = GitHubDynamicDependency(github=self.spec.github)
            resolve_dependency(
                dep,
                self.project_config,
                get_resolver_stack(self.project_config, self.spec.resolution_strategy),
            )
            self.commit = self.description = dep.ref
            return

        self.description = ref[6:] if ref.startswith("heads/") else ref
        self.commit = self.repo.ref(ref).object.sha

    def fetch(self):
        """Fetch the archive of the specified commit and construct its project config."""
        with self.project_config.open_cache(
            fs.path.join("projects", self.repo_name, self.commit)
        ) as path:
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
                # Note: we currently only pass the branch if it was explicitly
                # included in the source spec. If the commit was found another way,
                # we aren't looking up what branches have that commit as their head.
                "branch": self.branch,
            }
        )
        return project_config

    @property
    def frozenspec(self):
        """Return a spec to reconstruct this source at the current commit"""
        # TODO: The branch name is lost when freezing the source for MetaDeploy.
        # We could include it here, but it would fail validation when GitHubSourceModel
        # parses it due to having both commit and branch.
        return {
            "github": self.url,
            "commit": self.commit,
            "description": self.description,
        }
