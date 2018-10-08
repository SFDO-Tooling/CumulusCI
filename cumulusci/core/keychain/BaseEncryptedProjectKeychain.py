from __future__ import print_function
from builtins import chr
import base64
import os
import pickle

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers.modes import CBC

from cumulusci.core.config import ConnectedAppOAuthConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import ScratchOrgConfig
from cumulusci.core.config import ServiceConfig
from cumulusci.core.exceptions import ConfigError, KeychainKeyNotFound
from cumulusci.core.keychain import BaseProjectKeychain

BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS).encode("ascii")
unpad = lambda s: s[0 : -ord(s[-1])]
backend = default_backend()


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
        key = self.key
        if not isinstance(key, bytes):
            key = key.encode()
        if iv is None:
            iv = os.urandom(16)
        cipher = Cipher(AES(key), CBC(iv), backend=backend)
        return cipher, iv

    def _encrypt_config(self, config):
        pickled = pickle.dumps(config.config, protocol=2)
        pickled = pad(pickled)
        cipher, iv = self._get_cipher()
        return base64.b64encode(iv + cipher.encryptor().update(pickled))

    def _decrypt_config(self, config_class, encrypted_config, extra=None):
        if not encrypted_config:
            if extra:
                return config_class(None, *extra)
            else:
                return config_class()
        encrypted_config = base64.b64decode(encrypted_config)
        iv = encrypted_config[:16]
        cipher, iv = self._get_cipher(iv)
        pickled = cipher.decryptor().update(encrypted_config[16:])
        try:
            unpickled = pickle.loads(pickled, encoding="bytes")
        except TypeError:  # Python 2
            unpickled = pickle.loads(pickled)
            # Convert text created in Python 3
            config_dict = {}
            for k, v in unpickled.items():
                if isinstance(k, unicode):
                    k = k.encode("utf-8")
                if isinstance(v, unicode):
                    v = v.encode("utf-8")
                config_dict[k] = v
        else:  # Python 3
            # Convert bytes created in Python 2
            config_dict = {}
            for k, v in unpickled.items():
                if isinstance(k, bytes):
                    k = k.decode("utf-8")
                if isinstance(v, bytes):
                    v = v.decode("utf-8")
                config_dict[k] = v
        args = [config_dict]
        if extra:
            args += extra
        return self._construct_config(config_class, args)

    def _construct_config(self, config_class, args):
        if args[0].get("scratch"):
            config_class = ScratchOrgConfig

        return config_class(*args)

    def _validate_key(self):
        if not self.key:
            raise KeychainKeyNotFound(
                "The CUMULUSCI_KEY environment variable is not set."
            )
        if len(self.key) != 16:
            raise ConfigError(
                "The CUMULUSCI_KEY environment variable must be 16 characters long."
            )
