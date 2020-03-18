import os

from cumulusci.core.utils import merge_config
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.config import BaseTaskFlowConfig
from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load

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
        BaseGlobalConfig.config_global = cci_safe_load(self.config_global_path)

        # Load the local config
        if self.config_global_local_path:
            config = cci_safe_load(self.config_global_local_path)
        else:
            config = {}
        BaseGlobalConfig.config_global_local = config

        BaseGlobalConfig.config = merge_config(
            {
                "global_config": BaseGlobalConfig.config_global,
                "global_local": BaseGlobalConfig.config_global_local,
            }
        )
