from datetime import datetime

from github3 import GitHub
from github3.exceptions import NotFoundError
from github3.git import Tag

from cumulusci.core.exceptions import GithubApiNotFoundError
from cumulusci.core.github import catch_common_github_auth_errors

from ..repository import RepositoryInterface
from .reference import ReferenceAdapter
from .tag import TagAdapter


class RepositoryAdapter(RepositoryInterface):

    github: GitHub

    def __init__(self, github, project_config):
        self.github = github
        self.project_config = project_config
        self._repo = self.github.repository(
            project_config.repo_owner, project_config.repo_name
        )

    def get_repo(self):
        return self._repo

    def get_ref_for_tag(self, tag_name: str) -> ReferenceAdapter:
        """Gets a Reference object for the tag with the given name"""
        try:
            ref = self._repo.ref(f"tags/{tag_name}")
            return ReferenceAdapter(ref)
        except NotFoundError:
            raise GithubApiNotFoundError(
                f"Could not find reference for 'tags/{tag_name}' on GitHub"
            )

    def get_tag_by_ref(self, ref: str, tag_name: str = None) -> Tag:
        """Fetches a tag by reference, name from the given repository"""
        try:
            tag = self._repo.tag(ref.object.sha)
            return TagAdapter(tag)
        except NotFoundError:
            msg = f"Could not find tag '{tag_name}' with SHA {ref.object.sha} on GitHub"
            if ref.object.type != "tag":
                msg += f"\n{tag_name} is not an annotated tag."
            raise GithubApiNotFoundError(msg)

    @catch_common_github_auth_errors
    def create_tag(
        self, tag_name: str, message: str, sha: str, obj_type: str, tagger={}
    ) -> TagAdapter:
        github_config = self.project_config.keychain.get_service("github")

        tagger["name"] = tagger.get("name", github_config.username)
        tagger["email"] = tagger.get("email", github_config.email)
        tagger["date"] = tagger.get("date", f"{datetime.utcnow().isoformat()}Z")

        tag = self._repo.create_tag(
            tag=tag_name, message=message, sha=sha, obj_type=obj_type, tagger=tagger
        )
        return TagAdapter(tag)
