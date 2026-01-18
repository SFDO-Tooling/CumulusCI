import logging
import sys
from abc import abstractmethod
from typing import TYPE_CHECKING, Optional, Type

from cumulusci.core.config import BaseProjectConfig, UniversalConfig
from cumulusci.core.debug import DebugMode, get_debug_mode
from cumulusci.core.exceptions import NotInProject, ProjectConfigNotFound
from cumulusci.core.flowrunner import FlowCallback, FlowCoordinator
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.plugins import PluginManager

if TYPE_CHECKING:
    from cumulusci.core.plugins import PluginManager as PluginManagerType

logger = logging.getLogger(__name__)


# pylint: disable=assignment-from-none
class BaseCumulusCI:
    universal_config_class = UniversalConfig
    project_config_class = BaseProjectConfig
    keychain_class = BaseProjectKeychain
    callback_class = FlowCallback

    universal_config: UniversalConfig
    project_config: Optional[BaseProjectConfig]
    keychain: Optional[BaseProjectKeychain]
    plugin_manager: "PluginManagerType"
    debug_mode: DebugMode
    project_config_error: Exception

    def __init__(self, *args, load_keychain=True, load_plugins=True, **kwargs):
        self.keychain = None
        self.debug_mode = get_debug_mode()

        # Initialize plugin manager early
        self.plugin_manager = PluginManager(self)

        self._load_universal_config()

        try:
            self._load_project_config(*args, **kwargs)
            self._add_repo_to_path()
        except (NotInProject, ProjectConfigNotFound) as e:
            self.project_config = None
            self.project_config_error = e

        if load_keychain:
            self._load_keychain()

        # Load plugins after project config and keychain are available
        if load_plugins:
            self._load_plugins()

    @property
    def universal_config_cls(self) -> Type:
        klass = self.get_universal_config_class()
        return klass or self.universal_config_class

    @abstractmethod
    def get_universal_config_class(self) -> Optional[Type]:
        return None

    @property
    def project_config_cls(self) -> Type:
        klass = self.get_project_config_class()
        return klass or self.project_config_class

    @abstractmethod
    def get_project_config_class(self) -> Optional[Type]:
        return None

    @property
    def keychain_cls(self) -> Type:
        klass = self.get_keychain_class()
        return klass or self.keychain_class

    @abstractmethod
    def get_keychain_class(self) -> Optional[Type]:
        return None

    @property
    def keychain_key(self):
        return self.get_keychain_key()

    @abstractmethod
    def get_keychain_key(self):
        return None

    def _add_repo_to_path(self):
        if self.project_config and self.project_config.repo_root:
            sys.path.append(self.project_config.repo_root)

    def _load_universal_config(self):
        self.universal_config = self.universal_config_cls()

    def _load_project_config(self, *args, **kwargs):
        self.project_config = self.project_config_cls(
            self.universal_config, *args, **kwargs
        )
        if self.project_config is not None:
            self.project_config._add_tasks_directory_to_python_path()

    def _load_keychain(self):
        if self.keychain is not None:
            return

        keychain_key = self.keychain_key if self.keychain_cls.encrypted else None

        if self.project_config is None:
            self.keychain = self.keychain_cls(self.universal_config, keychain_key)
        else:
            self.keychain = self.keychain_cls(self.project_config, keychain_key)
            self.project_config.keychain = self.keychain

    def _load_plugins(self):
        """Discover and load enabled plugins."""
        try:
            # Discover available plugins
            self.plugin_manager.discover_plugins()

            # Load plugin configurations from project config
            if self.project_config:
                plugin_configs = self.project_config.lookup("plugins") or {}
                self.plugin_manager.load_plugin_configs(plugin_configs)

            # Load enabled plugins
            self.plugin_manager.load_enabled_plugins()

            # Call cli_init hook
            self.plugin_manager.hook_manager.hook.cci_cli_init(runtime=self)

        except Exception as e:
            logger.warning(f"Error loading plugins: {e}")
            if self.debug_mode:
                raise

    def get_flow(self, name: str, options: Optional[dict] = None) -> FlowCoordinator:
        """Get a primed and ready-to-go flow coordinator."""
        if not self.project_config:
            raise ProjectConfigNotFound
        flow_config = self.project_config.get_flow(name)
        callbacks = self.callback_class()
        coordinator = FlowCoordinator(
            flow_config.project_config,
            flow_config,
            name=flow_config.name,
            options=options,
            skip=None,
            callbacks=callbacks,
        )
        return coordinator
