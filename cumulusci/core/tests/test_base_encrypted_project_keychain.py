import pytest

from cumulusci.core.keychain import BaseEncryptedProjectKeychain
from cumulusci.core.config import (
    BaseConfig,
    BaseProjectConfig,
    ConnectedAppOAuthConfig,
    OrgConfig,
    ScratchOrgConfig,
    ServiceConfig,
    UniversalConfig,
)
from cumulusci.core.exceptions import (
    ConfigError,
    KeychainKeyNotFound,
)


@pytest.fixture()
def project_config():
    universal_config = UniversalConfig()
    project_config = BaseProjectConfig(universal_config, config={"no_yaml": True})
    project_config.config["services"] = {
        "connected_app": {"attributes": {"test": {"required": True}}},
        "github": {"attributes": {"name": {"required": True}, "password": {}}},
        "not_configured": {"attributes": {"foo": {"required": True}}},
    }
    project_config.project__name = "TestProject"
    return project_config


@pytest.fixture
def service_configs():
    return {
        "connected_app": ServiceConfig({"test": "value"}),
        "github": ServiceConfig({"name": "hub"}),
    }


@pytest.fixture
def org_config():
    return OrgConfig({"foo": "bar"}, "test")


@pytest.fixture
def scratch_org_config():
    return ScratchOrgConfig({"foo": "bar", "scratch": True}, "test_scratch")


@pytest.fixture
def key():
    return "0123456789123456"


@pytest.fixture
def service_conf():
    return ServiceConfig({"name": "bar@baz.biz", "password": "test123"})


@pytest.fixture()
def keychain(project_config, key):
    keychain = BaseEncryptedProjectKeychain(project_config, key)
    assert keychain.project_config == project_config
    assert keychain.key == key
    return keychain


class TestBaseEncryptedProjectKeychain:
    def test_get_connected_app(self, keychain):
        keychain.app = keychain._encrypt_config(BaseConfig({}))
        app = keychain.get_connected_app()
        assert isinstance(app, ConnectedAppOAuthConfig)

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
