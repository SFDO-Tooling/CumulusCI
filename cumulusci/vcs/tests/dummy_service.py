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


class ConcreteVCSService(VCSService):
    service_type = "github"

    @classmethod
    def validate_service(cls, options, keychain):
        return {"validated": True}

    def get_repository(self):
        return DummyRepo()


class DummyTag(AbstractGitTag):
    pass


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

    def pull_requests(self):
        pass
