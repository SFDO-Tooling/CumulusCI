import os
from pathlib import Path

from cumulusci.core.config import BaseTaskFlowConfig
from cumulusci.core.config.project_config import (
    BaseProjectConfig,
    ProjectConfigPropertiesMixin,
)
from cumulusci.core.utils import merge_config
from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load

__location__ = os.path.dirname(os.path.realpath(__file__))


class UniversalConfig(BaseTaskFlowConfig, ProjectConfigPropertiesMixin):
    """Base class for the global config which contains all configuration not specific to projects"""

    project_local_dir: str
    cli: dict

    config = None
    config_filename = "cumulusci.yml"
    project_config_class = BaseProjectConfig
    universal_config_obj = None

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
        """The global config path. Usually ~/.cumulusci/cumulusci.yml"""
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
        """Loads the local configuration"""
        # avoid loading multiple times
        if UniversalConfig.config is not None:
            return

        # load the universal config
        UniversalConfig.config_universal = cci_safe_load(self.config_universal_path)

        # Load the local config
        if self.config_global_path:
            config = cci_safe_load(self.config_global_path)
        else:
            config = {}
        UniversalConfig.config_global = config

        UniversalConfig.config = merge_config(
            {
                "universal_config": UniversalConfig.config_universal,
                "global_config": UniversalConfig.config_global,
            }
        )
