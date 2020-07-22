import os

import yaml
from pathlib import Path

from cumulusci.core.utils import merge_config
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.config import BaseTaskFlowConfig

__location__ = os.path.dirname(os.path.realpath(__file__))


class UniversalConfig(BaseTaskFlowConfig):
    """ Base class for the global config which contains all configuration not specific to projects """

    config = None
    config_filename = "cumulusci.yml"
    project_config_class = BaseProjectConfig

    def __init__(self, config=None):
        self._init_logger()
        self._load_config()

    @property
    def cumulusci_config_dir(self):
        """Get the root directory for storing persistent data, as an instance property"""
        return self.default_cumulusci_dir()

    @staticmethod
    def default_cumulusci_dir():
        """Get the root directory for storing persistent data (~/.cumulusci)

        Creates it if it doesn't exist yet.
        """
        config_dir = Path.home() / ".cumulusci"

        if not config_dir.exists():
            config_dir.mkdir(parents=True)

        return config_dir

    @property
    def config_global_path(self):
        directory = self.cumulusci_config_dir
        if not os.path.exists(directory):
            os.makedirs(directory)

        config_path = os.path.join(directory, self.config_filename)
        if not os.path.isfile(config_path):
            return None

        return config_path

    @property
    def config_universal_path(self):
        return os.path.abspath(
            os.path.join(__location__, "..", "..", self.config_filename)
        )

    def _load_config(self):
        """ Loads the local configuration """
        # avoid loading multiple times
        if UniversalConfig.config is not None:
            return

        # load the global config
        with open(self.config_universal_path, "r") as f_config:
            config = yaml.safe_load(f_config)
        UniversalConfig.config_universal = config

        # Load the local config
        if self.config_global_path:
            with open(self.config_global_path, "r") as f:
                config = yaml.safe_load(f)
        else:
            config = {}
        UniversalConfig.config_global = config

        UniversalConfig.config = merge_config(
            {
                "universal_config": UniversalConfig.config_universal,
                "global_config": UniversalConfig.config_global,
            }
        )
