"""Plugin manager for CumulusCI.

The PluginManager is responsible for discovering, loading, and managing
plugins. It uses Python's entry_points mechanism for plugin discovery
and integrates with the hook system for event handling.
"""

import logging
from importlib.metadata import entry_points
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from cumulusci.core.plugins.base import (
    CCIPlugin,
    PluginInfo,
    PluginManifest,
    TrustLevel,
)
from cumulusci.core.plugins.exceptions import (
    PluginLoadError,
    PluginNotFoundError,
    PluginTrustError,
    PluginVersionError,
)
from cumulusci.core.plugins.hooks import HookManager, get_hook_manager

if TYPE_CHECKING:
    from cumulusci.core.runtime import BaseCumulusCI

logger = logging.getLogger(__name__)

# Entry point group names
PLUGIN_ENTRY_POINT = "cumulusci.plugins"
CLI_ENTRY_POINT = "cumulusci.cli"


class PluginManager:
    """Manager for CumulusCI plugins.

    The PluginManager handles:
    - Plugin discovery via entry points
    - Plugin loading and initialization
    - Plugin configuration from cumulusci.yml
    - Aggregating tasks, flows, and services from plugins
    - Hook registration

    Example usage::

        manager = PluginManager(runtime)
        manager.discover_plugins()
        manager.load_enabled_plugins()

        # Get all tasks including plugin tasks
        all_tasks = manager.get_all_tasks()
    """

    def __init__(self, runtime: Optional["BaseCumulusCI"] = None):
        """Initialize the plugin manager.

        Args:
            runtime: The CumulusCI runtime instance
        """
        self._runtime = runtime
        self._discovered_plugins: Dict[str, PluginInfo] = {}
        self._loaded_plugins: Dict[str, CCIPlugin] = {}
        self._hook_manager: HookManager = get_hook_manager()
        self._plugin_configs: Dict[str, Dict[str, Any]] = {}

    @property
    def runtime(self) -> Optional["BaseCumulusCI"]:
        """Get the runtime instance."""
        return self._runtime

    @runtime.setter
    def runtime(self, value: "BaseCumulusCI") -> None:
        """Set the runtime instance."""
        self._runtime = value

    @property
    def hook_manager(self) -> HookManager:
        """Get the hook manager."""
        return self._hook_manager

    def discover_plugins(self) -> List[str]:
        """Discover available plugins via entry points.

        Scans the Python environment for packages that have registered
        entry points under the 'cumulusci.plugins' group.

        Returns:
            List of discovered plugin names
        """
        discovered = []

        # Get entry points for plugins
        eps = entry_points()
        if hasattr(eps, "select"):
            # Python 3.10+ / importlib_metadata 3.6+
            plugin_eps = eps.select(group=PLUGIN_ENTRY_POINT)
        else:
            # Older Python versions
            plugin_eps = eps.get(PLUGIN_ENTRY_POINT, [])

        for ep in plugin_eps:
            plugin_name = ep.name
            try:
                self._discovered_plugins[plugin_name] = PluginInfo(
                    name=plugin_name,
                    entry_point=f"{ep.value}",
                    module_name=ep.value.split(":")[0] if ":" in ep.value else ep.value,
                )
                discovered.append(plugin_name)
                logger.debug(f"Discovered plugin: {plugin_name} ({ep.value})")
            except Exception as e:
                logger.warning(f"Error discovering plugin {plugin_name}: {e}")
                self._discovered_plugins[plugin_name] = PluginInfo(
                    name=plugin_name,
                    entry_point=f"{ep.value}",
                    module_name="",
                    error=str(e),
                )

        logger.info(f"Discovered {len(discovered)} plugins")
        return discovered

    def get_discovered_plugins(self) -> Dict[str, PluginInfo]:
        """Get all discovered plugins.

        Returns:
            Dictionary mapping plugin names to PluginInfo objects
        """
        return self._discovered_plugins.copy()

    def get_loaded_plugins(self) -> Dict[str, CCIPlugin]:
        """Get all loaded plugins.

        Returns:
            Dictionary mapping plugin names to plugin instances
        """
        return self._loaded_plugins.copy()

    def load_plugin_configs(self, configs: Dict[str, Dict[str, Any]]) -> None:
        """Load plugin configurations from cumulusci.yml.

        Args:
            configs: Plugin configurations from cumulusci.yml plugins section
        """
        self._plugin_configs = configs or {}

    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """Check if a plugin is enabled.

        A plugin is enabled if:
        1. It exists in the plugins config and enabled is True
        2. It exists in the plugins config with no enabled key (default True)
        3. The plugin name starts with 'cci-' (auto-enabled convention)

        Args:
            plugin_name: Name of the plugin

        Returns:
            True if the plugin is enabled
        """
        if plugin_name in self._plugin_configs:
            config = self._plugin_configs[plugin_name]
            return config.get("enabled", True)

        # Auto-enable plugins starting with cci- if they don't have explicit config
        return plugin_name.startswith("cci-")

    def get_plugin_trust_level(self, plugin_name: str) -> TrustLevel:
        """Get the configured trust level for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            The configured trust level, defaulting to STANDARD
        """
        if plugin_name in self._plugin_configs:
            config = self._plugin_configs[plugin_name]
            trust_str = config.get("trust_level", "standard")
            try:
                return TrustLevel(trust_str)
            except ValueError:
                logger.warning(
                    f"Invalid trust level '{trust_str}' for plugin {plugin_name}, "
                    f"using 'standard'"
                )
                return TrustLevel.STANDARD
        return TrustLevel.STANDARD

    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """Get the configuration for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin configuration dictionary
        """
        if plugin_name in self._plugin_configs:
            return self._plugin_configs[plugin_name].get("config", {})
        return {}

    def load_enabled_plugins(self) -> List[str]:
        """Load all enabled plugins.

        Returns:
            List of successfully loaded plugin names
        """
        loaded = []

        for name, info in self._discovered_plugins.items():
            if info.error:
                continue

            if not self.is_plugin_enabled(name):
                logger.debug(f"Plugin {name} is not enabled, skipping")
                continue

            try:
                self.load_plugin(name)
                loaded.append(name)
            except Exception as e:
                logger.error(f"Failed to load plugin {name}: {e}")
                info.error = str(e)

        logger.info(f"Loaded {len(loaded)} plugins")
        return loaded

    def load_plugin(self, name: str) -> CCIPlugin:
        """Load a specific plugin.

        Args:
            name: Name of the plugin to load

        Returns:
            The loaded plugin instance

        Raises:
            PluginNotFoundError: If the plugin is not found
            PluginLoadError: If the plugin fails to load
            PluginTrustError: If trust level requirements aren't met
            PluginVersionError: If CCI version requirements aren't met
        """
        if name in self._loaded_plugins:
            return self._loaded_plugins[name]

        if name not in self._discovered_plugins:
            raise PluginNotFoundError(f"Plugin not found: {name}")

        info = self._discovered_plugins[name]
        if info.error:
            raise PluginLoadError(f"Plugin {name} has errors: {info.error}")

        # Get entry point and load the plugin class
        eps = entry_points()
        if hasattr(eps, "select"):
            plugin_eps = list(eps.select(group=PLUGIN_ENTRY_POINT, name=name))
        else:
            plugin_eps = [
                ep for ep in eps.get(PLUGIN_ENTRY_POINT, []) if ep.name == name
            ]

        if not plugin_eps:
            raise PluginNotFoundError(f"Entry point not found for plugin: {name}")

        ep = plugin_eps[0]

        try:
            plugin_class = ep.load()
        except Exception as e:
            raise PluginLoadError(f"Failed to load plugin class {name}: {e}")

        # Verify it's a CCIPlugin subclass
        if not (isinstance(plugin_class, type) and issubclass(plugin_class, CCIPlugin)):
            raise PluginLoadError(
                f"Plugin {name} must be a subclass of CCIPlugin, "
                f"got {type(plugin_class)}"
            )

        # Instantiate the plugin
        try:
            plugin = plugin_class()
        except Exception as e:
            raise PluginLoadError(f"Failed to instantiate plugin {name}: {e}")

        # Check trust level requirements
        configured_trust = self.get_plugin_trust_level(name)
        required_trust = plugin.manifest.required_trust_level
        if required_trust > configured_trust:
            raise PluginTrustError(
                f"Plugin {name} requires trust level '{required_trust.value}', "
                f"but only '{configured_trust.value}' is configured"
            )

        # Check CCI version requirements
        self._check_version_requirements(plugin.manifest)

        # Initialize the plugin
        plugin._set_runtime(self._runtime)
        plugin._set_enabled(True)

        # Call on_load hook
        if self._runtime:
            plugin.on_load(self._runtime)

        # Apply configuration
        config = self.get_plugin_config(name)
        plugin.configure(config)

        # Register with hook manager
        self._hook_manager.register(plugin, name=name)

        # Update tracking
        self._loaded_plugins[name] = plugin
        info.is_loaded = True
        info.is_enabled = True
        info.plugin_instance = plugin
        info.trust_level = configured_trust

        logger.info(f"Loaded plugin: {name} v{plugin.version}")
        return plugin

    def unload_plugin(self, name: str) -> None:
        """Unload a plugin.

        Args:
            name: Name of the plugin to unload

        Raises:
            PluginNotFoundError: If the plugin is not loaded
        """
        if name not in self._loaded_plugins:
            raise PluginNotFoundError(f"Plugin not loaded: {name}")

        plugin = self._loaded_plugins[name]

        # Call on_unload hook
        plugin.on_unload()

        # Unregister from hook manager
        self._hook_manager.unregister(name=name)

        # Update tracking
        plugin._set_enabled(False)
        del self._loaded_plugins[name]

        if name in self._discovered_plugins:
            info = self._discovered_plugins[name]
            info.is_loaded = False
            info.is_enabled = False
            info.plugin_instance = None

        logger.info(f"Unloaded plugin: {name}")

    def _check_version_requirements(self, manifest: PluginManifest) -> None:
        """Check if CumulusCI version requirements are met.

        Args:
            manifest: Plugin manifest with version requirements

        Raises:
            PluginVersionError: If version requirements are not met
        """
        import cumulusci

        current_version = cumulusci.__version__

        if manifest.min_cci_version:
            from packaging.version import Version

            try:
                if Version(current_version) < Version(manifest.min_cci_version):
                    raise PluginVersionError(
                        f"Plugin {manifest.name} requires CumulusCI >= "
                        f"{manifest.min_cci_version}, but {current_version} is installed"
                    )
            except Exception as e:
                if isinstance(e, PluginVersionError):
                    raise
                # If version parsing fails, log warning but continue
                logger.warning(f"Could not check min version requirement: {e}")

        if manifest.max_cci_version:
            from packaging.version import Version

            try:
                if Version(current_version) > Version(manifest.max_cci_version):
                    raise PluginVersionError(
                        f"Plugin {manifest.name} requires CumulusCI <= "
                        f"{manifest.max_cci_version}, but {current_version} is installed"
                    )
            except Exception as e:
                if isinstance(e, PluginVersionError):
                    raise
                logger.warning(f"Could not check max version requirement: {e}")

    def get_all_tasks(self) -> Dict[str, str]:
        """Get all tasks from loaded plugins.

        Returns:
            Dictionary mapping task names to class paths
        """
        tasks = {}
        for plugin in self._loaded_plugins.values():
            for task_name, class_path in plugin.manifest.tasks.items():
                if task_name in tasks:
                    logger.warning(
                        f"Task {task_name} from plugin {plugin.name} "
                        f"conflicts with existing task, skipping"
                    )
                    continue
                tasks[task_name] = class_path
        return tasks

    def get_all_flows(self) -> Dict[str, dict]:
        """Get all flows from loaded plugins.

        Returns:
            Dictionary mapping flow names to flow configurations
        """
        flows = {}
        for plugin in self._loaded_plugins.values():
            for flow_name, flow_config in plugin.manifest.flows.items():
                if flow_name in flows:
                    logger.warning(
                        f"Flow {flow_name} from plugin {plugin.name} "
                        f"conflicts with existing flow, skipping"
                    )
                    continue
                flows[flow_name] = flow_config
        return flows

    def get_all_services(self) -> Dict[str, dict]:
        """Get all services from loaded plugins.

        Returns:
            Dictionary mapping service type names to service definitions
        """
        services = {}
        for plugin in self._loaded_plugins.values():
            for service_name, service_def in plugin.manifest.services.items():
                if service_name in services:
                    logger.warning(
                        f"Service {service_name} from plugin {plugin.name} "
                        f"conflicts with existing service, skipping"
                    )
                    continue
                services[service_name] = service_def
        return services

    def get_all_cli_commands(self) -> List[str]:
        """Get all CLI command entry points from loaded trusted plugins.

        Only plugins with TRUSTED trust level can provide CLI commands.

        Returns:
            List of CLI command entry point strings
        """
        commands = []
        for name, plugin in self._loaded_plugins.items():
            trust_level = self.get_plugin_trust_level(name)
            if trust_level != TrustLevel.TRUSTED:
                continue
            commands.extend(plugin.manifest.cli_commands)
        return commands

    def get_all_robot_libraries(self) -> Dict[str, str]:
        """Get all Robot Framework libraries from loaded plugins.

        Returns:
            Dictionary mapping library names to class paths
        """
        libraries = {}
        for plugin in self._loaded_plugins.values():
            for lib_name, class_path in plugin.manifest.robot_libraries.items():
                if lib_name in libraries:
                    logger.warning(
                        f"Robot library {lib_name} from plugin {plugin.name} "
                        f"conflicts with existing library, skipping"
                    )
                    continue
                libraries[lib_name] = class_path
        return libraries

    def get_plugin_task(self, plugin_name: str, task_name: str) -> Optional[str]:
        """Get a specific task from a plugin.

        Args:
            plugin_name: Name of the plugin
            task_name: Name of the task

        Returns:
            Task class path or None if not found
        """
        if plugin_name not in self._loaded_plugins:
            return None
        plugin = self._loaded_plugins[plugin_name]
        return plugin.manifest.tasks.get(task_name)

    def get_plugin_flow(self, plugin_name: str, flow_name: str) -> Optional[dict]:
        """Get a specific flow from a plugin.

        Args:
            plugin_name: Name of the plugin
            flow_name: Name of the flow

        Returns:
            Flow configuration or None if not found
        """
        if plugin_name not in self._loaded_plugins:
            return None
        plugin = self._loaded_plugins[plugin_name]
        return plugin.manifest.flows.get(flow_name)


# Global plugin manager instance
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager instance.

    Creates the plugin manager on first call.

    Returns:
        The global PluginManager instance
    """
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


def reset_plugin_manager() -> None:
    """Reset the global plugin manager.

    This is primarily useful for testing.
    """
    global _plugin_manager
    _plugin_manager = None
