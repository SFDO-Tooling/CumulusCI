import inspect
import logging
import os
from abc import ABC
from pathlib import Path
from typing import Optional

from cumulusci.utils.yaml.cumulusci_yml import Plugin, cci_safe_load


class PluginBase(ABC):
    plugin: Plugin
    plugin_config_file: str = "cumulusci_plugin.yml"
    path: str = None
    plugin_project_config: Optional[dict] = None

    def __init__(self, **kwargs) -> None:
        self.logger = kwargs.get("logger", logging.getLogger(self.__class__.__name__))
        self.path = inspect.getfile(self.__class__)
        self._load_config()

    @property
    def api_name(self) -> str:
        """Returns the api_name of the plugin."""
        return self._api_name

    @api_name.setter
    def api_name(self, value: str) -> None:
        """Sets the api_name of the plugin."""
        self._api_name = value

    @property
    def name(self) -> str:
        """Returns the name of the plugin."""
        return self.plugin.name if self.plugin else "Unnamed Plugin"

    @property
    def version(self) -> str:
        """Returns the version of the plugin."""
        return self.plugin.version if self.plugin else "0.0.0"

    def initialize(self) -> None:
        """Initialize the plugin. This method is called when the plugin is loaded."""
        self.logger.info(
            f"Initializing plugin: {self.name}) v{self.version} by {self.plugin.author}"
        )
        self._initialize()
        self.logger.info(f"Loaded plugin: {self.name}) v{self.version}")

    def teardown(self) -> None:
        """Tear down the plugin. This method is called when the plugin is unloaded."""
        self.logger.info(f"Tearing down plugin: {self.name})")

    @property
    def config_plugin_path(self) -> Optional[str]:
        """Returns the path to the plugin configuration file."""
        plugin_config_path = os.path.join(
            os.path.dirname(self.path), self.plugin_config_file
        )
        plugin_path = Path(plugin_config_path)
        if plugin_path.is_file():
            return str(plugin_path)
        return None

    def _load_config(self) -> None:
        """Loads the plugin configuration file if it exists."""
        config_plugin_path = self.config_plugin_path
        if config_plugin_path:
            self.logger.info(
                f"{self.__class__.__name__}: Plugin configuration file found at: {config_plugin_path}"
            )
            self.plugin_project_config = cci_safe_load(
                config_plugin_path, context=self.__class__.__name__, logger=self.logger
            )

            for plugin_name in self.plugin_project_config.get("plugins", {}).keys():
                self._api_name = plugin_name
                self.plugin = Plugin(
                    **self.plugin_project_config.get("plugins", {}).get(plugin_name, {})
                )
                break

            self.logger.info(
                f"{self.name}: Plugin project configuration loaded successfully."
            )
        else:
            self.logger.warning(
                f"{self.__class__.__name__}: No plugin configuration file found."
            )

    def _initialize(self) -> None:
        """Override this method to add custom initialization logic."""
        pass
