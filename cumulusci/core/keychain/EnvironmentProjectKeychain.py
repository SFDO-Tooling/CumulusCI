import json
import os

from cumulusci.core.config import ConnectedAppOAuthConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import ScratchOrgConfig
from cumulusci.core.config import ServiceConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.utils import import_global

scratch_org_class = os.environ.get("CUMULUSCI_SCRATCH_ORG_CLASS")
if scratch_org_class:
    scratch_org_factory = import_global(scratch_org_class)
else:
    scratch_org_factory = ScratchOrgConfig


class EnvironmentProjectKeychain(BaseProjectKeychain):
    """ A project keychain that stores org credentials in environment variables """

    encrypted = False
    org_var_prefix = "CUMULUSCI_ORG_"
    app_var = "CUMULUSCI_CONNECTED_APP"
    service_var_prefix = "CUMULUSCI_SERVICE_"

    def _get_env(self):
        """ loads the environment variables as unicode if ascii """
        env = {}
        for k, v in os.environ.items():
            k = k.decode() if isinstance(k, bytes) else k
            v = v.decode() if isinstance(v, bytes) else v
            env[k] = v
        return list(env.items())

    def _load_app(self):
        app = os.environ.get(self.app_var)
        if app:
            self.app = ConnectedAppOAuthConfig(json.loads(app))

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
                service_name = key[len(self.service_var_prefix) :].lower()
                self._set_service(service_name, ServiceConfig(service_config))
