from __future__ import unicode_literals
import os

from cumulusci.core.config.BaseProjectConfig import BaseProjectConfig
from cumulusci.core.config import BaseTaskFlowConfig


class BaseGlobalConfig(BaseTaskFlowConfig):
    """ Base class for the global config which contains all configuration not specific to projects """
    project_config_class = BaseProjectConfig

    config_local_dir = '.cumulusci'

    def list_projects(self):
        """ Returns a list of project names """
        raise NotImplementedError('Subclasses must provide an implementation')

    def get_project_config(self):
        """ Returns a ProjectConfig for the given project """
        return self.project_config_class(self)

    def create_project(self, project_name, config):
        """ Creates a new project configuration and returns it """
        raise NotImplementedError('Subclasses must provide an implementation')
