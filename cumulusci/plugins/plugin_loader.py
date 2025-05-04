import logging
from typing import Optional

import pkg_resources

from cumulusci.plugins import PluginBase


def load_plugins(logger: Optional[logging.Logger] = None) -> list["PluginBase"]:
    """Load all plugins from entry points and return a list of plugins."""
    plugins = []
    for entry_point in pkg_resources.iter_entry_points("cumulusci.plugins"):
        try:
            plugin_class = entry_point.load()

            if issubclass(plugin_class, PluginBase):
                instance = plugin_class()
                instance.initialize()
                plugins.append(instance)
        except Exception as e:
            print(f"[PluginLoader] Failed to load plugin {entry_point.name}: {e}")

    plugins.sort(key=lambda p: getattr(p, "priority", 0), reverse=True)
    return plugins
