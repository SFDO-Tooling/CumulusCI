from unittest.mock import MagicMock

import pytest

from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.keychain import EncryptedFileProjectKeychain
from cumulusci.vcs import bootstrap
from cumulusci.vcs.base import VCSService
from cumulusci.vcs.tests.dummy_service import DummyRef, DummyRepo, DummyTag


class TestVCSBase:
    @pytest.fixture()
    def keychain(self, project_config, key) -> EncryptedFileProjectKeychain:
        keychain = EncryptedFileProjectKeychain(project_config, key)
        assert keychain.project_config == project_config
        assert keychain.key == key
        return keychain

    def test_get_service_with_class_path(self, keychain, service_config):
        project_config = keychain.project_config
        project_config.keychain = keychain
        keychain.set_service("github", "alias", service_config)

        encrypted = keychain._get_config_bytes(service_config)
        keychain.config["services"]["github"] = {"alias": encrypted}

        keychain._save_default_service("github", "alias", project=False)
        keychain._load_default_services()

        result = bootstrap.get_service(project_config)
        assert isinstance(result, VCSService)

    def test_get_service_missing_class_path(self):
        config = MagicMock()
        config.lookup.return_value = "github"
        config.services = {"github": {}}
        with pytest.raises(CumulusCIException) as e:
            bootstrap.get_service(config)
        assert "Provider class for github not found in config" in str(e.value)

    def test_get_ref_for_tag(self):
        repo = DummyRepo()
        assert isinstance(bootstrap.get_ref_for_tag(repo, "v1.0"), DummyRef)

    def test_get_tag_by_name(self):
        repo = DummyRepo()
        # get_tag_by_name calls get_ref_for_tag and get_tag_by_ref
        assert isinstance(bootstrap.get_tag_by_name(repo, "v1.0"), DummyTag)
