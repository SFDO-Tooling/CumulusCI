import sarge

from cumulusci.core.config import BaseConfig, ConnectedAppOAuthConfig, ScratchOrgConfig
from cumulusci.core.exceptions import (
    CumulusCIException,
    OrgNotFound,
    ServiceNotConfigured,
    ServiceNotValid,
)
from cumulusci.core.sfdx import sfdx

DEFAULT_CONNECTED_APP = ConnectedAppOAuthConfig(
    {
        "client_id": "3MVG9i1HRpGLXp.or6OVlWVWyn8DXi9xueKNM4npq_AWh.yqswojK9sE5WY7f.biP0w7bNJIENfXc7JMDZGO1",
        "client_secret": None,
        "callback_url": "http://localhost:8080/callback",
    }
)


class BaseProjectKeychain(BaseConfig):
    encrypted = False

    def __init__(self, project_config, key):
        super(BaseProjectKeychain, self).__init__()
        self.config = {
            "orgs": {},
            "app": None,
            "services": {},
        }
        self.project_config = project_config
        self._default_services = {}
        self.key = key
        self._validate_key()
        self._load_keychain()

    def _load_keychain(self):
        self._load_orgs()
        self._load_scratch_orgs()
        self._load_services()
        self._load_default_services()

    def _validate_key(self):
        pass

    #######################################
    #               Orgs                  #
    #######################################

    def _load_orgs(self):
        pass

    def _load_scratch_orgs(self):
        """Creates all scratch org configs for the project in the keychain if
        a keychain org doesn't already exist"""
        current_orgs = self.list_orgs()
        if not self.project_config.orgs__scratch:
            return
        for config_name in self.project_config.orgs__scratch.keys():
            if config_name in current_orgs:
                # Don't overwrite an existing keychain org
                continue
            self.create_scratch_org(config_name, config_name)

    def create_scratch_org(self, org_name, config_name, days=None, set_password=True):
        """Adds/Updates a scratch org config to the keychain from a named config"""
        scratch_config = getattr(self.project_config, f"orgs__scratch__{config_name}")
        if days is not None:
            # Allow override of scratch config's default days
            scratch_config["days"] = days
        else:
            # Use scratch config days or default of 1 day
            scratch_config.setdefault("days", 1)
        scratch_config["set_password"] = bool(set_password)
        scratch_config["scratch"] = True
        scratch_config.setdefault("namespaced", False)
        scratch_config["config_name"] = config_name
        scratch_config[
            "sfdx_alias"
        ] = f"{self.project_config.project__name}__{org_name}"
        org_config = ScratchOrgConfig(
            scratch_config, org_name, keychain=self, global_org=False
        )
        org_config.save()

    def set_org(self, org_config, global_org=False):
        if isinstance(org_config, ScratchOrgConfig):
            org_config.config["scratch"] = True
        self._set_org(org_config, global_org)
        self._load_orgs()

    def _set_org(self, org_config, global_org):
        self.orgs[org_config.name] = org_config

    def set_default_org(self, name):
        """set the default org for tasks and flows by name"""
        org = self.get_org(name)
        self.unset_default_org()
        org.config["default"] = True
        org.save()
        if org.created:
            sfdx(
                sarge.shell_format(
                    "force:config:set defaultusername={}", org.sfdx_alias
                )
            )

    def unset_default_org(self):
        """unset the default orgs for tasks"""
        for org in self.list_orgs():
            org_config = self.get_org(org)
            if org_config.default:
                del org_config.config["default"]
                org_config.save()
        sfdx("force:config:set defaultusername=")

    def get_org(self, name: str):
        """retrieve an org configuration by name key"""
        if name not in self.orgs:
            self._raise_org_not_found(name)
        org = self._get_org(name)
        if org.keychain:
            assert org.keychain is self
        else:
            org.keychain = self
        return org

    def _get_org(self, name):
        return self.orgs.get(name)

    # This implementation of get_default_org, set_default_org, and unset_default_org
    # is currently kept for backwards compatibility, but EncryptedFileProjectKeychain
    # now stores the default elsewhere, and EnvironmentProjectKeychain doesn't actually
    # persist across multiple invocations of cci, so we should consider getting rid of this.

    def get_default_org(self):
        """retrieve the name and configuration of the default org"""
        for org in self.list_orgs():
            org_config = self.get_org(org)
            if org_config.default:
                return org, org_config
        return None, None

    def remove_org(self, name, global_org=None):
        if name in self.orgs.keys():
            self._remove_org(name, global_org)
        self.cleanup_org_cache_dirs()

    def _remove_org(self, name, global_org):
        del self.orgs[name]
        self._load_orgs()

    def list_orgs(self):
        """list the orgs configured in the keychain"""
        orgs = list(self.orgs.keys())
        orgs.sort()
        return orgs

    def _raise_org_not_found(self, name):
        raise OrgNotFound(f"Org named {name} was not found in keychain")

    def cleanup_org_cache_dirs(self):
        pass

    #######################################
    #              Services               #
    #######################################

    def _load_services(self):
        pass

    def _load_default_services(self):
        pass

    def set_service(self, service_type, alias, service_config):
        """Store a ServiceConfig in the keychain"""
        self._validate_service(service_type, alias, service_config)
        self._set_service(service_type, alias, service_config)
        self._load_services()

    def _set_service(self, service_type, alias, service_config):
        if service_type not in self.services:
            self.services[service_type] = {}
            self._default_services[service_type] = alias

        self.services[service_type][alias] = service_config

    def get_service(self, service_type, alias=None):
        """Retrieve a stored ServiceConfig from the keychain.
        If no alias is specified then the default service for
        the given type is returned.

        @param service_type: the service to retrieve e.g. 'github'
        @param alias: the alias of the service
        @returns: ServiceConfig for the requested service
        """
        if not self.project_config.services:
            raise ServiceNotValid(
                "Expecting services to be loaded, but none were found."
            )
        elif service_type not in self.project_config.services:
            raise ServiceNotConfigured(
                f"Service type is not configured: {service_type}"
            )

        if service_type not in self.services:
            if service_type == "connected_app":
                return DEFAULT_CONNECTED_APP
            self._raise_service_not_configured(service_type)

        if not alias:
            alias = self._default_services.get(service_type)
            if not alias:
                raise CumulusCIException(
                    f"No default service currently set for service type: {service_type}"
                )
        service = self._get_service(service_type, alias)

        # transparent migration of github API tokens to new key
        if service_type == "github" and service.password and not service.token:
            service.config["token"] = service.password

        return service

    def _get_service(self, service_type, alias):
        return self.services[service_type][alias]

    def _validate_service(self, service_type, alias, config):
        if (
            not self.project_config.services
            or service_type not in self.project_config.services
        ):
            self._raise_service_not_valid(service_type)

        self._validate_service_alias(service_type, alias)
        self._validate_service_attributes(service_type, config)

    def _validate_service_attributes(self, service_type, service_config):
        """
        Validate that all of the required attributes for a
        given service are present.
        """
        missing_required = []
        attr_key = f"services__{service_type}__attributes"
        for atr, config in list(getattr(self.project_config, attr_key).items()):
            if config.get("required") and not getattr(service_config, atr):
                missing_required.append(atr)

        if missing_required:
            raise ServiceNotValid(
                f"Missing required attribute(s) for service: {missing_required}"
            )

    def _validate_service_alias(self, service_type, alias):
        if alias == service_type:
            raise ServiceNotValid(
                "Service name cannot be the same as the service type."
            )

    def _raise_service_not_configured(self, name):
        services = ", ".join(list(self.services))
        raise ServiceNotConfigured(
            f"Service named {name} is not configured for this project. Configured services are: {services}"
        )

    def _raise_service_not_valid(self, name):
        raise ServiceNotValid(f"Service named {name} is not valid for this project")

    def list_services(self):
        """list the services configured in the keychain"""
        service_types = list(self.services.keys())
        service_types.sort()

        services = {}
        for s_type in service_types:
            if s_type not in services:
                services[s_type] = []
            names = list(self.services[s_type].keys())
            names.sort()
            for name in names:
                services[s_type].append(name)
        return services

    @property
    def cache_dir(self):
        "Helper function to get the cache_dir from the project_config"
        return self.project_config.cache_dir  # pragma: no cover
