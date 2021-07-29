import json
import os

from cumulusci.core.config import OrgConfig, ScratchOrgConfig, ServiceConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.keychain.base_project_keychain import DEFAULT_CONNECTED_APP_NAME
from cumulusci.core.utils import import_global

scratch_org_class = os.environ.get("CUMULUSCI_SCRATCH_ORG_CLASS")
if scratch_org_class:
    scratch_org_factory = import_global(scratch_org_class)  # pragma: no cover
else:
    scratch_org_factory = ScratchOrgConfig


class EnvironmentProjectKeychain(BaseProjectKeychain):
    """A project keychain that stores org credentials in environment variables"""

    encrypted = False
    org_var_prefix = "CUMULUSCI_ORG_"
    app_var = "CUMULUSCI_CONNECTED_APP"
    service_var_prefix = "CUMULUSCI_SERVICE_"

    def _get_env(self):
        """loads the environment variables as unicode if ascii"""
        env = {}
        for k, v in os.environ.items():
            k = k.decode() if isinstance(k, bytes) else k
            v = v.decode() if isinstance(v, bytes) else v
            env[k] = v
        return list(env.items())

    def _load_orgs(self):
        for key, value in self._get_env():
            if key.startswith(self.org_var_prefix):
                org_config = json.loads(value)
                org_name = key[len(self.org_var_prefix) :].lower()
                if org_config.get("scratch"):
                    self.orgs[org_name] = scratch_org_factory(
                        json.loads(value), org_name, keychain=self, global_org=False
                    )
                else:
                    self.orgs[org_name] = OrgConfig(
                        json.loads(value), org_name, keychain=self, global_org=False
                    )

    def _load_services(self):
        for key, value in self._get_env():
            if key.startswith(self.service_var_prefix):
                service_config = json.loads(value)
                service_type = key[len(self.service_var_prefix) :].lower()
                self._set_service(service_type, "env", ServiceConfig(service_config))

    def _load_default_services(self):
        for service_type in self.services:
            self._default_services[service_type] = "env"

        # If there are no connected_app services loaded
        # then set the built-in connected_app as the default.
        # The built-in is always loaded, so 2 or more would indicate
        # the presence of a user-provided connected app.
        if len(self.config["services"]["connected_app"]) == 1:
            self._default_services["connected_app"] = DEFAULT_CONNECTED_APP_NAME

    def cleanup_org_cache_dirs(self):
        pass
