"""Hook specifications for the CumulusCI plugin system.

This module defines the hooks that plugins can implement to intercept
and respond to CumulusCI events. The hook system is built on pluggy,
the same library used by pytest.

Example usage in a plugin::

    from cumulusci.core.plugins import CCIPlugin, PluginManifest
    from cumulusci.core.plugins.hooks import hookimpl

    class MyPlugin(CCIPlugin):
        @property
        def manifest(self) -> PluginManifest:
            return PluginManifest(name="my-plugin", version="1.0.0")

        @hookimpl
        def cci_task_complete(self, task, result):
            if result.get("success"):
                print(f"Task {task.name} completed successfully!")

Available hooks:
    - cci_cli_init: Called when CLI runtime is initialized
    - cci_flow_start: Called before a flow starts execution
    - cci_flow_complete: Called after a flow completes
    - cci_task_start: Called before a task starts execution
    - cci_task_complete: Called after a task completes
    - cci_org_connect: Called when an org is connected
    - cci_service_connect: Called when a service is connected
    - cci_task_option_transform: Transform task options before execution
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

import pluggy

if TYPE_CHECKING:
    from cumulusci.core.config import OrgConfig
    from cumulusci.core.flowrunner import FlowCoordinator
    from cumulusci.core.runtime import BaseCumulusCI
    from cumulusci.core.tasks import BaseTask

# Project name for pluggy hooks
PROJECT_NAME = "cumulusci"

# Hook specification and implementation markers
hookspec = pluggy.HookspecMarker(PROJECT_NAME)
hookimpl = pluggy.HookimplMarker(PROJECT_NAME)


class CCIHookSpec:
    """Hook specifications for CumulusCI plugin system.

    This class defines all the hooks that plugins can implement.
    Each hook is decorated with @hookspec to register it with pluggy.
    """

    @hookspec
    def cci_cli_init(self, runtime: "BaseCumulusCI") -> None:
        """Called when the CLI runtime is initialized.

        This hook is called after the runtime object is created but
        before any commands are executed. Plugins can use this to
        perform additional initialization.

        Args:
            runtime: The CumulusCI runtime instance
        """

    @hookspec
    def cci_flow_start(self, flow: "FlowCoordinator", context: Dict[str, Any]) -> None:
        """Called before a flow starts execution.

        Args:
            flow: The FlowCoordinator instance about to run
            context: Additional context including:
                - org_config: The org configuration
                - flow_name: Name of the flow
                - options: Runtime options passed to the flow
        """

    @hookspec
    def cci_flow_complete(
        self, flow: "FlowCoordinator", result: Dict[str, Any]
    ) -> None:
        """Called after a flow completes (success or failure).

        Args:
            flow: The FlowCoordinator instance that ran
            result: Result information including:
                - success: Boolean indicating success/failure
                - exception: Exception if flow failed, None otherwise
                - steps_completed: Number of steps completed
        """

    @hookspec
    def cci_task_start(self, task: "BaseTask", context: Dict[str, Any]) -> None:
        """Called before a task starts execution.

        Args:
            task: The task instance about to run
            context: Additional context including:
                - step_num: Step number in the flow (if part of a flow)
                - flow_name: Name of the parent flow (if any)
                - options: Task options
        """

    @hookspec
    def cci_task_complete(self, task: "BaseTask", result: Dict[str, Any]) -> None:
        """Called after a task completes (success or failure).

        Args:
            task: The task instance that ran
            result: Result information including:
                - success: Boolean indicating success/failure
                - exception: Exception if task failed, None otherwise
                - return_values: Task return values
        """

    @hookspec
    def cci_org_connect(self, org_config: "OrgConfig", context: Dict[str, Any]) -> None:
        """Called when an org is connected.

        Args:
            org_config: The org configuration that was connected
            context: Additional context including:
                - org_name: Name/alias of the org
                - is_scratch: Whether the org is a scratch org
                - is_new: Whether this is a newly created org
        """

    @hookspec
    def cci_service_connect(
        self, service_type: str, service_config: Dict[str, Any]
    ) -> None:
        """Called when a service is connected.

        Args:
            service_type: Type of the service (e.g., "github", "slack")
            service_config: The service configuration
        """

    @hookspec(firstresult=True)
    def cci_task_option_transform(
        self, task_name: str, options: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Transform task options before execution.

        This hook uses firstresult=True, meaning the first non-None
        result from any plugin will be used and other plugins won't
        be called. Use this to modify or validate task options.

        Args:
            task_name: Name of the task
            options: Current task options

        Returns:
            Modified options dict, or None to keep original options
        """


def create_plugin_manager() -> pluggy.PluginManager:
    """Create and configure a plugin manager for CumulusCI.

    Returns:
        Configured pluggy.PluginManager instance
    """
    pm = pluggy.PluginManager(PROJECT_NAME)
    pm.add_hookspecs(CCIHookSpec)
    return pm


class HookManager:
    """Manager for CumulusCI plugin hooks.

    This class wraps the pluggy PluginManager and provides methods
    for registering plugins and calling hooks.
    """

    def __init__(self):
        """Initialize the hook manager."""
        self._pm = create_plugin_manager()
        self._registered_plugins: Dict[str, Any] = {}

    @property
    def hook(self) -> Any:
        """Access the hook caller.

        Returns the pluggy hook object that can be used to call hooks.
        Example: hook_manager.hook.cci_task_complete(task=task, result=result)
        """
        return self._pm.hook

    def register(self, plugin: Any, name: Optional[str] = None) -> str:
        """Register a plugin with the hook manager.

        Args:
            plugin: Plugin instance implementing hook methods
            name: Optional name for the plugin

        Returns:
            The plugin name
        """
        plugin_name = name or getattr(plugin, "name", None) or str(id(plugin))
        self._pm.register(plugin, name=plugin_name)
        self._registered_plugins[plugin_name] = plugin
        return plugin_name

    def unregister(self, plugin: Any = None, name: Optional[str] = None) -> Any:
        """Unregister a plugin from the hook manager.

        Args:
            plugin: Plugin instance to unregister
            name: Name of the plugin to unregister

        Returns:
            The unregistered plugin
        """
        if name and name in self._registered_plugins:
            del self._registered_plugins[name]
        return self._pm.unregister(plugin=plugin, name=name)

    def is_registered(self, plugin: Any = None, name: Optional[str] = None) -> bool:
        """Check if a plugin is registered.

        Args:
            plugin: Plugin instance to check
            name: Name of the plugin to check

        Returns:
            True if the plugin is registered
        """
        if name:
            return name in self._registered_plugins
        return self._pm.is_registered(plugin)

    def get_plugins(self) -> list:
        """Get list of registered plugins.

        Returns:
            List of registered plugin instances
        """
        return list(self._pm.get_plugins())

    def list_plugin_names(self) -> list:
        """Get list of registered plugin names.

        Returns:
            List of registered plugin names
        """
        return list(self._registered_plugins.keys())


# Global hook manager instance
_hook_manager: Optional[HookManager] = None


def get_hook_manager() -> HookManager:
    """Get the global hook manager instance.

    Creates the hook manager on first call.

    Returns:
        The global HookManager instance
    """
    global _hook_manager
    if _hook_manager is None:
        _hook_manager = HookManager()
    return _hook_manager


def reset_hook_manager() -> None:
    """Reset the global hook manager.

    This is primarily useful for testing.
    """
    global _hook_manager
    _hook_manager = None
