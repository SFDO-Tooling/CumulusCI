import importlib.metadata
import logging
from functools import lru_cache
from typing import Dict, List, Optional, Type

from cumulusci.plugins.plugin_base import PluginBase


def get_plugin_manager(logger: logging.Logger) -> "PluginManager":
    """Get the plugin manager instance."""
    return PluginManager(logger=logger)


@lru_cache(maxsize=50)
def load_plugins(logger: logging.Logger) -> List[PluginBase]:
    """Load all available plugins and return them as a list."""
    manager = get_plugin_manager(logger)
    plugins = []
    for name, plugin_class in manager._plugins.items():
        try:
            plugin = plugin_class(logger=logger)
            plugin.initialize()
            plugins.append(plugin)
        except Exception as e:
            logger.warning(f"Failed to initialize plugin {name}: {str(e)}")
    return plugins


class PluginManager:
    """Manages the loading and access of CumulusCI plugins."""

    def __init__(self, logger: logging.Logger) -> None:
        self._plugins: Dict[str, Type[PluginBase]] = {}
        self.logger = logger
        self._load_plugins()

    def _load_plugins(self) -> None:
        """Load all available plugins."""
        try:
            for entry_point in importlib.metadata.entry_points().select(
                group="cumulusci.plugins"
            ):
                try:
                    plugin_class = entry_point.load()
                    self._plugins[entry_point.name] = plugin_class
                except Exception as e:
                    self.logger.warning(
                        f"Failed to load plugin {entry_point.name}: {str(e)}"
                    )
        except Exception as e:
            self.logger.warning(f"Failed to load plugins: {str(e)}")

    def get_plugin(self, name: str) -> Optional[Type[PluginBase]]:
        """Get a plugin by name."""
        return self._plugins.get(name)

    def list_plugins(self) -> List[str]:
        """List all available plugin names."""
        return list(self._plugins.keys())
