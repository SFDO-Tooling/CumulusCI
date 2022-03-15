import logging
import os
import warnings
from functools import lru_cache, reduce

# turn on strictness.
# delete this when strictness is mandatory
STRICT_GETATTR = os.environ.get("STRICT_GETATTR")


class BaseConfig(object):
    """BaseConfig provides a common interface for nested access for all Config objects in CCI."""

    defaults = {}
    config: dict

    def __init__(self, config=None, keychain=None):
        if config is None:
            self.config = {}
        else:
            self.config = config
        self._init_logger()
        self._load_config()

    def _init_logger(self):
        """Initializes self.logger"""
        self.logger = logging.getLogger(__name__)

    def _load_config(self):
        """Subclasses may override this method to initialize :py:attr:`~config`"""
        pass

    @classmethod
    def allowed_names(cls) -> set:
        properties = set(dir(cls))
        annotations = set(getattr(cls, "__annotations__", {}))
        return properties.union(annotations)

    # long term plan is to get rid of this
    def __getattr__(self, name):
        if not name.startswith("_"):
            first_part = name.split("__")[0]
            if (
                first_part
                not in self.all_allowed_names()
                # and first_part not in self.config
            ):
                warnings.warn(
                    f"__getattr__ on Configs is deprecated: `{first_part}` on `{self.__class__.__name__}`",
                    DeprecationWarning,
                )

                assert (
                    not STRICT_GETATTR
                ), f"__getattr__ on Configs is deprecated: `{first_part}` on `{self.__class__.__name__}`"
        return self.lookup(name)

    @classmethod
    @lru_cache
    def all_allowed_names(cls):
        "Allowed names from this class and its base classes"
        allowed_names_from_all_base_classes = (
            baseclass.allowed_names()
            for baseclass in cls.__mro__
            if hasattr(baseclass, "allowed_names")
        )
        return reduce(
            set.union,
            allowed_names_from_all_base_classes,
            cls.allowed_names(),
        )

    def lookup(self, name, default=None):
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
            return self.defaults.get(name, default)
