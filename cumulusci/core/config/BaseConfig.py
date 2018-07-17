from __future__ import unicode_literals
from builtins import object
import logging


class BaseConfig(object):
    """ Base class for all configuration objects """

    defaults = {}
    search_path = ['config']

    def __init__(self, config=None):
        if config is None:
            self.config = {}
        else:
            self.config = config
        self._init_logger()
        self._load_config()

    def _init_logger(self):
        """ Initializes self.logger """
        self.logger = logging.getLogger(__name__)

    def _load_config(self):
        """ Performs the logic to initialize self.config """
        pass

    def __getattr__(self, name):
        tree = name.split('__')
        if name.startswith('_'):
            raise AttributeError('Attribute {} not found'.format(name))
        value = None
        value_found = False
        for attr in self.search_path:
            config = getattr(self, attr)
            if len(tree) > 1:
                # Walk through the config dictionary using __ as a delimiter
                for key in tree[:-1]:
                    config = config.get(key)
                    if config is None:
                        break
            if config is None:
                continue

            if tree[-1] in config:
                value = config[tree[-1]]
                value_found = True
                break

        if value_found:
            return value
        else:
            return self.defaults.get(name)
