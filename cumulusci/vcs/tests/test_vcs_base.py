# test_vcs_base.py

from unittest import mock

import pytest

from cumulusci.core.config import BaseProjectConfig, UniversalConfig
from cumulusci.core.keychain.base_project_keychain import BaseProjectKeychain
from cumulusci.vcs.base import VCSService
from cumulusci.vcs.models import AbstractRepo


class DummyRepo(AbstractRepo):
    def create_tag(self):
        pass

    def get_ref_for_tag(self):
        pass

    def get_tag_by_ref(self):
        pass


class ConcreteVCSService(VCSService):
    service_type = "dummy"

    @classmethod
    def validate_service(cls, options, keychain):
        return {"validated": True}

    def get_repository(self):
        return DummyRepo()


class TestVCSBase:
    @pytest.fixture
    def keychain(self):
        runtime = mock.Mock()
        runtime.project_config = BaseProjectConfig(UniversalConfig(), config={})
        runtime.keychain = BaseProjectKeychain(runtime.project_config, None)
        return runtime.keychain

    def test_init_sets_attributes(self, keychain):
        config = {"foo": "bar"}
        name = "dummy"
        svc = ConcreteVCSService(config, name, keychain)
        assert svc.config == config
        assert svc.name == name
        assert svc.keychain == keychain

    def test_service_type_property(self, keychain):
        assert ConcreteVCSService.service_type == "dummy"
        ConcreteVCSService.service_type = "other"
        assert ConcreteVCSService.service_type == "other"

    def test_validate_service(self, keychain):
        result = ConcreteVCSService.validate_service({}, keychain)
        assert result == {"validated": True}

    def test_get_repository_returns_repo(self, keychain):
        svc = ConcreteVCSService({}, "dummy", keychain)
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

        svc = NoServiceTypeVCS({}, "dummy", keychain)
        with pytest.raises(NotImplementedError):
            _ = svc.service_type
