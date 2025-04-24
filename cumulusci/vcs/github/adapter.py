from datetime import datetime

from github3 import GitHub
from github3.exceptions import NotFoundError
from github3.git import Reference, Tag
from github3.repos.repo import Repository

from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.exceptions import GithubApiNotFoundError
from cumulusci.core.github import catch_common_github_auth_errors
from cumulusci.vcs.models import AbstractGitTag, AbstractRef, AbstractRepo


class GitHubRef(AbstractRef):
    ref: Reference

    def __init__(self, ref: Reference, **kwargs) -> None:
        super().__init__(ref, **kwargs)
        self.sha = ref.object.sha


class GitHubTag(AbstractGitTag):
    tag: Tag

    def __init__(self, tag: Reference, **kwargs) -> None:
        super().__init__(tag, **kwargs)
        self.sha = tag.sha


class GitHubRepository(AbstractRepo):

    github: GitHub
    project_config: BaseProjectConfig
    repo: Repository

    def __init__(self, github: GitHub, project_config: BaseProjectConfig):
        self.github: GitHub = github
        self.project_config: BaseProjectConfig = project_config
        self.repo: Repository = self.github.repository(
            self.project_config.repo_owner, self.project_config.repo_name
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

    def get_tag_by_ref(self, ref: str, tag_name: str = None) -> GitHubTag:
        """Fetches a tag by reference, name from the given repository"""
        try:
            tag = self.repo.tag(ref.sha)
            return GitHubTag(tag=tag)
        except NotFoundError:
            msg = f"Could not find tag '{tag_name}' with SHA {ref.object.sha} on GitHub"
            if ref.object.type != "tag":
                msg += f"\n{tag_name} is not an annotated tag."
            raise GithubApiNotFoundError(msg)

    @catch_common_github_auth_errors
    def create_tag(
        self, tag_name: str, message: str, sha: str, obj_type: str, tagger={}
    ) -> GitHubTag:
        github_config = self.project_config.keychain.get_service("github")

        tagger["name"] = tagger.get("name", github_config.username)
        tagger["email"] = tagger.get("email", github_config.email)
        tagger["date"] = tagger.get("date", f"{datetime.utcnow().isoformat()}Z")

        tag = self.repo.create_tag(
            tag=tag_name, message=message, sha=sha, obj_type=obj_type, tagger=tagger
        )
        return GitHubTag(tag=tag)
