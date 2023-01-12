import logging
import os
import warnings
from functools import lru_cache
from typing import Any, Dict, Optional

# turn on strictness.
# delete this when strictness is mandatory
STRICT_GETATTR = os.environ.get("STRICT_GETATTR")
CHECK_CONFIG_TYPES = os.environ.get("CHECK_CONFIG_TYPES")


class BaseConfig(object):
    """BaseConfig provides a common interface for nested access for all Config objects in CCI."""

    defaults = {}
    config: dict
    logger: logging.Logger

    def __init__(self, config: Optional[dict] = None, keychain=None):
        if config is None:
            self.config = {}
        else:
            types = self._all_allowed_names()
            if CHECK_CONFIG_TYPES:
                for k, v in config.items():
                    type_for_value = types.get(k)
                    if not type_for_value:
                        warnings.warn(f"{k}: {v} not declared for {type(self)}")
                    if (v is not None) and (type_for_value is not None):
                        assert isinstance(
                            v, type_for_value
                        ), f"{k}: {v} should be of type {type_for_value}, not {type(v)} for {type(self)}"
            self.config = config.copy()

        self._init_logger()
        self._load_config()

    def _init_logger(self):
        """Initializes self.logger"""
        self.logger = logging.getLogger(__name__)

    def _load_config(self):
        """Subclasses may override this method to initialize :py:attr:`~config`"""
        pass

    @classmethod
    def _allowed_names(cls) -> Dict[str, type]:
        return getattr(cls, "__annotations__", {})

    # long term plan is to get rid of this
    def __getattr__(self, name: str) -> Any:
        """Look up a property in a sub-dictionary

        Property names should be declared in each Config class with type annotations.
        """
        if not name.startswith("_"):
            first_part = name.split("__")[0]
            if first_part not in self._all_allowed_names():
                message = (
                    f"Property `{first_part}` is unknown on class `{self.__class__.__name__}`. "
                    + "Either declare it in the type declaration or use lookup() to look it up dynamically"
                )
                warnings.warn(
                    message,
                    DeprecationWarning,
                )

                assert not STRICT_GETATTR, message
        return self.lookup(name, already_called_getattr=True)

    @classmethod
    @lru_cache
    def _all_allowed_names(cls) -> Dict[str, type]:
        "Allowed names from this class and its base classes"
        allowed_names_from_all_base_classes = (
            baseclass._allowed_names()  # type: ignore
            for baseclass in cls.__mro__
            if hasattr(baseclass, "_allowed_names")
        )
        ret = {}
        for d in allowed_names_from_all_base_classes:
            ret.update(d)
        return ret

    def lookup(
        self, name: str, default: Any = None, already_called_getattr: bool = False
    ) -> Any:
        tree = name.split("__")
        if name.startswith("_"):
            raise AttributeError(f"Attribute {name} not found")
        value: Any = None
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
            if not already_called_getattr and hasattr(self, name):
                return getattr(self, name)
            else:
                return self.defaults.get(name, default)
