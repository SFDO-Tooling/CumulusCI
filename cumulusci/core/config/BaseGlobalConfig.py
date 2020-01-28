import os

import yaml

from cumulusci.core.utils import merge_config
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.config import BaseTaskFlowConfig

__location__ = os.path.dirname(os.path.realpath(__file__))


class BaseGlobalConfig(BaseTaskFlowConfig):
    """ Base class for the global config which contains all configuration not specific to projects """

    config = None
    config_filename = "cumulusci.yml"
    project_config_class = BaseProjectConfig
    config_local_dir = ".cumulusci"

    def __init__(self, config=None):
        self._init_logger()
        self._load_config()

    @property
    def config_global_local_path(self):
        directory = os.path.join(os.path.expanduser("~"), self.config_local_dir)
        if not os.path.exists(directory):
            os.makedirs(directory)

        config_path = os.path.join(directory, self.config_filename)
        if not os.path.isfile(config_path):
            return None

        return config_path

    @property
    def config_global_path(self):
        return os.path.abspath(
            os.path.join(__location__, "..", "..", self.config_filename)
        )

    def _load_config(self):
        """ Loads the local configuration """
        # avoid loading multiple times
        if BaseGlobalConfig.config is not None:
            return

        # load the global config
        with open(self.config_global_path, "r") as f_config:
            config = yaml.safe_load(f_config)
        BaseGlobalConfig.config_global = config

        # Load the local config
        if self.config_global_local_path:
            with open(self.config_global_local_path, "r") as f:
                config = yaml.safe_load(f)
        else:
            config = {}
        BaseGlobalConfig.config_global_local = config

        BaseGlobalConfig.config = merge_config(
            {
                "global_config": BaseGlobalConfig.config_global,
                "global_local": BaseGlobalConfig.config_global_local,
            }
        )
