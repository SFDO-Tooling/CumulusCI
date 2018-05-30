from __future__ import print_function
from builtins import chr
import base64
import pickle

from Crypto import Random
from Crypto.Cipher import AES

from cumulusci.core.config import ConnectedAppOAuthConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import ScratchOrgConfig
from cumulusci.core.config import ServiceConfig
from cumulusci.core.exceptions import ConfigError
from cumulusci.core.keychain import BaseProjectKeychain

BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS).encode('ascii')
unpad = lambda s: s[0:-ord(s[-1])]

class BaseEncryptedProjectKeychain(BaseProjectKeychain):
    """ Base class for building project keychains that use AES encryption for securing stored org credentials """
    encrypted = True

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

    def _set_org(self, org_config, global_org):
        encrypted = self._encrypt_config(org_config)
        self._set_encrypted_org(org_config.name, encrypted, global_org)

    def _set_encrypted_org(self, name, encrypted, global_org):
        self.orgs[name] = encrypted

    def _get_org(self, name):
        return self._decrypt_config(OrgConfig, self.orgs[name], extra=[name])

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

    def _decrypt_config(self, config_class, encrypted_config, extra=None):
        if not encrypted_config:
            if extra:
                return config_class(None, *extra)
            else:
                return config_class()
        encrypted_config = base64.b64decode(encrypted_config)
        iv = encrypted_config[:16]
        cipher, iv = self._get_cipher(iv)
        pickled = cipher.decrypt(encrypted_config[16:])
        config_dict = pickle.loads(pickled)
        args = [config_dict]
        if extra:
            args += extra
        return self._construct_config(config_class, args)

    def _construct_config(self, config_class, args):
        if args[0].get('scratch'):
            config_class = ScratchOrgConfig
        
        return config_class(*args)

    def _validate_key(self):
        if not self.key:
            raise ConfigError('CUMULUSCI_KEY not set')
        if len(self.key) != 16:
            raise ConfigError('CUMULUSCI_KEY must be 16 characters long')
