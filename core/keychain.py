import base64
import os
import pickle

from Crypto import Random
from Crypto.Cipher import AES

from core.config import BaseConfig
from core.config import ConnectedAppOAuthConfig
from core.config import OrgConfig
from core.exceptions import KeychainConnectedAppNotFound
from oauth.salesforce import SalesforceOAuth2

class BaseProjectKeychain(BaseConfig):
    def __init__(self, project_config, key):
        self.config = {'orgs': {}}
        self.project_config = project_config
        self.key = key
        super(BaseProjectKeychain, self).__init__()

    def set_org(self, name, org_config):
        self.orgs[name] = org_config

    def get_org(self, name):
        return self.orgs.get(name)

    def list_orgs(self):
        return self.orgs.keys()

BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s : s[0:-ord(s[-1])]

class BaseEncryptedProjectKeychain(BaseProjectKeychain):

    def _load_config(self):
        self.config['app'] = {}
        self.config['orgs'] = {}
        self._load_encrypted_config()

    def _load_encrypted_config(self):
        raise NotImplementedError('Subclasses must override this method to provide their own logic')

    def save(self):
        """ Encrypts and saves to disk the connected app and org configs.  If you change self.key after init and call this, you can change the encryption password """
        self.set_connected_app(self.app)
        for org in self.orgs:
            self.set_org(org)
        
    def set_connected_app(self, app_config):
        encrypted = self._encrypt_config(app_config)
        f_org = open(os.path.join(self.project_local_dir, 'connected.app'), 'w')
        f_org.write(encrypted)
        f_org.close()
        self._load_config()

    def set_org(self, name, org_config):
        encrypted = self._encrypt_config(org_config)
        self._set_encrypted_org(name, encrypted)
        self._load_config()

    def _set_encrypted_org(self, name, encrypted):
        raise NotImplementedError('Subclasses must override this method to provide their own logic')

    def get_org(self, name):
        org = self.orgs.get(name)
        if not org:
            raise OrgNotFound('Org information could not be found.  Expected to find encrypted file at {}/{}.org'.format(self.project_local_dir, name))
        return org

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

    def _load_encrypted_config(self):
        if not self.project_local_dir: 
            return

        for item in os.listdir(self.project_local_dir):
            if item.endswith('.org'):
                f_item = open(os.path.join(self.project_local_dir, item), 'r')
                org_name = item.replace('.org', '')
                org_config = self._decrypt_config(OrgConfig, f_item.read())
                self.config['orgs'][org_name] = org_config
            elif item == 'connected.app':
                f_item = open(os.path.join(self.project_local_dir, item), 'r')
                app_config = self._decrypt_config(ConnectedAppOAuthConfig, f_item.read())
                self.config['app'] = app_config

        #if not self.config['app']:
        #    raise KeychainConnectedAppNotFound('Expected to find the connected app info for the keychain in {}/connected.app'.format(self.project_local_dir))

    @property
    def project_local_dir(self):
        return self.project_config.project_local_dir

    def _set_encrypted_org(self, name, encrypted_org_config):
        f_org = open(os.path.join(self.project_local_dir, '{}.org'.format(name)), 'w')
        f_org.write(encrypted)
        f_org.close()

