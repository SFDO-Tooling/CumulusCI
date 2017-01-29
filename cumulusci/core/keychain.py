import base64
import json
import os
import pickle

from Crypto import Random
from Crypto.Cipher import AES

from cumulusci.core.config import BaseConfig
from cumulusci.core.config import ConnectedAppOAuthConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import ScratchOrgConfig
from cumulusci.core.config import ServiceConfig
from cumulusci.core.exceptions import OrgNotFound
from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci.core.exceptions import KeychainConnectedAppNotFound

class BaseProjectKeychain(BaseConfig):
    encrypted = False

    def __init__(self, project_config, key):
        super(BaseProjectKeychain, self).__init__()
        self.config = {
            'orgs': {}, 
            'app': None, 
            'services': {},
        }
        self.project_config = project_config
        self.key = key
        self._load_keychain()

    def _load_keychain(self):
        """ Subclasses can override to implement logic to load the keychain """
        pass

    def change_key(self, key):
        connected_app = self.get_connected_app()

        services = {}
        for service_name in self.list_services():
            services[service_name] = self.get_service(service_name)

        orgs = {}
        for org_name in self.list_orgs():
            orgs[org_name] = self.get_org(org_name)

        self.key = key
        if connected_app:
            self.set_connected_app(connected_app)

        if orgs:
            for org_name, org_config in orgs.items():
                self.set_org(org_name, org_config)

        if services:
            for service_name, service_config in services.items():
                self.set_service(service_name, service_config)

    def set_connected_app(self, app_config, project=False):
        self._set_connected_app(app_config, project)
        self._load_keychain()
    
    def _set_connected_app(self, app_config, project):
        self.app = app_config

    def get_connected_app(self):
        return self._get_connected_app()

    def _get_connected_app(self):
        return self.app

    def set_org(self, name, org_config, global_org=False):
        if isinstance(org_config, ScratchOrgConfig):
            org_config.config['scratch'] = True
        self._set_org(name, org_config, global_org)
        self._load_keychain()

    def _set_org(self, name, org_config, global_org):
        self.orgs[name] = org_config

    def get_default_org(self):
        for org in self.list_orgs():
            org_config = self.get_org(org)
            if org_config.default:
                return org, org_config
        return None, None

    def set_default_org(self, name):
        org = self.get_org(name)
        self.unset_default_org()
        org.config['default'] = True
        self.set_org(name, org)
        
    def unset_default_org(self):
        for org in self.list_orgs():
            org_config = self.get_org(org)
            if org_config.default:
                del org_config.config['default']
                self.set_org(org, org_config)

    def get_org(self, name):
        if name not in self.orgs:
            self._raise_org_not_found(name)
        return self._get_org(name)

    def _get_org(self, name):
        return self.orgs.get(name)
    
    def _raise_org_not_found(self, name):
        raise OrgNotFound('Org named {} was not found in keychain'.format(name))

    def list_orgs(self):
        orgs = self.orgs.keys()
        orgs.sort()
        return orgs

    def set_service(self, name, service_config, project=False):
        self._set_service(name, service_config, project)
        self._load_keychain()

    def _set_service(self, name, service_config, project):
        self.services[name] = service_config

    def get_service(self, name):
        if name not in self.services:
            self._raise_service_not_configured(name)
        return self._get_service(name)

    def _get_service(self, name):
        return self.services.get(name)
    
    def _raise_service_not_configured(self, name):
        raise ServiceNotConfigured('Service named {} is not configured for this project'.format(name))

    def list_services(self):
        services = self.services.keys()
        services.sort()
        return services

class EnvironmentProjectKeychain(BaseProjectKeychain):
    """ A project keychain that stores org credentials in environment variables """ 
    encrypted = False
    org_var_prefix = 'CUMULUSCI_ORG_'
    app_var = 'CUMULUSCI_CONNECTED_APP'
    service_var_prefix = 'CUMULUSCI_SERVICE_'
   
    def _load_keychain(self): 
        self._load_keychain_app()
        self._load_keychain_orgs()
        self._load_keychain_services()

    def _load_keychain_app(self):
        app = os.environ.get(self.app_var)
        if app:
            self.app = ConnectedAppOAuthConfig(json.loads(app))

    def _load_keychain_orgs(self):
        for key, value in os.environ.items():
            if key.startswith(self.org_var_prefix):
                org_config = json.loads(value)
                if org_config.get('scratch'):
                    self.orgs[key[len(self.org_var_prefix):]] = ScratchOrgConfig(json.loads(value))
                else:
                    self.orgs[key[len(self.org_var_prefix):]] = OrgConfig(json.loads(value))

    def _load_keychain_services(self):
        for key, value in os.environ.items():
            if key.startswith(self.service_var_prefix):
                self.services[key[len(self.service_var_prefix):]] = ServiceConfig(json.loads(value))


BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s : s[0:-ord(s[-1])]

class BaseEncryptedProjectKeychain(BaseProjectKeychain):
    """ Base class for building project keychains that use AES encryption for securing stored org credentials """
    encrypted = True

    def _set_connected_app(self, app_config, project):
        encrypted = self._encrypt_config(app_config)
        self._set_encrypted_connected_app(encrypted, project)

    def _set_encrypted_connected_app(self, encrypted, project):
        self.app = encrypted

    def _get_connected_app(self):
        if self.app:
            return self._decrypt_config(ConnectedAppOAuthConfig, self.app)

    def _get_service(self, name):
        return self._decrypt_config(ServiceConfig, self.services[name])

    def _set_service(self, service, service_config, project):
        encrypted = self._encrypt_config(service_config)
        self._set_encrypted_service(service, encrypted, project)

    def _set_encrypted_service(self, service, encrypted, project):
        self.services[service] = encrypted

    def _set_org(self, name, org_config, global_org):
        encrypted = self._encrypt_config(org_config)
        self._set_encrypted_org(name, encrypted, global_org)

    def _set_encrypted_org(self, name, encrypted, global_org):
        self.orgs[name] = encrypted

    def _get_org(self, name):
        return self._decrypt_config(OrgConfig, self.orgs[name])

    def _get_cipher(self, iv=None):
        if iv is None:
            iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return cipher, iv

    def _encrypt_config(self, config):
        pickled = pickle.dumps(config.config)
        pickled = pad(pickled)
        #pickled = base64.b64encode(pickled)
        cipher, iv = self._get_cipher()
        encrypted = base64.b64encode(iv + cipher.encrypt(pickled))
        return encrypted

    def _decrypt_config(self, config_class, encrypted_config):
        if not encrypted_config:
            return config_class()
        encrypted_config = base64.b64decode(encrypted_config)
        iv = encrypted_config[:16]
        cipher, iv = self._get_cipher(iv)
        pickled = cipher.decrypt(encrypted_config[16:])
        config_dict = pickle.loads(pickled)
        if config_dict.get('scratch'):
            config_class = ScratchOrgConfig
        return config_class(pickle.loads(pickled))

class EncryptedFileProjectKeychain(BaseEncryptedProjectKeychain):
    """ An encrypted project keychain that stores in the project's local directory """

    @property
    def config_local_dir(self):
        return os.path.join(
            os.path.expanduser('~'),
            self.project_config.global_config_obj.config_local_dir,
        )

    @property
    def project_local_dir(self):
        return self.project_config.project_local_dir

    def _load_keychain(self):

        def load_files(dirname):
            for item in os.listdir(dirname):
                if item.endswith('.org'):
                    with open(os.path.join(dirname, item), 'r') as f_item:
                        org_config = f_item.read()
                    org_name = item.replace('.org', '')
                    self.config['orgs'][org_name] = org_config
                elif item.endswith('.service'):
                    with open(os.path.join(dirname, item), 'r') as f_item:
                        service_config = f_item.read()
                    service_name = item.replace('.service', '')
                    self.config['services'][service_name] = service_config
                elif item == 'connected.app':
                    with open(os.path.join(dirname, item), 'r') as f_item:
                        app_config = f_item.read()
                    self.config['app'] = app_config

        load_files(self.config_local_dir)
        if not self.project_local_dir: 
            return
        load_files(self.project_local_dir)

    def _set_encrypted_connected_app(self, encrypted, project):
        if project:
            filename = os.path.join(self.project_local_dir, 'connected.app')
        else:
            filename = os.path.join(self.config_local_dir, 'connected.app')
        with open(filename, 'w') as f_org:
            f_org.write(encrypted)
        self.app = encrypted

    def _set_encrypted_org(self, name, encrypted, global_org):
        if global_org:
            filename = os.path.join(self.config_local_dir, '{}.org'.format(name))
        else:
            filename = os.path.join(self.project_local_dir, '{}.org'.format(name))
        with open(filename, 'w') as f_org:
            f_org.write(encrypted)

    def _set_encrypted_service(self, name, encrypted, project):
        if project:
            filename = os.path.join(self.project_local_dir, '{}.service'.format(name))
        else:
            filename = os.path.join(self.config_local_dir, '{}.service'.format(name))
        with open(filename, 'w') as f_service:
            f_service.write(encrypted)

    def _raise_org_not_found(self, name):
        raise OrgNotFound(
            'Org information could not be found.  Expected to find encrypted file at {}/{}.org'.format(
                self.project_local_dir, 
                name
            )
        )

    def _raise_service_not_configured(self, name):
        raise ServiceNotConfigured(
            'Service configuration could not be found.  Expected to find encrypted file at {}/{}.org'.format(
                self.project_local_dir, 
                name
            )
        )
