from __future__ import print_function
import json
import os

from cumulusci.core.config import ConnectedAppOAuthConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import ScratchOrgConfig
from cumulusci.core.config import ServiceConfig
from cumulusci.core.keychain import BaseProjectKeychain


class EnvironmentProjectKeychain(BaseProjectKeychain):
    """ A project keychain that stores org credentials in environment variables """
    encrypted = False
    org_var_prefix = 'CUMULUSCI_ORG_'
    app_var = 'CUMULUSCI_CONNECTED_APP'
    service_var_prefix = 'CUMULUSCI_SERVICE_'

    def _get_env(self):
        """ loads the environment variables as unicode if ascii """
        try:
            return [(k.decode(), v.decode()) for k,v in list(os.environ.items())]
        except AttributeError:
            return list(os.environ.items())

    def _load_app(self):
        try:
            app = os.environ.get(self.app_var.encode('ascii'))
        except TypeError:
            app = os.environ.get(self.app_var)
        if app:
            self.app = ConnectedAppOAuthConfig(json.loads(app))

    def _load_orgs(self):
        for key, value in self._get_env():
            if key.startswith(self.org_var_prefix):
                org_config = json.loads(value)
                org_name = key[len(self.org_var_prefix):].lower()
                if org_config.get('scratch'):
                    self.orgs[org_name] = ScratchOrgConfig(json.loads(value), org_name)
                else:
                    self.orgs[org_name] = OrgConfig(json.loads(value), org_name)

    def _load_services(self):
        for key, value in self._get_env():
            if key.startswith(self.service_var_prefix):
                service_config = json.loads(value)
                service_name = key[len(self.service_var_prefix):].lower()
                self._set_service(service_name, ServiceConfig(service_config))
