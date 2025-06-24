import http.client
from datetime import UTC, datetime
from io import BytesIO, StringIO
from re import Pattern
from string import Template
from typing import Optional, Union

from github3 import GitHub, GitHubError
from github3.exceptions import NotFoundError, UnprocessableEntity
from github3.git import Reference, Tag
from github3.issues.issue import ShortIssue
from github3.issues.label import ShortLabel
from github3.pulls import PullRequest, ShortPullRequest
from github3.repos.branch import Branch
from github3.repos.commit import RepoCommit
from github3.repos.release import Release
from github3.repos.repo import Repository
from github3.session import GitHubSession
from requests.models import Response

from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.exceptions import GithubApiNotFoundError
from cumulusci.core.github import catch_common_github_auth_errors
from cumulusci.utils.git import parse_repo_url
from cumulusci.utils.http.requests_utils import safe_json_from_response
from cumulusci.vcs.models import (
    AbstractBranch,
    AbstractComparison,
    AbstractGitTag,
    AbstractPullRequest,
    AbstractRef,
    AbstractRelease,
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

    @property
    def message(self) -> str:
        """Gets the message of the tag."""
        return self.tag.message if self.tag else ""

    @property
    def sha(self) -> str:
        """Gets the SHA of the tag."""
        return self.tag.object.sha or self.tag.sha if self.tag else ""


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

    commit: RepoCommit
    _sha: str

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._sha = self.commit.sha if self.commit else kwargs.get("sha", "")

    def get_statuses(self, context: str, regex_match: Pattern[str]) -> Optional[str]:
        for status in self.commit.status().statuses:
            if status.state == "success" and status.context == context:
                match = regex_match.search(status.description)
                if match:
                    return match.group(1)
        return None

    @property
    def parents(self) -> list["GitHubCommit"]:
        return [GitHubCommit(**c) for c in self.commit.parents]

    @property
    def sha(self) -> str:
        """Gets the SHA of the commit."""
        return self._sha


class GitHubBranch(AbstractBranch):
    repo: "GitHubRepository"
    branch: Optional[Branch]

    def __init__(self, repo: "GitHubRepository", branch_name: str, **kwargs) -> None:
        super().__init__(repo, branch_name, **kwargs)

    def get_branch(self) -> None:
        try:
            self.branch = self.repo.repo.branch(self.name)
        except NotFoundError:
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
        except NotFoundError:
            raise GithubApiNotFoundError("Could not find branches on GitHub")

    @property
    def commit(self) -> Optional[GitHubCommit]:
        """Gets the branch commit for the current branch."""
        if self.branch is None:
            self.get_branch()

        return GitHubCommit(commit=self.branch.commit) if self.branch else None


class GitHubRelease(AbstractRelease):
    """GitHub release object for creating and managing releases."""

    release: Release

    @property
    def tag_name(self) -> str:
        """Gets the tag name of the release."""
        return self.release.tag_name if self.release else ""

    @property
    def body(self) -> Union[str, None]:
        """Gets the body of the release."""
        return self.release.body if self.release else None

    @property
    def prerelease(self) -> bool:
        """Checks if the release is a pre-release."""
        return self.release.prerelease if self.release else False

    @property
    def name(self) -> str:
        """Gets the name of the release."""
        return self.release.name if self.release else ""

    @property
    def html_url(self) -> str:
        """Gets the HTML URL of the release."""
        return self.release.html_url if self.release else ""

    @property
    def created_at(self) -> datetime:
        """Gets the creation date of the release."""
        return self.release.created_at if self.release else None

    @property
    def draft(self) -> bool:
        """Checks if the release is a draft."""
        return self.release.draft if self.release else False

    @property
    def tag_ref_name(self) -> str:
        """Gets the tag reference name of the release."""
        return "tags/" + self.tag_name


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
        except NotFoundError:
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
            pull_request: PullRequest = git_repo.repo.create_pull(
                title,
                base,
                head,
                body=body,
                maintainer_can_modify=maintainer_can_modify,
            )
            return GitHubPullRequest(repo=git_repo, pull_request=pull_request)
        except NotFoundError:
            raise GithubApiNotFoundError("Could not create pull request on GitHub")

    @property
    def number(self) -> int:
        """Gets the pull request number."""
        return self.pull_request.number if self.pull_request else None

    @property
    def title(self) -> str:
        """Gets the pull request title."""
        return self.pull_request.title if self.pull_request else ""

    @property
    def base_ref(self) -> str:
        """Gets the base reference of the pull request."""
        return self.pull_request.base.ref if self.pull_request else ""

    @property
    def head_ref(self) -> str:
        """Gets the head reference of the pull request."""
        return self.pull_request.head.ref if self.pull_request else ""

    @property
    def merged_at(self) -> datetime:
        """Gets the merged date of the short pull request."""
        return self.pull_request.merged_at if self.pull_request else None


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
        self.service_type = kwargs.get("service_type") or "github"
        self._service_config = kwargs.get("service_config")

        self._init_repo()

    def _init_repo(self) -> None:
        """Initializes the repository object."""
        if self.repo_url is not None:
            self.repo_owner, self.repo_name, host = parse_repo_url(self.repo_url)

        self.repo_owner = (
            self.repo_owner
            or self.options.get("repo_owner")
            or self.project_config.repo_owner
        )
        self.repo_name = (
            self.repo_name
            or self.options.get("repo_name")
            or self.project_config.repo_name
        )
        self.repo: Repository = self.github.repository(self.repo_owner, self.repo_name)
        self.repo_url = self.repo_url or self.repo.html_url

    @property
    def service_config(self):
        if not self._service_config:
            self._service_config = self.project_config.keychain.get_service(
                self.service_type
            )
        return self._service_config

    @property
    def owner_login(self) -> str:
        """Returns the owner login of the repository."""
        return self.repo.owner.login if self.repo else ""

    def get_ref(self, ref_sha: str) -> GitHubRef:
        """Gets a Reference object for the tag with the given SHA"""
        try:
            ref = self.repo.ref(ref_sha)
            return GitHubRef(ref=ref)
        except NotFoundError:
            raise GithubApiNotFoundError(
                f"Could not find reference for '{ref_sha}' on GitHub"
            )

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
        self,
        tag_name: str,
        message: str,
        sha: str,
        obj_type: str,
        tagger: dict = {},
        lightweight: Optional[bool] = False,
    ) -> GitHubTag:
        # Create a tag on the given repository
        tagger["name"] = tagger.get("name", self.service_config.username)
        tagger["email"] = tagger.get("email", self.service_config.email)
        tagger["date"] = tagger.get(
            "date", f"{datetime.now(UTC).replace(tzinfo=None).isoformat()}Z"
        )

        tag = self.repo.create_tag(
            tag=tag_name,
            message=message,
            sha=sha,
            obj_type=obj_type,
            tagger=tagger,
            lightweight=lightweight,
        )
        return GitHubTag(tag=tag)

    def branch(self, branch_name) -> GitHubBranch:
        # Fetches a branch from the given repository
        return GitHubBranch(self, branch_name)

    def branches(self) -> list[GitHubBranch]:
        # Fetches all branches from the given repository
        return GitHubBranch.branches(self)

    def compare_commits(
        self, branch_name: str, commit: str, source: str
    ) -> GitHubComparison:
        # Compares the given branch with the given commit
        return GitHubComparison.compare(self, branch_name, commit)

    def merge(
        self, base: str, head: str, source: str, message: str = ""
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
        except UnprocessableEntity as e:
            error_msg = options.get(
                "error_message",
                f"Error creating pull request to merge {head} into {base}",
            )
            self.logger.error(f"{error_msg}:\n{e.response.text}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {str(e)}")
        return None

    def get_commit(self, commit_sha: str) -> GitHubCommit:
        """Given a SHA1 hash, retrieve a Commit object from the REST API."""
        try:
            commit = self.repo.commit(commit_sha)
            return GitHubCommit(commit=commit)
        except (NotFoundError, UnprocessableEntity):
            # GitHub returns 422 for nonexistent commits in at least some circumstances.
            raise GithubApiNotFoundError(
                f"Could not find commit {commit_sha} on GitHub"
            )

    def release_from_tag(self, tag_name: str) -> GitHubRelease:
        """Fetches a release from the given tag name."""
        try:
            release: Release = self.repo.release_from_tag(tag_name)
        except NotFoundError:
            message = f"Release for {tag_name} not found"
            raise GithubApiNotFoundError(message)
        return GitHubRelease(release=release)

    @property
    def default_branch(self) -> str:
        """Returns the default branch of the repository."""
        return self.repo.default_branch if self.repo else ""

    def archive(
        self, format: str, zip_content: Union[str, object], ref=None
    ) -> BytesIO:
        """Archives the repository content as a zip file."""
        try:
            self.repo.archive(format, zip_content, ref)
            return zip_content
        except NotFoundError:
            raise GithubApiNotFoundError(
                f"Could not find archive for {zip_content} for service {self.service_type}"
            )

    def full_name(self) -> str:
        """Returns the full name of the repository."""
        return self.repo.full_name if self.repo else ""

    def create_release(
        self,
        tag_name: str,
        name: str = None,
        body: str = None,
        draft: bool = False,
        prerelease: bool = False,
        options: dict = {},
    ) -> GitHubRelease:
        """Creates a release on the given repository."""
        try:
            release = self.repo.create_release(
                tag_name, name=name, body=body, draft=draft, prerelease=prerelease
            )
            return GitHubRelease(release=release)
        except NotFoundError:
            raise GithubApiNotFoundError(
                f"Could not create release for {tag_name} on GitHub"
            )

    def releases(self) -> list[GitHubRelease]:
        """Fetches all releases from the given repository."""
        try:
            releases = self.repo.releases()
            return [GitHubRelease(release=release) for release in releases]
        except NotFoundError:
            raise GithubApiNotFoundError("Could not find releases on GitHub")
        except UnprocessableEntity:
            raise GithubApiNotFoundError(
                "Could not find releases on GitHub. Check if the repository is archived."
            )
        except GitHubError as e:
            if e.code == http.client.UNAUTHORIZED:
                raise GithubApiNotFoundError(
                    "Could not find releases on GitHub. Check your authentication."
                )
            else:
                raise GithubApiNotFoundError(
                    f"Could not find releases on GitHub: {e.message}"
                )
        except Exception as e:
            raise GithubApiNotFoundError(
                f"An unexpected error occurred while fetching releases: {str(e)}"
            )
        return []

    def latest_release(self) -> Optional[GitHubRelease]:
        """Fetches the latest release from the given repository."""
        try:
            release = self.repo.latest_release()
            if release:
                return GitHubRelease(release=release)
            return None
        except NotFoundError:
            raise GithubApiNotFoundError("Could not find latest release on GitHub")

    def has_issues(self) -> bool:
        """Checks if the repository has issues enabled."""
        return self.repo.has_issues() if self.repo else False

    def get_pull_requests_by_commit(self, commit_sha) -> list[GitHubPullRequest]:
        """Fetches all pull requests associated with the given commit SHA."""
        endpoint = (
            self.github.session.base_url
            + f"/repos/{self.repo.owner.login}/{self.repo.name}/commits/{commit_sha}/pulls"
        )
        response = self.github.session.get(
            endpoint, headers={"Accept": "application/vnd.github.groot-preview+json"}
        )
        json_list = safe_json_from_response(response)

        for json in json_list:
            json["body_html"] = ""
            json["body_text"] = ""

        pull_requests = [
            GitHubPullRequest(
                repo=self.repo, pull_request=ShortPullRequest(json, self.github)
            )
            for json in json_list
        ]
        return pull_requests

    def get_pr_issue_labels(self, pull_request: GitHubPullRequest) -> list[str]:
        """Fetches all labels associated with the given pull request."""
        issue: ShortIssue = self.repo.issue(pull_request.number)
        labels: ShortLabel = issue.labels()
        return [label.name for label in labels] if labels else []

    def get_latest_prerelease(self) -> Optional[GitHubRelease]:
        """Fetches the latest pre-release from the given repository."""
        try:
            QUERY = Template(
                """
                query {
                    repository(owner: "$owner", name: "$name") {
                    releases(last: 1, orderBy: {field: CREATED_AT, direction: ASC}) {
                        nodes {
                        tagName
                        }
                    }
                    }
                }
                """
            ).substitute(dict(owner=self.repo.owner, name=self.repo.name))

            session: GitHubSession = self.repo.session
            # HACK: This is a kludgy workaround because GitHub Enterprise Server
            # base_urls in github3.py end in `/api/v3`.
            host = (
                session.base_url[: -len("/v3")]
                if session.base_url.endswith("/v3")
                else session.base_url
            )
            url: str = f"{host}/graphql"
            response: Response = session.request("POST", url, json={"query": QUERY})
            response_dict: dict = response.json()

            if release_tags := response_dict["data"]["repository"]["releases"]["nodes"]:
                return self.release_from_tag(release_tags[0]["tagName"])
        except NotFoundError:
            raise GithubApiNotFoundError("Could not find latest prerelease on GitHub")

    def directory_contents(self, subfolder: str, return_as, ref: str) -> dict:
        try:
            contents = self.repo.directory_contents(
                subfolder, return_as=return_as, ref=ref
            )
        except NotFoundError:
            contents = None
            raise GithubApiNotFoundError(
                f"Could not find directory {subfolder} on GitHub."
            )
        return contents

    def file_contents(self, file_path: str, ref: str) -> StringIO:
        contents = self.repo.file_contents(file_path, ref=ref)
        contents_io = StringIO(contents.decoded.decode("utf-8") if contents else "")
        contents_io.url = (
            f"{file_path} from {self.repo.owner}/{self.repo.name}"  # for logging
        )
        return contents_io

    @property
    def clone_url(self) -> str:
        return self.repo.clone_url

    def create_commit_status(
        self,
        commit_id: str,
        context: str,
        state: str,
        description: str,
        target_url: str,
    ) -> GitHubCommit:
        """Creates a commit status in the repository."""
        try:
            status = self.repo.create_status(
                commit_id,
                state,
                target_url=target_url,
                description=description,
                context=context,
            )
            if not status:
                raise GithubApiNotFoundError(
                    f"Could not create commit status for {commit_id} on GitHub"
                )
            return self.get_commit(commit_id)
        except NotFoundError:
            raise GithubApiNotFoundError(
                f"Could not create commit status for {commit_id} on GitHub"
            )
        except UnprocessableEntity as e:
            raise GithubApiNotFoundError(
                f"Could not create commit status for {commit_id} on GitHub: {e.response.text}"
            )
