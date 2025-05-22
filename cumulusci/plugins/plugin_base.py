import inspect
import logging
import os
from abc import ABC
from pathlib import Path
from typing import Optional

from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load


class PluginBase(ABC):

    name: str = None
    api_name: str = None
    version: str = "0.1"
    author: str = "Unknown"
    priority: int = 0
    description: str = "No description provided."
    plugin_config_file: str = "cumulusci_plugin.yml"
    path: str = None
    plugin_project_config: Optional[dict] = None

    def __init_subclass__(cls, **kwargs):
        for required in (
            "name",
            "api_name",
        ):
            if not getattr(cls, required):
                raise TypeError(
                    f"Can't instantiate abstract class {cls.__name__} without {required} attribute defined"
                )
        return super().__init_subclass__(**kwargs)

    def __init__(self, **kwargs) -> None:
        self.logger = kwargs.get("logger", logging.getLogger(self.__class__.__name__))
        self.path = inspect.getfile(self.__class__)

    def initialize(self) -> None:
        """Initialize the plugin. This method is called when the plugin is loaded."""
        self.logger.info(
            f"Initializing plugin: {self.name}({self.api_name}) v{self.version} by {self.author}"
        )
        self._load_config()
        self.logger.info(f"Loaded plugin: {self.name}({self.api_name}) v{self.version}")

    def teardown(self) -> None:
        """Tear down the plugin. This method is called when the plugin is unloaded."""
        self.logger.info(f"Tearing down plugin: {self.name}({self.api_name})")

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
                f"{self.api_name}: Plugin configuration file found at: {config_plugin_path}"
            )
            self.plugin_project_config = cci_safe_load(
                config_plugin_path, context=self.name, logger=self.logger
            )

            self.logger.info(
                f"{self.api_name}: Plugin project configuration loaded successfully."
            )
        else:
            self.logger.warning(f"{self.api_name}: No plugin configuration file found.")
