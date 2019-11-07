import logging


class BaseConfig(object):
    """ BaseConfig provides a common interface for nested access for all Config objects in CCI. """

    defaults = {}

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
        """ Subclasses may override this method to initialize :py:attr:`~config` """
        pass

    def __getattr__(self, name):
        tree = name.split("__")
        if name.startswith("_"):
            raise AttributeError(f"Attribute {name} not found")
        value = None
        value_found = False
        config = self.config
        if len(tree) > 1:
            # Walk through the config dictionary using __ as a delimiter
            for key in tree[:-1]:
                config = config.get(key)
                if config is None:
                    break
        if config and tree[-1] in config:
            value = config[tree[-1]]
            value_found = True

        if value_found:
            return value
        else:
            return self.defaults.get(name)
