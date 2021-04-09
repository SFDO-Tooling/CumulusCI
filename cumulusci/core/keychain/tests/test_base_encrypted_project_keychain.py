from cumulusci.core.config.ScratchOrgConfig import ScratchOrgConfig
import pytest

from cumulusci.core.keychain import BaseEncryptedProjectKeychain
from cumulusci.core.config import (
    BaseConfig,
    OrgConfig,
)
from cumulusci.core.exceptions import (
    ConfigError,
    CumulusCIException,
    KeychainKeyNotFound,
)


@pytest.fixture()
def keychain(project_config, key):
    keychain = BaseEncryptedProjectKeychain(project_config, key)
    assert keychain.project_config == project_config
    assert keychain.key == key
    return keychain


class TestBaseEncryptedProjectKeychain:
    def test_decrypt_config__no_config(self, keychain):
        config = keychain._decrypt_config(OrgConfig, None, extra=["test", keychain])
        assert config.__class__ == OrgConfig
        assert config.config == {}
        assert config.keychain == keychain

    def test_decrypt_config__no_config_2(self, keychain):
        config = keychain._decrypt_config(BaseConfig, None)
        assert config.__class__ == BaseConfig
        assert config.config == {}

    def test_decrypt_config__wrong_key(self, keychain, org_config):
        keychain.set_org(org_config, False)
        keychain.key = "x" * 16
        with pytest.raises(KeychainKeyNotFound):
            keychain.get_org("test")

    def test_validate_key__not_set(self, project_config):
        with pytest.raises(KeychainKeyNotFound):
            BaseEncryptedProjectKeychain(project_config, None)

    def test_validate_key__wrong_length(self, project_config):
        with pytest.raises(ConfigError):
            BaseEncryptedProjectKeychain(project_config, "1")

    def test_get_service__default(self, keychain, service_config):
        encrypted = keychain._encrypt_config(service_config)
        keychain.config["services"] = {"devhub": {"foo": encrypted}}
        keychain._default_services["devhub"] = "foo"

        default_devhub_service = keychain.get_service("devhub")
        assert default_devhub_service.config == service_config.config

    def test_set_default_service(self, keychain, service_config):
        encrypted = keychain._encrypt_config(service_config)
        keychain.config["services"] = {"devhub": {"foo": encrypted}}
        keychain._default_services["devhub"] = "bar"

        assert keychain._default_services["devhub"] == "bar"
        keychain.set_default_service("devhub", "foo")
        assert keychain._default_services["devhub"] == "foo"

    def test_set_default_service__service_not_configured(self, keychain):
        with pytest.raises(
            CumulusCIException, match="Service type is not configured: foo"
        ):
            keychain.set_default_service("foo", "foo_alias")

    def test_set_default_service__invalid_alias(self, keychain):
        keychain.config["services"] = {"devhub": {}}
        with pytest.raises(
            CumulusCIException,
            match="No service of type devhub configured with the name: foo_alias",
        ):
            keychain.set_default_service("devhub", "foo_alias")

    def test_set_encrypted_service(self, keychain, service_config):
        keychain.config["services"] = {"github": {}}
        encrypted = keychain._encrypt_config(service_config)
        keychain._set_encrypted_service("github", "alias", encrypted)
        assert keychain.services["github"]["alias"] == encrypted

    def test_construct_config(self, keychain):
        result = keychain._construct_config(
            None, [{"scratch": "scratch org"}, "org_name"]
        )
        assert isinstance(result, ScratchOrgConfig)
