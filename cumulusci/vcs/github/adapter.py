import http.client
from datetime import UTC, datetime
from typing import Union

import github3.exceptions
from github3 import GitHub, GitHubError
from github3.exceptions import NotFoundError
from github3.git import Reference, Tag
from github3.repos.repo import Repository

from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.exceptions import GithubApiNotFoundError
from cumulusci.core.github import catch_common_github_auth_errors
from cumulusci.vcs.models import (
    AbstractBranch,
    AbstractComparison,
    AbstractGitTag,
    AbstractPullRequest,
    AbstractRef,
    AbstractRepo,
    AbstractRepoCommit,
)


class GitHubRef(AbstractRef):
    ref: Reference
    sha: str
    type: str

    def __init__(self, ref: Reference, **kwargs) -> None:
        super().__init__(ref, **kwargs)
        self.sha = ref.object.sha
        self.type = ref.object.type


class GitHubTag(AbstractGitTag):
    tag: Tag

    def __init__(self, tag: Tag, **kwargs) -> None:
        super().__init__(tag, **kwargs)
        self.tag = tag
        self.sha = tag.sha


class GitHubComparison(AbstractComparison):
    @catch_common_github_auth_errors
    def get_comparison(self) -> None:
        """Gets the comparison object for the current base and head."""
        self.comparison = self.repo.repo.compare_commits(self.base, self.head)

    @property
    def files(self) -> list:
        return (
            self.comparison.files if self.comparison and self.comparison.files else []
        )

    @property
    def behind_by(self) -> int:
        """Returns the number of commits the head is behind the base."""
        return (
            self.comparison.behind_by
            if self.comparison and self.comparison.behind_by
            else 0
        )

    @classmethod
    def compare(cls, repo: AbstractRepo, base: str, head: str) -> "GitHubComparison":
        comparison = GitHubComparison(repo, base, head)
        comparison.get_comparison()
        return comparison


class GitHubCommit(AbstractRepoCommit):
    """GitHub comparison object for comparing commits."""

    pass


class GitHubBranch(AbstractBranch):
    repo: "GitHubRepository"

    def __init__(self, repo: "GitHubRepository", branch_name: str, **kwargs) -> None:
        super().__init__(repo, branch_name, **kwargs)
        self.repo = repo

    def get_branch(self) -> None:
        try:
            self.branch = self.repo.repo.branch(self.name)
        except github3.exceptions.NotFoundError:
            message = f"Branch {self.name} not found"
            raise GithubApiNotFoundError(message)
        return

    @classmethod
    @catch_common_github_auth_errors
    def branches(cls, git_repo: AbstractRepo) -> list["GitHubBranch"]:
        """Fetches all branches from the given repository"""
        try:
            branches = git_repo.repo.branches()
            return [
                GitHubBranch(git_repo, branch.name, branch=branch)
                for branch in branches
            ]
        except github3.exceptions.NotFoundError:
            raise GithubApiNotFoundError("Could not find branches on GitHub")


class GitHubPullRequest(AbstractPullRequest):
    """GitHub pull request object for creating and managing pull requests."""

    @classmethod
    def pull_requests(
        cls,
        git_repo: AbstractRepo,
        state=None,
        head=None,
        base=None,
        sort="created",
        direction="desc",
        number=-1,
        etag=None,
    ) -> list["GitHubPullRequest"]:
        """Fetches all pull requests from the repository."""
        try:
            pull_requests = git_repo.repo.pull_requests(
                state=state,
                head=head,
                base=base,
                sort=sort,
                direction=direction,
                number=number,
                etag=etag,
            )
            return [
                GitHubPullRequest(repo=git_repo, pull_request=pull_request)
                for pull_request in pull_requests
            ]
        except github3.exceptions.NotFoundError:
            raise GithubApiNotFoundError("Could not find pull requests on GitHub")

    @classmethod
    def create_pull(
        cls,
        git_repo: AbstractRepo,
        title: str,
        base: str,
        head: str,
        body: str = None,
        maintainer_can_modify: bool = None,
    ) -> "GitHubPullRequest":
        """Creates a pull request on the given repository."""
        try:
            pull_request = git_repo.repo.create_pull(
                title,
                base,
                head,
                body=body,
                maintainer_can_modify=maintainer_can_modify,
            )
            return GitHubPullRequest(repo=git_repo, pull_request=pull_request)
        except github3.exceptions.NotFoundError:
            raise GithubApiNotFoundError("Could not create pull request on GitHub")

    @property
    def number(self) -> int:
        """Gets the pull request number."""
        return self.pull_request.number if self.pull_request else None

    @property
    def base_ref(self) -> str:
        """Gets the base reference of the pull request."""
        return self.pull_request.base.ref if self.pull_request else ""

    @property
    def head_ref(self) -> str:
        """Gets the head reference of the pull request."""
        return self.pull_request.head.ref if self.pull_request else ""


class GitHubRepository(AbstractRepo):

    github: GitHub
    project_config: BaseProjectConfig
    repo: Repository

    def __init__(
        self, github: GitHub, project_config: BaseProjectConfig, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.github: GitHub = github
        self.project_config: BaseProjectConfig = project_config
        self.repo: Repository = self.github.repository(
            self.project_config.repo_owner, self.project_config.repo_name
        )
        self.service_type = kwargs.get("service_type") or "github"
        self._service_config = kwargs.get("service_config")

    @property
    def service_config(self):
        if not self._service_config:
            self._service_config = self.project_config.keychain.get_service(
                self.service_type
            )
        return self._service_config

    def get_ref_for_tag(self, tag_name: str) -> GitHubRef:
        """Gets a Reference object for the tag with the given name"""
        try:
            ref = self.repo.ref(f"tags/{tag_name}")
            return GitHubRef(ref=ref)
        except NotFoundError:
            raise GithubApiNotFoundError(
                f"Could not find reference for 'tags/{tag_name}' on GitHub"
            )

    def get_tag_by_ref(self, ref: GitHubRef, tag_name: str = None) -> GitHubTag:
        """Fetches a tag by reference, name from the given repository"""
        try:
            tag = self.repo.tag(ref.sha)
            return GitHubTag(tag=tag)
        except NotFoundError:
            msg = f"Could not find tag '{tag_name}' with SHA {ref.sha} on GitHub"
            if ref.type != "tag":
                msg += f"\n{tag_name} is not an annotated tag."
            raise GithubApiNotFoundError(msg)

    @catch_common_github_auth_errors
    def create_tag(
        self, tag_name: str, message: str, sha: str, obj_type: str, tagger: dict = {}
    ) -> GitHubTag:
        # Create a tag on the given repository
        tagger["name"] = tagger.get("name", self.service_config.username)
        tagger["email"] = tagger.get("email", self.service_config.email)
        tagger["date"] = tagger.get(
            "date", f"{datetime.now(UTC).replace(tzinfo=None).isoformat()}Z"
        )

        tag = self.repo.create_tag(
            tag=tag_name, message=message, sha=sha, obj_type=obj_type, tagger=tagger
        )
        return GitHubTag(tag=tag)

    def branch(self, branch_name) -> GitHubBranch:
        # Fetches a branch from the given repository
        return GitHubBranch(self, branch_name)

    def branches(self) -> list[GitHubBranch]:
        # Fetches all branches from the given repository
        return GitHubBranch.branches(self)

    def compare_commits(self, branch_name: str, commit: str) -> GitHubComparison:
        # Compares the given branch with the given commit
        return GitHubComparison.compare(self, branch_name, commit)

    def merge(
        self, base: str, head: str, message: str = ""
    ) -> Union[GitHubCommit, None]:
        # Merges the given base and head with the specified message
        try:
            commit = self.repo.merge(base, head, message)
            git_commit = GitHubCommit(commit=commit)
            return git_commit
        except GitHubError as e:
            if e.code != http.client.CONFLICT:
                raise
        except NotFoundError:
            raise GithubApiNotFoundError(
                f"Could not find base {base} or head {head} for merge on GitHub"
            )

    def pull_requests(
        self,
        state: str = None,
        head: str = None,
        base: str = None,
        sort: str = "created",
        direction: str = "desc",
        number: int = -1,
        etag: str = None,
    ) -> list[GitHubPullRequest]:
        """Fetches all pull requests from the given repository"""
        return GitHubPullRequest.pull_requests(
            self,
            state=state,
            head=head,
            base=base,
            sort=sort,
            direction=direction,
            number=number,
            etag=etag,
        )

    def create_pull(
        self,
        title: str,
        base: str,
        head: str,
        body: str = None,
        maintainer_can_modify: bool = None,
        options: dict = {},
    ) -> Union[GitHubPullRequest, None]:
        """Creates a pull request on the given repository"""
        try:
            pull_request = GitHubPullRequest.create_pull(
                self,
                title,
                base,
                head,
                body=body,
                maintainer_can_modify=maintainer_can_modify,
            )
            return pull_request
        except github3.exceptions.UnprocessableEntity as e:
            error_msg = options.get(
                "error_message",
                f"Error creating pull request to merge {head} into {base}",
            )
            self.logger.error(f"{error_msg}:\n{e.response.text}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {str(e)}")
        return None
