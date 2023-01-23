import sarge

from cumulusci.core.config import ConnectedAppOAuthConfig, ServiceConfig
from cumulusci.core.config.base_config import BaseConfig
from cumulusci.core.config.scratch_org_config import ScratchOrgConfig
from cumulusci.core.exceptions import (
    CumulusCIException,
    CumulusCIUsageError,
    OrgNotFound,
    ServiceNotConfigured,
    ServiceNotValid,
)
from cumulusci.core.sfdx import sfdx

DEFAULT_CONNECTED_APP_PORT = 7788
DEFAULT_CONNECTED_APP_NAME = "built-in"
DEFAULT_CONNECTED_APP = ConnectedAppOAuthConfig(
    {
        "client_id": "3MVG9i1HRpGLXp.or6OVlWVWyn8DXi9xueKNM4npq_AWh.yqswojK9sE5WY7f.biP0w7bNJIENfXc7JMDZGO1",
        "client_secret": None,
        "callback_url": f"http://localhost:{DEFAULT_CONNECTED_APP_PORT}/callback",
    }
)


class BaseProjectKeychain(BaseConfig):
    encrypted = False
    orgs: dict
    services: dict

    def __init__(self, project_config, key):
        super(BaseProjectKeychain, self).__init__()
        self.config = {
            "orgs": {},
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
        self._load_default_connected_app()
        self._load_services()
        self._load_default_services()

    def _validate_key(self):
        pass

    #######################################
    #               Orgs                  #
    #######################################

    def create_scratch_org(self, org_name, config_name, days=None, set_password=True):
        """Adds/Updates a scratch org config to the keychain from a named config"""
        scratch_config = self.project_config.lookup(f"orgs__scratch__{config_name}")
        if scratch_config is None:
            raise OrgNotFound(f"No such org configured: `{config_name}`")
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

    def set_org(self, org_config, global_org=False, save=True):
        if isinstance(org_config, ScratchOrgConfig):
            org_config.config["scratch"] = True
        self._set_org(org_config, global_org, save=save)

    def set_default_org(self, name):
        """set the default org for tasks and flows by name"""
        org = self.get_org(name)
        assert org is not None
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
            assert org_config is not None
            if org_config.default:
                del org_config.config["default"]
                org_config.save()
        sfdx("force:config:set defaultusername=")

    # This implementation of get_default_org, set_default_org, and unset_default_org
    # is currently kept for backwards compatibility, but EncryptedFileProjectKeychain
    # now stores the default elsewhere, and EnvironmentProjectKeychain doesn't actually
    # persist across multiple invocations of cci, so we should consider getting rid of this.

    def get_default_org(self):
        """retrieve the name and configuration of the default org"""
        for org in self.list_orgs():
            org_config = self.get_org(org)
            assert org_config is not None
            if org_config.default:
                return org, org_config
        return None, None

    def get_org(self, name: str):
        """retrieve an org configuration by name key"""
        org = self._get_org(name)
        assert org
        if org.keychain:
            assert org.keychain is self
        else:
            org.keychain = self
        return org

    def list_orgs(self):
        """list the orgs configured in the keychain"""
        orgs = list(self.orgs.keys())
        orgs.sort()
        return orgs

    def remove_org(self, name, global_org=None):
        if name in self.orgs.keys():
            self._remove_org(name, global_org)
        self.cleanup_org_cache_dirs()

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

    def _set_org(self, org_config, global_org, save=True):
        self.orgs[org_config.name] = org_config

    def _get_org(self, name):
        if name not in self.orgs:
            raise OrgNotFound(f"Org named {name} was not found in keychain")
        return self.orgs.get(name)

    def _remove_org(self, name, global_org):
        del self.orgs[name]
        self._load_orgs()

    def cleanup_org_cache_dirs(self):
        pass  # pragma: no cover

    #######################################
    #              Services               #
    #######################################

    def set_default_service(
        self, service_type: str, alias: str, project: bool = False, save: bool = True
    ) -> None:
        """Public API for setting a default service e.g. `cci service default`

        @param service_type: the type of service
        @param alias: the name of the service
        @param project: Should this be a project default
        @param save: save the defaults so they are loaded on subsequent executions
        @raises ServiceNotConfigured if service_type or alias are invalid
        """
        self._validate_service_type_and_alias(service_type, alias)
        self._default_services[service_type] = alias

    def get_default_service_name(self, service_type: str):
        """Returns the name of the default service for the given type
        or None if no default is currently set for the given type."""
        try:
            return self._default_services[service_type]
        except KeyError:
            return None

    def set_service(
        self,
        service_type: str,
        alias: str,
        service_config: ServiceConfig,
        save: bool = True,
        config_encrypted: bool = False,
    ):
        """Store a ServiceConfig in the keychain
        @service_type - type of service
        @alias - name that the service will be stored under
        @service_config - dict of service attributes
        @save - If true, indicates that the service
        should be saved in some manner (subclasses implement).
        @config_encrypted - Indicates whether or not the config
        is already encrypted (as can be the case when reading
        services back from an encrypted file).
        """
        # we only validate attributes when they aren't encrypted
        # if we are setting a service from an encrypted file then it has already been validated
        if not config_encrypted:
            self._validate_service(service_type, alias, service_config)
        self._set_service(
            service_type,
            alias,
            service_config,
            save=save,
            config_encrypted=config_encrypted,
        )

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
            self._raise_service_not_configured(service_type)

        if not alias:
            alias = self.get_default_service_name(service_type)
            if not alias:
                raise CumulusCIException(
                    f"No default service currently set for service type: {service_type}"
                )
        service = self._get_service(service_type, alias)

        # transparent migration of github API tokens to new key
        if service_type == "github" and service.password and not service.token:
            service.config["token"] = service.password

        return service

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

    def get_services_for_type(self, service_type: str) -> list:
        return [
            self.get_service(service_type, alias)
            for alias in self.list_services().get(service_type, [])
        ]

    def rename_service(
        self, service_type: str, current_alias: str, new_alias: str
    ) -> None:
        """Public API for renaming a service

        @param service_type type of service being renamed
        @param current_alias the current alias of the service
        @param new_alias the new alias for the service
        @throws: ServiceNotValid if no services of the given type are configured,
        or if no service of the given type has the current_alias
        """
        if (
            service_type == "connected_app"
            and current_alias == DEFAULT_CONNECTED_APP_NAME
        ):
            raise CumulusCIException(
                "You cannot rename the connected app service that is provided by CumulusCI."
            )

        self._validate_service_type_and_alias(service_type, current_alias)
        if new_alias in self.services[service_type]:
            raise CumulusCIUsageError(
                f"A service of type {service_type} already exists with name: {new_alias}"
            )

        self.services[service_type][new_alias] = self.services[service_type].pop(
            current_alias
        )

        if self._default_services.get(service_type) == current_alias:
            self._default_services[service_type] = new_alias

    def remove_service(self, service_type: str, alias: str):
        """Removes the given service from the keychain. If the service
        is the default service, and there is only one other service
        of the same type, that service is set as the new default.

        @param service_type type of the service
        @param alias the name of the service
        @raises ServiceNotConfigured if the service_type or alias are invalid
        """
        if service_type == "connected_app" and alias == DEFAULT_CONNECTED_APP_NAME:
            raise CumulusCIException(
                f"Unable to remove connected app service: {DEFAULT_CONNECTED_APP_NAME}. "
                "This connected app is provided by CumulusCI and cannot be removed."
            )

        self._validate_service_type_and_alias(service_type, alias)
        # remove the loaded service from the keychain
        del self.services[service_type][alias]

        # if set, remove the service as the default
        if alias == self._default_services[service_type]:
            del self._default_services[service_type]
            if len(self.services[service_type].keys()) == 1:
                alias = self.list_services()[service_type][0]
                self.set_default_service(service_type, alias, project=False)

    def _load_services(self):
        pass

    def _load_default_services(self):
        self._default_services["connected_app"] = DEFAULT_CONNECTED_APP_NAME

    def _load_default_connected_app(self):
        """Load the default connected app as a first class service on the keychain."""
        if "connected_app" not in self.config["services"]:
            self.config["services"]["connected_app"] = {}
        self.config["services"]["connected_app"][
            DEFAULT_CONNECTED_APP_NAME
        ] = DEFAULT_CONNECTED_APP

    def _set_service(
        self, service_type, alias, service_config, save=True, config_encrypted=False
    ):
        # The first service of a given service_type automatically becomes the default
        if service_type not in self.services:
            self.services[service_type] = {}
            self._default_services[service_type] = alias

        self.services[service_type][alias] = service_config

    def _get_service(self, service_type, alias):
        try:
            return self.services[service_type][alias]
        except KeyError:
            raise ServiceNotConfigured(
                f"No service of type {service_type} configured with name: {alias}"
            )

    def _validate_service(self, service_type, alias, config):
        if (
            not self.project_config.services
            or service_type not in self.project_config.services
        ):
            raise ServiceNotValid(
                f"Service named {alias} is not valid for this project"
            )

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
            if config.get("required") and not service_config.lookup(atr):
                missing_required.append(atr)

        if missing_required:
            if service_type == "github" and missing_required == ["token"]:
                service_config.token = service_config.password
                return

            raise ServiceNotValid(
                f"Missing required attribute(s) for {service_type} service: {missing_required}"
            )

    def _validate_service_alias(self, service_type, alias):
        if alias == service_type:
            raise ServiceNotValid(
                "Service name cannot be the same as the service type."
            )
        if service_type == "connected_app" and alias == DEFAULT_CONNECTED_APP_NAME:
            raise ServiceNotValid(
                f"You cannot use the name {DEFAULT_CONNECTED_APP_NAME} for a connected app service. Please select a different name."
            )

    def _validate_service_type_and_alias(self, service_type, alias):
        """Raises ServiceNotConfigured exception if the service_type
        or alias are not valid."""
        if service_type not in self.services:
            raise ServiceNotConfigured(
                f"No services of type {service_type} are currently configured"
            )
        elif alias not in self.services[service_type]:
            raise ServiceNotConfigured(
                f"No service of type {service_type} configured with the name: {alias}"
            )

    def _raise_service_not_configured(self, service_type):
        service_types = ", ".join(list(self.services))
        raise ServiceNotConfigured(
            f"Service type {service_type} is not configured for this project. Configured services are: {service_types}"
        )

    @property
    def cache_dir(self):
        "Helper function to get the cache_dir from the project_config"
        return self.project_config.cache_dir  # pragma: no cover
