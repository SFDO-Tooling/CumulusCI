from __future__ import unicode_literals
import os
from collections import OrderedDict

from cumulusci.core.utils import ordered_yaml_load, merge_config
from cumulusci.core.config.BaseProjectConfig import BaseProjectConfig
from cumulusci.core.config import BaseTaskFlowConfig

__location__ = os.path.dirname(os.path.realpath(__file__))


class BaseGlobalConfig(BaseTaskFlowConfig):
    """ Base class for the global config which contains all configuration not specific to projects """

    config_filename = "cumulusci.yml"
    project_config_class = BaseProjectConfig
    config_local_dir = ".cumulusci"

    def __init__(self, config=None):
        self.config_global_local = {}
        self.config_global = {}
        super(BaseGlobalConfig, self).__init__(config)

    def list_projects(self):
        """ Returns a list of project names """
        raise NotImplementedError("Subclasses must provide an implementation")

    def get_project_config(self):
        """ Returns a ProjectConfig for the given project """
        return self.project_config_class(self)

    def create_project(self, project_name, config):
        """ Creates a new project configuration and returns it """
        raise NotImplementedError("Subclasses must provide an implementation")

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
        # load the global config
        with open(self.config_global_path, "r") as f_config:
            config = ordered_yaml_load(f_config)
        self.config_global = config

        # Load the local config
        if self.config_global_local_path:
            config = ordered_yaml_load(open(self.config_global_local_path, "r"))
            self.config_global_local = config

        self.config = merge_config(
            OrderedDict(
                [
                    ("global_local", self.config_global_local),
                    ("global_config", self.config_global),
                ]
            )
        )
