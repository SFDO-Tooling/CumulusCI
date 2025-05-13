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
    service_type = "github"

    @classmethod
    def validate_service(cls, options, keychain):
        return {"validated": True}

    def get_repository(self):
        return DummyRepo()

    @classmethod
    def get_service_for_url(cls, url):
        return cls()

    def get_committer(self, repo: AbstractRepo) -> AbstractCommitDir:
        return DummyCommitDir()


class DummyCommitDir(AbstractCommitDir):
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


class DummyRepo(AbstractRepo):
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

    def branch(self):
        pass

    def branches(self):
        pass

    def compare_commits(self):
        pass

    def merge(self):
        pass

    def archive(self):
        pass

    def create_pull(self):
        pass

    def create_release(self):
        pass

    def default_branch(self):
        pass

    def full_name(self):
        pass

    def get_commit(self):
        pass

    def pull_requests(self):
        pass

    def release_from_tag(self):
        pass

    def releases(self):
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
