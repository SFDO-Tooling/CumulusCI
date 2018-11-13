import sys

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.keychain import BaseProjectKeychain


# pylint: disable=assignment-from-none
class BaseCumulusCI(object):
    global_config_class = BaseGlobalConfig
    project_config_class = BaseProjectConfig
    keychain_class = BaseProjectKeychain

    def __init__(self, *args, **kwargs):
        load_project_config = kwargs.pop(
            "load_project_config", True
        )  # this & below can be added to fn signature in py3
        load_keychain = kwargs.pop("load_keychain", True)

        self.global_config = None
        self.project_config = None
        self.keychain = None

        self._load_global_config()

        if load_project_config:
            self._load_project_config(*args, **kwargs)
            self._add_repo_to_path()
            if load_keychain:
                self._load_keychain()

    @property
    def global_config_cls(self):
        klass = self.get_global_config_class()
        return klass or self.global_config_class

    def get_global_config_class(self):
        return None

    @property
    def project_config_cls(self):
        klass = self.get_project_config_class()
        return klass or self.project_config_class

    def get_project_config_class(self):
        return None

    @property
    def keychain_cls(self):
        klass = self.get_keychain_class()
        return klass or self.keychain_class

    def get_keychain_class(self):
        return None

    @property
    def keychain_key(self):
        return self.get_keychain_key()

    def get_keychain_key(self):
        return None

    def _add_repo_to_path(self):
        if self.project_config:
            sys.path.append(self.project_config.repo_root)

    def _load_global_config(self):
        self.global_config = self.global_config_cls()

    def _load_project_config(self, *args, **kwargs):
        self.project_config = self.project_config_cls(
            self.global_config, *args, **kwargs
        )

    def _load_keychain(self):
        self.keychain = self.keychain_cls(self.project_config, self.keychain_key)
        self.project_config.set_keychain(self.keychain)  # never understood this but ok.
