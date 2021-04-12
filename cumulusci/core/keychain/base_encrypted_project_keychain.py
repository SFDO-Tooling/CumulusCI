import base64
import os
import pickle

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers.modes import CBC

from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import ScratchOrgConfig
from cumulusci.core.config import ServiceConfig
from cumulusci.core.exceptions import (
    ConfigError,
    CumulusCIException,
    KeychainKeyNotFound,
)

BS = 16
backend = default_backend()


def pad(s):
    return s + (BS - len(s) % BS) * chr(BS - len(s) % BS).encode("ascii")


class BaseEncryptedProjectKeychain(BaseProjectKeychain):
    """ Base class for building project keychains that use AES encryption for securing stored org credentials """

    encrypted = True

    def set_default_service(
        self, service_type: str, alias: str, project: bool = False
    ) -> None:
        if service_type not in self.services:
            raise CumulusCIException(f"Service type is not configured: {service_type}")
        if alias not in self.services[service_type]:
            raise CumulusCIException(
                f"No service of type {service_type} configured with the name: {alias}"
            )

        self._default_services[service_type] = alias

    def _set_service(self, service_type, alias, service_config):
        if service_type not in self.services:
            self.services[service_type] = {}
            # set the first service of a given type as the global default
            self._default_services[service_type] = alias
            self._save_default_service(service_type, alias, project=False)

        encrypted = self._encrypt_config(service_config)
        self._set_encrypted_service(service_type, alias, encrypted)

    def _set_encrypted_service(self, service_type, alias, encrypted):
        self.services[service_type][alias] = encrypted

    def _get_service(self, service_type, alias):
        return self._decrypt_config(
            ServiceConfig,
            self.services[service_type][alias],
            context=f"service config ({service_type}/{alias})",
        )

    def _set_org(self, org_config, global_org):
        if org_config.keychain:
            assert org_config.keychain is self
        assert org_config.global_org == global_org
        org_config.keychain = self
        org_config.global_org = global_org
        encrypted = self._encrypt_config(org_config)
        self._set_encrypted_org(org_config.name, encrypted, global_org)

    def _set_encrypted_org(self, name, encrypted, global_org):
        self.orgs[name] = encrypted

    def _get_org(self, name):
        return self._decrypt_config(
            OrgConfig,
            self.orgs[name],
            extra=[name, self],
            context=f"org config ({name})",
        )

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

    def _decrypt_config(self, config_class, encrypted_config, extra=None, context=None):
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
        except Exception:
            raise KeychainKeyNotFound(
                f"Unable to decrypt{' ' + context if context else ''}. "
                "It was probably stored using a different CUMULUSCI_KEY."
            )
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
            raise KeychainKeyNotFound("The keychain key was not found.")
        if len(self.key) != 16:
            raise ConfigError("The keychain key must be 16 characters long.")
