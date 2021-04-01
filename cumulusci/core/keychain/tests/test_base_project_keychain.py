import re
import pytest

from unittest import mock

from cumulusci.core.keychain import BaseProjectKeychain, DEFAULT_CONNECTED_APP
from cumulusci.core.exceptions import OrgNotFound, ServiceNotValid, ServiceNotConfigured
from cumulusci.core.config import (
    BaseConfig,
    BaseProjectConfig,
    OrgConfig,
    ScratchOrgConfig,
    ServiceConfig,
    UniversalConfig,
)


@pytest.fixture()
def project_config():
    universal_config = UniversalConfig()
    project_config = BaseProjectConfig(universal_config, config={"no_yaml": True})
    project_config.config["services"] = {
        "connected_app": {"attributes": {"test": {"required": True}}},
        "github": {"attributes": {"name": {"required": True}, "password": {}}},
        "not_configured": {"attributes": {"foo": {"required": True}}},
        "devhub": {"attributes": {"foo": {"required": True}}},
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
    keychain = BaseProjectKeychain(project_config, key)
    assert keychain.project_config == project_config
    assert keychain.key == key
    return keychain


class TestBaseProjectKeychain:
    def test_set_non_existant_service(self, project_config, key):
        keychain = BaseProjectKeychain(project_config, key)
        with pytest.raises(ServiceNotValid):
            keychain.set_service(
                "doesnotexist", "alias", ServiceConfig({"name": ""}), project=False
            )

    def test_set_invalid_service(self, keychain):
        with pytest.raises(ServiceNotValid):
            keychain.set_service(
                "github", "alias", ServiceConfig({"name": ""}), project=False
            )

    def test_get_service_not_in_configuration(self, keychain):
        """This service is not listed as a service type in cumulusci.yml"""
        with pytest.raises(ServiceNotConfigured):
            keychain.get_service("not_in_configuration")

    def test_get_service_not_configured(self, keychain):
        """This service is supported by CumulusCI but is not currently configured"""
        with pytest.raises(ServiceNotConfigured):
            keychain.get_service("not_configured")

    def test_change_key(self, keychain, org_config, service_configs):
        keychain.set_org(org_config)
        keychain.services = {"connected_app": {}, "github": {}}
        keychain.set_service("connected_app", "alias", service_configs["connected_app"])
        keychain.set_service("github", "alias", service_configs["github"])

        new_key = "9876543210987654"
        keychain.change_key(new_key)

        assert keychain.key == new_key
        assert keychain.get_org("test").config == org_config.config
        assert (
            keychain.get_service("github", "alias").config
            == service_configs["github"].config
        )
        assert (
            keychain.get_service("connected_app", "alias").config
            == service_configs["connected_app"].config
        )

    def test_set_service__github(self, keychain, service_conf):
        keychain.set_service("github", "alias", service_conf, project=False)
        assert keychain.get_service("github", "alias").config == service_conf.config

    def test_get_service__default_service(self, keychain):
        keychain._default_services = {"devhub": "baz"}
        keychain.config["services"] = {
            "devhub": {"foo": "config1", "bar": "config2", "baz": "config3"}
        }
        # If we don't specify an alias to get_service() we get
        # the default service for the given type
        default_github_service = keychain.get_service("devhub")

        assert default_github_service == "config3"

    def test_get_service__service_not_loaded(self, keychain, service_conf):
        keychain.project_config.config["services"] = {}
        with pytest.raises(
            ServiceNotValid,
            match=re.escape("Expecting services to be loaded, but none were found."),
        ):
            keychain.get_service("test-service", "alias").config == service_conf.config

    def test_get_service__service_type_not_in_config(self, keychain, service_conf):
        with pytest.raises(
            ServiceNotConfigured,
            match="Service type is not configured: test-service",
        ):
            keychain.get_service("test-service", "alias").config == service_conf.config

    def test_get_service__service_not_configured(self, keychain, service_conf):
        pass

    def test_get_service__DEFAULT_CONNECTED_APP(self, keychain, service_conf):
        service = keychain.get_service("connected_app", "alias")
        assert service is DEFAULT_CONNECTED_APP

    def test_set_service__private_method(self, keychain, service_conf):
        alias = "ziggy"
        keychain.services = {"github": {}}
        keychain._set_service("github", alias, service_conf, project=False)
        assert alias in keychain.services["github"].keys()
        assert keychain.services["github"][alias].config == service_conf.config

    def test_set_and_get_org(self, keychain, org_config):
        org_config.global_org = False
        keychain.set_org(org_config, global_org=False)
        assert list(keychain.orgs.keys()) == ["test"]
        assert keychain.get_org("test").config == org_config.config

    def test_set_and_get_scratch_org(self, keychain, scratch_org_config):
        keychain.set_org(scratch_org_config, global_org=False)
        assert list(keychain.orgs.keys()) == ["test_scratch"]
        org = keychain.get_org("test_scratch")
        assert org.config == scratch_org_config.config
        assert org.__class__ == ScratchOrgConfig

    def test_create_scratch_org(self, key):
        project_config = BaseProjectConfig(
            UniversalConfig, {"orgs": {"scratch": {"dev": {}}}}
        )
        keychain = BaseProjectKeychain(project_config, key)
        keychain.create_scratch_org("test", "dev", days=3)
        org_config = keychain.get_org("test").config
        assert org_config["days"] == 3

    def test_load_scratch_orgs(self, keychain):
        assert list(keychain.orgs) == []

    def test_get_org__existing_scratch_org(self, project_config, key):
        project_config.config["orgs"] = {}
        project_config.config["orgs"]["scratch"] = {}
        project_config.config["orgs"]["scratch"]["test_scratch_auto"] = {}
        keychain = BaseProjectKeychain(project_config, key)
        keychain._load_scratch_orgs()
        assert list(keychain.orgs) == ["test_scratch_auto"]

    def test_get_org__existing_org(self, project_config, key):
        project_config.config["orgs"] = {}
        project_config.config["orgs"]["scratch"] = {}
        project_config.config["orgs"]["scratch"]["test"] = {}

        keychain = BaseProjectKeychain(project_config, key)
        keychain.set_org(OrgConfig({}, "test"))

        assert list(keychain.orgs) == ["test"]
        org = keychain.get_org("test")
        assert org.scratch is None

    def test_get_org__not_found(self, keychain):
        with pytest.raises(OrgNotFound):
            keychain.get_org("test")

    @mock.patch("sarge.Command")
    def test_set_and_get_default_org(self, Command, keychain, org_config):
        org_config = OrgConfig({"created": True}, "test", keychain=keychain)
        org_config.save()
        keychain.set_default_org("test")
        org_config.config["default"] = True

        assert Command.call_count == 2
        assert keychain.get_default_org()[1].config == org_config.config

    @mock.patch("sarge.Command")
    def test_unset_default_org(self, Command, keychain, org_config):
        org_config = org_config.config.copy()
        org_config = OrgConfig(org_config, "test")
        org_config.config["default"] = True
        keychain.set_org(org_config)
        keychain.unset_default_org()

        Command.assert_called_once()
        assert keychain.get_default_org()[1] is None

    def test_list_orgs(self, keychain, org_config):
        keychain.set_org(org_config)
        assert keychain.list_orgs() == ["test"]

    def test_list_orgs__empty(self, keychain):
        assert keychain.list_orgs() == []

    def test_get_default_org__no_default(self, keychain):
        """Name and config for default org should be empty"""
        assert keychain.get_default_org() == (None, None)

    def test_validate_service_attributes(self, keychain):
        # config is missing the "name" attribute
        service_config = ServiceConfig({"password": "test123"})
        with pytest.raises(
            ServiceNotValid,
            match=re.escape("Missing required attribute(s) for service: ['name']"),
        ):
            keychain._validate_service_attributes("github", service_config)

    def test_validate_service_alias__same_as_service_type(self, keychain):
        with pytest.raises(
            ServiceNotValid,
            match=re.escape("Service alias cannot be the same as the service type."),
        ):
            keychain._validate_service_alias("service_type", "service_type")

    def test_validate_service_alias__same_as_default_alias(self, keychain):
        with pytest.raises(
            ServiceNotValid,
            match="Service alias cannot be the default alias: service_type__default",
        ):
            keychain._validate_service_alias("service_type", "service_type__default")

    def test_list_services(self, keychain):
        service_config = ServiceConfig({"foo": "bar"})
        keychain.services = {
            "devhub": {
                "foo_alias": service_config,
                "bar_alias": service_config,
            },
            "github": {
                "zed_alias": service_config,
                "zoo_alias": service_config,
            },
        }
        services = keychain.list_services()
        assert len(list(services.keys())) == 2
        assert services["devhub"] == ["bar_alias", "foo_alias"]
        assert services["github"] == ["zed_alias", "zoo_alias"]

    def test_convert_connected_app(self, key):
        project_config = BaseProjectConfig(
            UniversalConfig,
            {
                "services": {
                    "connected_app": {
                        "attributes": {
                            "callback_url": {},
                            "client_id": {},
                            "client_secret": {},
                        }
                    }
                }
            },
        )
        keychain = BaseProjectKeychain(project_config, key)
        app_config = {
            "callback_url": "http://localhost:8080/callback",
            "client_id": "CLIENT",
            "client_secret": "SECRET",
        }
        keychain.config["app"] = BaseConfig(app_config)
        keychain._convert_connected_app()
        actual_service = keychain.get_service(
            "connected_app", "please_contact_sfdo_releng"
        )
        assert app_config == actual_service.config

    @mock.patch("cumulusci.core.keychain.base_project_keychain.cleanup_org_cache_dirs")
    def test_remove_org(self, cleanup_org_cache_dirs, keychain, org_config):
        keychain.set_org(org_config)
        keychain.remove_org("test")
        assert "test" not in keychain.orgs
        assert cleanup_org_cache_dirs.called_once_with(keychain, project_config)
