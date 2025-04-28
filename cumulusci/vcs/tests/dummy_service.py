from cumulusci.vcs.base import VCSService
from cumulusci.vcs.models import AbstractGitTag, AbstractRef, AbstractRepo


class DummyTag(AbstractGitTag):
    pass


class DummyRef(AbstractRef):
    pass


class DummyRepo(AbstractRepo):
    def create_tag(self):
        pass

    def get_ref_for_tag(self, tag_name):
        return DummyRef(f"ref-{tag_name}")

    def get_tag_by_ref(self, ref, tag_name):
        return DummyTag(f"tag-{ref}-{tag_name}")


class ConcreteVCSService(VCSService):
    service_type = "github"

    @classmethod
    def validate_service(cls, options, keychain):
        return {"validated": True}

    def get_repository(self):
        return DummyRepo()
