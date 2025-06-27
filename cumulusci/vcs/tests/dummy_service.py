from io import StringIO
from typing import Optional

from cumulusci.core.config.tests.test_config import DummyRepository
from cumulusci.core.dependencies.base import DynamicDependency
from cumulusci.vcs.base import VCSService
from cumulusci.vcs.models import (
    AbstractBranch,
    AbstractComparison,
    AbstractGitTag,
    AbstractPullRequest,
    AbstractRef,
    AbstractRepo,
    AbstractRepoCommit,
)
from cumulusci.vcs.utils import AbstractCommitDir


class ConcreteVCSService(VCSService):
    service_type = "test_service"

    @classmethod
    def validate_service(cls, options, keychain):
        return {"validated": True}

    def get_repository(self, options: dict = {}):
        return DummyRepo()

    def parse_repo_url(self):
        pass

    @classmethod
    def get_service_for_url(cls, config, url, service_alias=None):
        return None

    @property
    def dynamic_dependency_class(self) -> DynamicDependency:
        return DynamicDependency

    def get_committer(self, repo: AbstractRepo) -> AbstractCommitDir:
        return DummyCommitDir()

    def markdown(self):
        pass

    def parent_pr_notes_generator(self, repo):
        pass

    def release_notes_generator(self, options: dict):
        pass


class DummyCommitDir(AbstractCommitDir):
    def __call__(
        self, local_dir, branch, repo_dir=None, commit_message=None, dry_run=False
    ):
        pass


class DummyTag(AbstractGitTag):
    def __init__(self, tag, **kwargs):
        super().__init__(**kwargs)
        self.tag = tag
        self.sha = "1234567890abcdef"

    @property
    def message(self) -> str:
        return "Dummy tag message"


class DummyRef(AbstractRef):
    pass


class DummyBranch(AbstractBranch):
    def branches(self):
        pass

    def get_branch(self):
        pass

    def commit(self):
        pass


class DummyRepo(AbstractRepo):

    repo: DummyRepository

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.repo = kwargs.get("repo", None)

    def create_tag(
        self, tag_name: str, message: str, sha: str, obj_type: str, tagger={}
    ) -> "AbstractGitTag":
        return DummyTag(tag_name)

    def get_ref_for_tag(self, tag_name: str) -> "AbstractRef":
        return DummyRef(f"ref-{tag_name}")

    def get_tag_by_ref(
        self, ref: AbstractRef, tag_name: str = None
    ) -> "AbstractGitTag":
        return DummyTag(f"tag-{ref}-{tag_name}")

    def branch(self, branch_name: str):
        pass

    def branches(self):
        pass

    def compare_commits(self, base: str, head: str, source: str):
        pass

    def merge(self, base: str, head: str, source: str, message: str = ""):
        pass

    def archive(self, format: str, zip_content, ref=None):
        pass

    def create_pull(
        self,
        title: str,
        base: str,
        head: str,
        body: str = None,
        maintainer_can_modify: bool = None,
        options: dict = {},
    ):
        pass

    def create_release(
        self,
        tag_name: str,
        name: str,
        body: str = None,
        draft: bool = False,
        prerelease: bool = False,
        options: dict = {},
    ):
        pass

    @property
    def default_branch(self):
        pass

    def full_name(self):
        pass

    def get_commit(self, commit_sha: str):
        pass

    def pull_requests(self, **kwargs):
        pass

    def release_from_tag(self, tag_name: str):
        pass

    def releases(self):
        pass

    def get_pr_issue_labels(self, pull_request):
        pass

    def has_issues(self):
        pass

    def latest_release(self):
        pass

    @property
    def owner_login(self):
        pass

    def directory_contents(self, subfolder: str, return_as, ref: str):
        pass

    @property
    def clone_url(self):
        return "https://github.com/test/repo.git"

    def file_contents(self, file_path: str, ref: str = None) -> StringIO:
        return self.repo.file_contents(file_path, ref=ref)

    def get_latest_prerelease(self):
        pass

    def get_ref(self, ref_sha: str):
        pass

    def create_commit_status(
        self,
        commit_id: str,
        context: str,
        state: str,
        description: str,
        target_url: str,
    ):
        pass


class DummyComparison(AbstractComparison):
    def compare(self):
        pass

    def get_comparison(self):
        pass


class DummyRepoCommit(AbstractRepoCommit):
    pass


class DummyPullRequest(AbstractPullRequest):
    def create_pull(self):
        pass

    @property
    def number(self):
        pass

    @property
    def title(self) -> str:
        return "Dummy pull request title"

    def pull_requests(self):
        pass

    @property
    def base_ref(self) -> Optional[str]:
        super().base_ref()

    @property
    def head_ref(self) -> str:
        return "Dummy pull request title"

    @property
    def merged_at(self) -> str:
        return "Dummy pull request title"
