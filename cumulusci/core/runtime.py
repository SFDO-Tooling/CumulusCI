import sys

from cumulusci.core.config import BaseGlobalConfig, BaseProjectConfig
from cumulusci.core.exceptions import NotInProject, ProjectConfigNotFound
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.flowrunner import FlowCallback, FlowCoordinator


# pylint: disable=assignment-from-none
class BaseCumulusCI(object):
    global_config_class = BaseGlobalConfig
    project_config_class = BaseProjectConfig
    keychain_class = BaseProjectKeychain
    callback_class = FlowCallback

    def __init__(self, *args, **kwargs):
        load_project_config = kwargs.pop(
            "load_project_config", True
        )  # this & below can be added to fn signature in py3
        load_keychain = kwargs.pop("load_keychain", True)
        allow_global_keychain = kwargs.pop("allow_global_keychain", False)

        self.global_config = None
        self.project_config = None
        self.keychain = None
        self.is_global_keychain = False

        self._load_global_config()

        if load_project_config:
            try:
                self._load_project_config(*args, **kwargs)
                self._add_repo_to_path()
            except (NotInProject, ProjectConfigNotFound):
                if allow_global_keychain:
                    self.is_global_keychain = True
                else:
                    raise
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
        if self.is_global_keychain:
            self.keychain = self.keychain_cls(self.global_config, self.keychain_key)
        else:
            self.keychain = self.keychain_cls(self.project_config, self.keychain_key)
            self.project_config.keychain = (
                self.keychain
            )  # never understood this but ok.

    def get_flow(self, name, options=None):
        """ Get a primed and readytogo flow coordinator. """
        config = self.project_config.get_flow(name)
        callbacks = self.callback_class()
        coordinator = FlowCoordinator(
            self.project_config,
            config,
            name=name,
            options=options,
            skip=None,
            callbacks=callbacks,
        )
        return coordinator
