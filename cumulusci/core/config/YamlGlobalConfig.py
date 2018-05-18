from __future__ import unicode_literals
import os

import hiyapyco
import yaml

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config.YamlProjectConfig import YamlProjectConfig

__location__ = os.path.dirname(os.path.realpath(__file__))


class YamlGlobalConfig(BaseGlobalConfig):
    config_filename = 'cumulusci.yml'
    config_local_dir = '.cumulusci'
    project_config_class = YamlProjectConfig

    def __init__(self):
        self.config_global_local = {}
        self.config_global = {}
        super(YamlGlobalConfig, self).__init__()

    @property
    def config_global_local_path(self):
        directory = os.path.join(
            os.path.expanduser('~'),
            self.config_local_dir,
        )
        if not os.path.exists(directory):
            os.makedirs(directory)

        config_path = os.path.join(
            directory,
            self.config_filename,
        )
        if not os.path.isfile(config_path):
            return None

        return config_path

    def _load_config(self):
        """ Loads the local configuration """
        # load the global config
        self._load_global_config()

        merge_yaml = [self.config_global_path]

        # Load the local config
        if self.config_global_local_path:
            config = yaml.load(open(self.config_global_local_path, 'r'))
            self.config_global_local = config
            if config:
                merge_yaml.append(self.config_global_local_path)

        self.config = hiyapyco.load(
            *merge_yaml,
            method=hiyapyco.METHOD_MERGE,
            loglevel='INFO'
        )

    @property
    def config_global_path(self):
        return os.path.abspath(os.path.join(
            __location__,
            '..',
            '..',
            self.config_filename,
        ))

    def _load_global_config(self):
        """ Loads the configuration for the project """

        # Load the global cumulusci.yml file
        with open(self.config_global_path, 'r') as f_config:
            config = yaml.load(f_config)
        self.config_global = config
