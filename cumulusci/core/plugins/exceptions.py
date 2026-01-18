"""Plugin-related exceptions for CumulusCI."""

from cumulusci.core.exceptions import CumulusCIException


class PluginException(CumulusCIException):
    """Base exception for plugin-related errors."""


class PluginNotFoundError(PluginException):
    """Raised when a plugin cannot be found."""


class PluginLoadError(PluginException):
    """Raised when a plugin fails to load."""


class PluginConfigError(PluginException):
    """Raised when there's an error in plugin configuration."""


class PluginTrustError(PluginException):
    """Raised when a plugin's trust level is insufficient for an operation."""


class PluginConflictError(PluginException):
    """Raised when there's a conflict between plugins."""


class PluginVersionError(PluginException):
    """Raised when a plugin version is incompatible."""


class PluginRegistryError(PluginException):
    """Raised when there's an error accessing the plugin registry."""
