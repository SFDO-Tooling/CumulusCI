"""CumulusCI Plugin Framework.

This module provides the infrastructure for extending CumulusCI through plugins.
Plugins can add custom tasks, flows, services, CLI commands, and Robot Framework
libraries.

Example plugin structure::

    from cumulusci.core.plugins import CCIPlugin, PluginManifest

    class MyPlugin(CCIPlugin):
        @property
        def manifest(self) -> PluginManifest:
            return PluginManifest(
                name="my-plugin",
                version="1.0.0",
                tasks={"my_task": "my_plugin.tasks.MyTask"},
            )

To register a plugin, add an entry point in your pyproject.toml::

    [project.entry-points."cumulusci.plugins"]
    my-plugin = "my_plugin:MyPlugin"

Example using hooks::

    from cumulusci.core.plugins import CCIPlugin, PluginManifest
    from cumulusci.core.plugins.hooks import hookimpl

    class MyPlugin(CCIPlugin):
        @property
        def manifest(self) -> PluginManifest:
            return PluginManifest(name="my-plugin", version="1.0.0")

        @hookimpl
        def cci_task_complete(self, task, result):
            print(f"Task {task.name} completed!")
"""

from cumulusci.core.plugins.base import (
    CCIPlugin,
    PluginInfo,
    PluginManifest,
    TrustLevel,
)
from cumulusci.core.plugins.exceptions import (
    PluginConfigError,
    PluginConflictError,
    PluginException,
    PluginLoadError,
    PluginNotFoundError,
    PluginRegistryError,
    PluginTrustError,
    PluginVersionError,
)
from cumulusci.core.plugins.hooks import (
    CCIHookSpec,
    HookManager,
    get_hook_manager,
    hookimpl,
    hookspec,
    reset_hook_manager,
)
from cumulusci.core.plugins.manager import (
    PluginManager,
    get_plugin_manager,
    reset_plugin_manager,
)
from cumulusci.core.plugins.registry import (
    PluginRegistry,
    PluginRegistryEntry,
    get_plugin_registry,
    reset_plugin_registry,
)

__all__ = [
    # Base classes
    "CCIPlugin",
    "PluginManifest",
    "PluginInfo",
    "TrustLevel",
    # Manager
    "PluginManager",
    "get_plugin_manager",
    "reset_plugin_manager",
    # Hooks
    "CCIHookSpec",
    "HookManager",
    "hookimpl",
    "hookspec",
    "get_hook_manager",
    "reset_hook_manager",
    # Registry
    "PluginRegistry",
    "PluginRegistryEntry",
    "get_plugin_registry",
    "reset_plugin_registry",
    # Exceptions
    "PluginException",
    "PluginNotFoundError",
    "PluginLoadError",
    "PluginConfigError",
    "PluginTrustError",
    "PluginConflictError",
    "PluginVersionError",
    "PluginRegistryError",
]
