import base64
import os
import pickle

from Crypto import Random
from Crypto.Cipher import AES

from cumulusci.core.config import BaseConfig
from cumulusci.core.config import ConnectedAppOAuthConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.exceptions import OrgNotFound
from cumulusci.core.exceptions import KeychainConnectedAppNotFound
from cumulusci.oauth.salesforce import SalesforceOAuth2

class BaseProjectKeychain(BaseConfig):
    def __init__(self, project_config, key):
        super(BaseProjectKeychain, self).__init__()
        self.config = {'orgs': {}, 'app': None}
        self.project_config = project_config
        self.key = key
        self._load_keychain()

    def _load_keychain(self):
        """ Subclasses can override to implement logic to load the keychain """
        pass

    def change_key(self, key):
        connected_app = self.get_connected_app()
        orgs = {}
        for org_name in self.list_orgs():
            orgs[org_name] = self.get_org(org_name)

        self.key = key
        if connected_app:
            self.set_connected_app(connected_app)

        if orgs:
            for org_name, org_config in orgs.items():
                self.set_org(org_name, org_config)

    def set_connected_app(self, app_config):
        self._set_connected_app(app_config)
        self._load_keychain()
    
    def _set_connected_app(self, app_config):
        self.app = app_config

    def get_connected_app(self):
        return self._get_connected_app()

    def _get_connected_app(self):
        return self.app

    def set_org(self, name, org_config):
        self._set_org(name, org_config)
        self._load_keychain()

    def _set_org(self, name, org_config):
        self.orgs[name] = org_config

    def get_org(self, name):
        if name not in self.orgs:
            self._raise_org_not_found(name)
        return self._get_org(name)

    def _get_org(self, name):
        return self.orgs.get(name)
    
    def _raise_org_not_found(self, name):
        raise OrgNotFound('Org named {} was not found in keychain'.format(name))

    def list_orgs(self):
        return self.orgs.keys()

BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s : s[0:-ord(s[-1])]

class BaseEncryptedProjectKeychain(BaseProjectKeychain):
    """ Base class for building project keychains that use AES encryption for securing stored org credentials """

    def _set_connected_app(self, app_config):
        encrypted = self._encrypt_config(app_config)
        self._set_encrypted_connected_app(encrypted)

    def _set_encrypted_connected_app(self, encrypted):
        self.app = encrypted

    def _get_connected_app(self):
        if self.app:
            return self._decrypt_config(ConnectedAppOAuthConfig, self.app)

    def _set_org(self, name, org_config):
        encrypted = self._encrypt_config(org_config)
        self._set_encrypted_org(name, encrypted)

    def _set_encrypted_org(self, name, encrypted):
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
        return base64.b64encode(iv + cipher.encrypt(pickled))

    def _decrypt_config(self, config_class, encrypted_config):
        if not encrypted_config:
            return config_class()
        encrypted_config = base64.b64decode(encrypted_config)
        iv = encrypted_config[:16]
        cipher, iv = self._get_cipher(iv)
        pickled = cipher.decrypt(encrypted_config[16:])
        return config_class(pickle.loads(pickled))

class EncryptedFileProjectKeychain(BaseEncryptedProjectKeychain):
    """ An encrypted project keychain that stores in the project's local directory """

    @property
    def project_local_dir(self):
        return self.project_config.project_local_dir

    def _load_keychain(self):
        if not self.project_local_dir: 
            return

        for item in os.listdir(self.project_local_dir):
            if item.endswith('.org'):
                f_item = open(os.path.join(self.project_local_dir, item), 'r')
                org_name = item.replace('.org', '')
                org_config = f_item.read()
                self.config['orgs'][org_name] = org_config
            elif item == 'connected.app':
                f_item = open(os.path.join(self.project_local_dir, item), 'r')
                app_config = f_item.read()
                self.config['app'] = app_config

        #if not self.config['app']:
        #    raise KeychainConnectedAppNotFound('Expected to find the connected app info for the keychain in {}/connected.app'.format(self.project_local_dir))

    def _set_encrypted_connected_app(self, encrypted):
        f_org = open(os.path.join(self.project_local_dir, 'connected.app'), 'w')
        f_org.write(encrypted)
        f_org.close()

    def _set_encrypted_org(self, name, encrypted):
        f_org = open(os.path.join(self.project_local_dir, '{}.org'.format(name)), 'w')
        f_org.write(encrypted)
        f_org.close()

    def _raise_org_not_found(self, name):
        raise OrgNotFound(
            'Org information could not be found.  Expected to find encrypted file at {}/{}.org'.format(
                self.project_local_dir, 
                name
            )
        )
