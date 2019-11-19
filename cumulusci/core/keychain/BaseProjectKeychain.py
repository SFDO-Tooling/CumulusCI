import sarge

from cumulusci.core.config import BaseConfig
from cumulusci.core.config import ConnectedAppOAuthConfig
from cumulusci.core.config import ScratchOrgConfig
from cumulusci.core.config import ServiceConfig
from cumulusci.core.exceptions import OrgNotFound
from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci.core.exceptions import ServiceNotValid
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
        self.config = {"orgs": {}, "app": None, "services": {}}
        self.project_config = project_config
        self.key = key
        self._validate_key()
        self._load_keychain()

    def _convert_connected_app(self):
        """Convert Connected App to service"""
        if self.services and "connected_app" in self.services:
            # already a service
            return
        connected_app = self.get_connected_app()
        if not connected_app:
            # not configured
            return
        self.logger.warning(
            "Reading Connected App info from deprecated config."
            " Connected App should be changed to a service."
            " If using environment keychain, update the environment variable."
            " Otherwise, it has been handled automatically and you should not"
            " see this message again."
        )
        ca_config = ServiceConfig(
            {
                "callback_url": connected_app.callback_url,
                "client_id": connected_app.client_id,
                "client_secret": connected_app.client_secret,
            }
        )
        self.set_service("connected_app", ca_config)

    def _load_keychain(self):
        self._load_app()
        self._load_orgs()
        self._load_scratch_orgs()
        self._load_services()

    def _load_app(self):
        pass

    def _load_orgs(self):
        pass

    def _load_scratch_orgs(self):
        """ Creates all scratch org configs for the project in the keychain if
            a keychain org doesn't already exist """
        current_orgs = self.list_orgs()
        if not self.project_config.orgs__scratch:
            return
        for config_name in self.project_config.orgs__scratch.keys():
            if config_name in current_orgs:
                # Don't overwrite an existing keychain org
                continue
            self.create_scratch_org(config_name, config_name)

    def _load_services(self):
        pass

    def create_scratch_org(self, org_name, config_name, days=None, set_password=True):
        """ Adds/Updates a scratch org config to the keychain from a named config """
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
        org_config = ScratchOrgConfig(scratch_config, org_name)
        self.set_org(org_config)

    def change_key(self, key):
        """ re-encrypt stored services and orgs with the new key """

        services = {}
        for service_name in self.list_services():
            services[service_name] = self.get_service(service_name)

        orgs = {}
        for org_name in self.list_orgs():
            orgs[org_name] = self.get_org(org_name)

        self.key = key

        if orgs:
            for org_name, org_config in list(orgs.items()):
                self.set_org(org_config)

        if services:
            for service_name, service_config in list(services.items()):
                self.set_service(service_name, service_config)

        self._convert_connected_app()

    def get_connected_app(self):
        """ retrieve the connected app configuration """

        return self._get_connected_app()

    def _get_connected_app(self):
        return self.app

    def remove_org(self, name, global_org=None):
        if name in self.orgs.keys():
            self._remove_org(name, global_org)

    def _remove_org(self, name, global_org):
        del self.orgs[name]
        self._load_orgs()

    def set_org(self, org_config, global_org=False):
        if isinstance(org_config, ScratchOrgConfig):
            org_config.config["scratch"] = True
        self._set_org(org_config, global_org)
        self._load_orgs()

    def _set_org(self, org_config, global_org):
        self.orgs[org_config.name] = org_config

    def get_default_org(self):
        """ retrieve the name and configuration of the default org """
        for org in self.list_orgs():
            org_config = self.get_org(org)
            if org_config.default:
                return org, org_config
        return None, None

    def set_default_org(self, name):
        """ set the default org for tasks by name key """
        org = self.get_org(name)
        self.unset_default_org()
        org.config["default"] = True
        self.set_org(org)
        if org.created:
            sfdx(
                sarge.shell_format(
                    "force:config:set defaultusername={}", org.sfdx_alias
                )
            )

    def unset_default_org(self):
        """ unset the default orgs for tasks """
        for org in self.list_orgs():
            org_config = self.get_org(org)
            if org_config.default:
                del org_config.config["default"]
                self.set_org(org_config)
        sfdx("force:config:set defaultusername=")

    def get_org(self, name):
        """ retrieve an org configuration by name key """
        if name not in self.orgs:
            self._raise_org_not_found(name)
        org = self._get_org(name)
        org.keychain = self
        return org

    def _get_org(self, name):
        return self.orgs.get(name)

    def _raise_org_not_found(self, name):
        raise OrgNotFound(f"Org named {name} was not found in keychain")

    def list_orgs(self):
        """ list the orgs configured in the keychain """
        orgs = list(self.orgs.keys())
        orgs.sort()
        return orgs

    def set_service(self, name, service_config, project=False):
        """ Store a ServiceConfig in the keychain """
        if not self.project_config.services or name not in self.project_config.services:
            self._raise_service_not_valid(name)
        self._validate_service(name, service_config)
        self._set_service(name, service_config, project)
        self._load_services()

    def _set_service(self, name, service_config, project=False):
        self.services[name] = service_config

    def get_service(self, name):
        """ Retrieve a stored ServiceConfig from the keychain or exception

        :param name: the service name to retrieve
        :type name: str

        :rtype ServiceConfig
        :return the configured Service
        """
        self._convert_connected_app()
        if not self.project_config.services or name not in self.project_config.services:
            self._raise_service_not_valid(name)
        if name not in self.services:
            if name == "connected_app":
                return DEFAULT_CONNECTED_APP
            self._raise_service_not_configured(name)

        return self._get_service(name)

    def _get_service(self, name):
        return self.services.get(name)

    def _validate_key(self):
        pass

    def _validate_service(self, name, service_config):
        missing_required = []
        attr_key = f"services__{name}__attributes"
        for atr, config in list(getattr(self.project_config, attr_key).items()):
            if config.get("required") is True and not getattr(service_config, atr):
                missing_required.append(atr)

        if missing_required:
            self._raise_service_not_valid(name)

    def _raise_service_not_configured(self, name):
        services = ", ".join(list(self.services))
        raise ServiceNotConfigured(
            f"Service named {name} is not configured for this project. Configured services are: {services}"
        )

    def _raise_service_not_valid(self, name):
        raise ServiceNotValid(f"Service named {name} is not valid for this project")

    def list_services(self):
        """ list the services configured in the keychain """
        services = list(self.services.keys())
        services.sort()
        return services
