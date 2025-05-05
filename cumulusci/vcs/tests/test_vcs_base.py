# test_vcs_base.py

from unittest import mock

import pytest

from cumulusci.core.config import BaseProjectConfig, UniversalConfig
from cumulusci.core.keychain.base_project_keychain import BaseProjectKeychain
from cumulusci.vcs.base import VCSService
from cumulusci.vcs.tests.dummy_service import (
    ConcreteVCSService,
    DummyBranch,
    DummyComparison,
    DummyPullRequest,
    DummyRepo,
    DummyTag,
)


class TestVCSBase:
    @pytest.fixture
    def keychain(self, service_config):
        runtime = mock.Mock()
        runtime.project_config = BaseProjectConfig(UniversalConfig(), config={})
        runtime.keychain = BaseProjectKeychain(runtime.project_config, None)
        runtime.keychain.set_service("github", "alias", service_config)
        return runtime.keychain

    def test_init_sets_attributes(self, keychain):
        config = keychain.project_config
        config.keychain = keychain

        svc = ConcreteVCSService(config, name="alias")
        assert svc.config == config
        assert svc.name == "alias"
        assert svc.keychain == keychain

    def test_service_type_property(self, keychain):
        assert ConcreteVCSService.service_type == "github"
        ConcreteVCSService.service_type = "other"
        assert ConcreteVCSService.service_type == "other"
        ConcreteVCSService.service_type = "github"

    def test_validate_service(self, keychain):
        result = ConcreteVCSService.validate_service({}, keychain)
        assert result == {"validated": True}

    def test_get_repository_returns_repo(self, keychain):
        config = keychain.project_config
        config.keychain = keychain
        svc = ConcreteVCSService(config)
        repo = svc.get_repository()
        assert isinstance(repo, DummyRepo)

    def test_abstract_methods_raise(self, keychain):
        # Can't instantiate VCSService directly
        with pytest.raises(TypeError):
            VCSService({}, "name", keychain)

        # Subclass missing abstract methods
        class IncompleteVCSService(VCSService):
            pass

        with pytest.raises(TypeError):
            IncompleteVCSService({}, "name", keychain)

    def test_service_type_not_implemented(self, keychain):
        class NoServiceTypeVCS(VCSService):
            @classmethod
            def validate_service(cls, options, keychain):
                return {}

            def get_repository(self):
                return DummyRepo()

        config = keychain.project_config
        config.keychain = keychain

        with pytest.raises(NotImplementedError):
            svc = NoServiceTypeVCS(config)
            _ = svc.service_type

    def test_abstract_git_tag(self):
        dt = DummyTag(None)
        assert dt.tag is None

        dt.sha = "1234567890abcdef"
        assert dt.sha == "1234567890abcdef"

    def test_abstract_branch(self):
        db = DummyBranch(DummyRepo(), "test-branch", branch="test-branch")
        assert db.name == "test-branch"
        assert isinstance(db.repo, DummyRepo)
        assert db.branch == "test-branch"

    def test_abstract_comparison(self):
        dc = DummyComparison(DummyRepo(), "base", "head")
        assert dc.base == "base"
        assert dc.head == "head"
        assert isinstance(dc.repo, DummyRepo)
        assert dc.comparison is None

        with pytest.raises(NotImplementedError):
            dc.files

    def test_abstract_pull_request(self):
        dpr = DummyPullRequest(repo=DummyRepo(), pull_request="test-pr")
        assert isinstance(dpr.repo, DummyRepo)
        assert dpr.pull_request == "test-pr"

        with pytest.raises(NotImplementedError):
            dpr.base_ref
