import re
from unittest import mock

import pytest

from cumulusci.core.config import (
    BaseProjectConfig,
    OrgConfig,
    ScratchOrgConfig,
    ServiceConfig,
    UniversalConfig,
)
from cumulusci.core.exceptions import (
    CumulusCIException,
    OrgNotFound,
    ServiceNotConfigured,
    ServiceNotValid,
)
from cumulusci.core.keychain import DEFAULT_CONNECTED_APP, BaseProjectKeychain


@pytest.fixture
def service_configs():
    return {
        "connected_app": ServiceConfig({"test": "value"}),
        "github": ServiceConfig({"name": "hub"}),
    }


@pytest.fixture
def scratch_org_config():
    return ScratchOrgConfig({"foo": "bar", "scratch": True}, "test_scratch")


@pytest.fixture()
def keychain(project_config, key):
    keychain = BaseProjectKeychain(project_config, key)
    assert keychain.project_config == project_config
    assert keychain.key == key
    return keychain


class TestBaseProjectKeychain:
    @pytest.mark.parametrize("key", ["0123456789123456", None])
    def test_set_non_existant_service(self, project_config, key):
        keychain = BaseProjectKeychain(project_config, key)
        keychain.key = key
        with pytest.raises(ServiceNotValid):
            keychain.set_service("doesnotexist", "alias", ServiceConfig({"name": ""}))

    def test_set_invalid_service(self, keychain):
        with pytest.raises(ServiceNotValid):
            keychain.set_service("github", "alias", ServiceConfig({"name": ""}))

    def test_get_service__type_not_in_configuration(self, keychain):
        """This service is not listed as a service type in cumulusci.yml"""
        with pytest.raises(ServiceNotConfigured):
            keychain.get_service("not_in_configuration")

    def test_get_service__alias_not_found(self, keychain):
        """This service is not listed as a service type in cumulusci.yml"""
        with pytest.raises(ServiceNotConfigured):
            keychain.get_service("connected_app", "not-in-configuration")

    def test_get_service_not_configured(self, keychain):
        """This service is supported by CumulusCI but is not currently configured"""
        with pytest.raises(ServiceNotConfigured):
            keychain.get_service("not_configured")

    def test_set_service__github(self, keychain, service_config):
        keychain.set_service("github", "alias", service_config)
        assert keychain.get_service("github", "alias").config == service_config.config

    def test_get_service__default_service(self, keychain):
        keychain._default_services = {"devhub": "baz"}
        keychain.config["services"] = {
            "devhub": {"foo": "config1", "bar": "config2", "baz": "config3"}
        }
        # If we don't specify an alias to get_service() we get
        # the default service for the given type
        default_github_service = keychain.get_service("devhub")

        assert default_github_service == "config3"

    def test_get_service__default_service_not_set(self, keychain):
        keychain._default_services = {"github": "baz"}
        keychain.config["services"] = {
            "devhub": {"foo": "config1", "bar": "config2", "baz": "config3"}
        }

        with pytest.raises(
            CumulusCIException,
            match="No default service currently set for service type: devhub",
        ):
            keychain.get_service("devhub")

    def test_get_service__service_not_loaded(self, keychain, service_config):
        keychain.project_config.config["services"] = {}
        with pytest.raises(
            ServiceNotValid,
            match=re.escape("Expecting services to be loaded, but none were found."),
        ):
            keychain.get_service(
                "test-service", "alias"
            ).config == service_config.config

    def test_get_service__service_type_not_in_config(self, keychain, service_config):
        with pytest.raises(
            ServiceNotConfigured,
            match="Service type is not configured: test-service",
        ):
            keychain.get_service(
                "test-service", "alias"
            ).config == service_config.config

    def test_get_service__DEFAULT_CONNECTED_APP(self, keychain):
        keychain._load_default_connected_app()
        service = keychain.get_service("connected_app")
        assert service is DEFAULT_CONNECTED_APP

    def test_set_service__private_method(self, keychain, service_config):
        alias = "ziggy"
        keychain.services = {"github": {}}
        keychain._set_service("github", alias, service_config)
        assert alias in keychain.services["github"].keys()
        assert keychain.services["github"][alias].config == service_config.config

    @pytest.mark.parametrize(
        "service_type,expected", [("github", "foo"), ("connected_app", None)]
    )
    def test_get_default_service_name(self, service_type, expected, keychain):
        keychain._default_services = {"github": "foo"}
        assert keychain.get_default_service_name(service_type) == expected

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

    @pytest.mark.parametrize("key", ["0123456789123456", None])
    def test_create_scratch_org(self, key):
        project_config = BaseProjectConfig(
            UniversalConfig, {"orgs": {"scratch": {"dev": {}}}}
        )
        keychain = BaseProjectKeychain(project_config, key)
        keychain.key = key
        keychain.create_scratch_org("test", "dev", days=3, release="previous")
        org_config = keychain.get_org("test").config
        assert org_config["days"] == 3
        assert org_config["release"] == "previous"

    def test_load_scratch_orgs(self, keychain):
        assert list(keychain.orgs) == []

    @pytest.mark.parametrize("key", ["0123456789123456", None])
    def test_get_org__existing_scratch_org(self, project_config, key):
        project_config.config["orgs"] = {}
        project_config.config["orgs"]["scratch"] = {}
        project_config.config["orgs"]["scratch"]["test_scratch_auto"] = {}
        keychain = BaseProjectKeychain(project_config, key)
        keychain.key = key
        keychain._load_scratch_orgs()
        assert list(keychain.orgs) == ["test_scratch_auto"]

    @pytest.mark.parametrize("key", ["0123456789123456", None])
    def test_get_org__existing_org(self, project_config, key):
        project_config.config["orgs"] = {}
        project_config.config["orgs"]["scratch"] = {}
        project_config.config["orgs"]["scratch"]["test"] = {}

        keychain = BaseProjectKeychain(project_config, key)
        keychain.key = key
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
        error_message = re.escape(
            "Missing required attribute(s) for github service: ['name']"
        )
        with pytest.raises(
            ServiceNotValid,
            match=error_message,
        ):
            keychain._validate_service_attributes("github", service_config)

    def test_validate_service_alias__same_as_service_type(self, keychain):
        with pytest.raises(
            ServiceNotValid,
            match=re.escape("Service name cannot be the same as the service type."),
        ):
            keychain._validate_service_alias("service_type", "service_type")

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

    def test_get_services_for_type(self, keychain):
        service_config = ServiceConfig({"foo": "bar"})
        keychain.services = {
            "devhub": {
                "foo_alias": service_config,
                "bar_alias": service_config,
            },
            "github": {
                "zed_alias": service_config,
                "zoo_alias": service_config,
                "zap_alias": service_config,
            },
            "github_enterprise": {
                "meep_alias": service_config,
                "morp_alias": service_config,
            },
        }
        devhub_services = keychain.get_services_for_type("devhub")
        github_services = keychain.get_services_for_type("github")
        ghent_services = keychain.get_services_for_type("github_enterprise")

        assert len(devhub_services) == 2
        assert len(github_services) == 3
        assert len(ghent_services) == 2

    def test_remove_org(
        self,
        keychain,
        org_config,
    ):
        keychain.cleanup_org_cache_dirs = mock.Mock()
        keychain.set_org(org_config)
        keychain.remove_org("test")
        assert "test" not in keychain.orgs
        keychain.cleanup_org_cache_dirs.assert_called_once()

    def test_org_definition__missing(self, project_config, key):
        """What if a scratch org was created with a YAML definition which was deleted more recently?"""
        keychain = BaseProjectKeychain(project_config, key)
        with pytest.raises(OrgNotFound, match="No such org"):
            keychain.create_scratch_org("no_such_org", "no_such_org")
