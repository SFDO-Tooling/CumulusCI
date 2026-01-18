"""Plugin registry for discovering and managing CumulusCI plugins.

The plugin registry provides a centralized listing of known CumulusCI plugins,
including their versions, compatibility information, and verification status.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import List, Literal, Optional

import requests

from cumulusci.core.plugins.exceptions import PluginRegistryError

logger = logging.getLogger(__name__)

# Default registry URL - hosted on GitHub Pages
DEFAULT_REGISTRY_URL = (
    "https://claritisoftware.github.io/CumulusCI/plugins/registry.json"
)

# Cache timeout in seconds
CACHE_TIMEOUT = 300  # 5 minutes


@dataclass
class PluginRegistryEntry:
    """An entry in the plugin registry.

    Attributes:
        name: Plugin name
        pypi_package: Name of the PyPI package
        description: Short description of the plugin
        category: Plugin category (official, verified, community)
        homepage: URL to plugin homepage/repository
        author: Plugin author
        min_cci_version: Minimum compatible CumulusCI version
        max_cci_version: Maximum compatible CumulusCI version (optional)
        tags: List of tags for searching
        deprecated: Whether the plugin is deprecated
        deprecated_message: Message explaining deprecation
    """

    name: str
    pypi_package: str
    description: str
    category: Literal["official", "verified", "community"]
    homepage: str
    author: str
    min_cci_version: str
    max_cci_version: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    deprecated: bool = False
    deprecated_message: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "PluginRegistryEntry":
        """Create an entry from a dictionary."""
        return cls(
            name=data["name"],
            pypi_package=data["pypi_package"],
            description=data.get("description", ""),
            category=data.get("category", "community"),
            homepage=data.get("homepage", ""),
            author=data.get("author", ""),
            min_cci_version=data.get("min_cci_version", ""),
            max_cci_version=data.get("max_cci_version"),
            tags=data.get("tags", []),
            deprecated=data.get("deprecated", False),
            deprecated_message=data.get("deprecated_message", ""),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "pypi_package": self.pypi_package,
            "description": self.description,
            "category": self.category,
            "homepage": self.homepage,
            "author": self.author,
            "min_cci_version": self.min_cci_version,
            "max_cci_version": self.max_cci_version,
            "tags": self.tags,
            "deprecated": self.deprecated,
            "deprecated_message": self.deprecated_message,
        }


class PluginRegistry:
    """Remote registry of known CumulusCI plugins.

    The registry is a JSON file hosted online that contains metadata
    about available CumulusCI plugins. It supports searching and
    filtering by category.

    Example usage::

        registry = PluginRegistry()
        plugins = registry.fetch_registry()

        # Search for plugins
        results = registry.search("slack")

        # Get only verified plugins
        verified = registry.get_verified_plugins()
    """

    def __init__(self, registry_url: str = DEFAULT_REGISTRY_URL):
        """Initialize the registry client.

        Args:
            registry_url: URL to the registry JSON file
        """
        self.registry_url = registry_url
        self._cache: Optional[List[PluginRegistryEntry]] = None
        self._cache_version: Optional[str] = None

    def fetch_registry(self, force_refresh: bool = False) -> List[PluginRegistryEntry]:
        """Fetch the latest plugin registry from the remote URL.

        Args:
            force_refresh: Force a refresh even if cached data exists

        Returns:
            List of PluginRegistryEntry objects

        Raises:
            PluginRegistryError: If fetching fails
        """
        if self._cache is not None and not force_refresh:
            return self._cache

        try:
            response = requests.get(self.registry_url, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise PluginRegistryError(f"Failed to fetch plugin registry: {e}")
        except json.JSONDecodeError as e:
            raise PluginRegistryError(f"Invalid registry JSON: {e}")

        self._cache_version = data.get("version", "unknown")

        plugins = []
        for plugin_data in data.get("plugins", []):
            try:
                entry = PluginRegistryEntry.from_dict(plugin_data)
                plugins.append(entry)
            except (KeyError, ValueError) as e:
                logger.warning(f"Skipping invalid plugin entry: {e}")
                continue

        self._cache = plugins
        logger.info(
            f"Loaded {len(plugins)} plugins from registry (version {self._cache_version})"
        )
        return plugins

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        include_deprecated: bool = False,
    ) -> List[PluginRegistryEntry]:
        """Search for plugins by name, description, or tags.

        Args:
            query: Search query string
            category: Filter by category (official, verified, community)
            include_deprecated: Include deprecated plugins in results

        Returns:
            List of matching PluginRegistryEntry objects
        """
        plugins = self.fetch_registry()
        query_lower = query.lower()

        results = []
        for plugin in plugins:
            # Skip deprecated unless requested
            if plugin.deprecated and not include_deprecated:
                continue

            # Filter by category
            if category and plugin.category != category:
                continue

            # Search in name, description, and tags
            if (
                query_lower in plugin.name.lower()
                or query_lower in plugin.description.lower()
                or any(query_lower in tag.lower() for tag in plugin.tags)
            ):
                results.append(plugin)

        return results

    def get_verified_plugins(self) -> List[PluginRegistryEntry]:
        """Get only verified plugins.

        Returns:
            List of verified PluginRegistryEntry objects
        """
        plugins = self.fetch_registry()
        return [p for p in plugins if p.category == "verified" and not p.deprecated]

    def get_official_plugins(self) -> List[PluginRegistryEntry]:
        """Get only official plugins.

        Returns:
            List of official PluginRegistryEntry objects
        """
        plugins = self.fetch_registry()
        return [p for p in plugins if p.category == "official" and not p.deprecated]

    def get_plugin(self, name: str) -> Optional[PluginRegistryEntry]:
        """Get a specific plugin by name.

        Args:
            name: Plugin name

        Returns:
            PluginRegistryEntry if found, None otherwise
        """
        plugins = self.fetch_registry()
        for plugin in plugins:
            if plugin.name == name:
                return plugin
        return None

    def check_compatibility(self, plugin_name: str) -> dict:
        """Check if a plugin is compatible with the current CumulusCI version.

        Args:
            plugin_name: Name of the plugin to check

        Returns:
            Dictionary with compatibility information:
            - compatible: Boolean
            - message: Explanation message
            - min_version: Minimum required version
            - max_version: Maximum supported version (if any)
        """
        from packaging.version import Version

        import cumulusci

        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return {
                "compatible": False,
                "message": f"Plugin '{plugin_name}' not found in registry",
            }

        current_version = Version(cumulusci.__version__)
        result = {
            "compatible": True,
            "message": "Compatible",
            "min_version": plugin.min_cci_version,
            "max_version": plugin.max_cci_version,
        }

        if plugin.min_cci_version:
            try:
                min_version = Version(plugin.min_cci_version)
                if current_version < min_version:
                    result["compatible"] = False
                    result[
                        "message"
                    ] = f"Requires CumulusCI >= {plugin.min_cci_version}"
            except Exception:
                pass

        if plugin.max_cci_version:
            try:
                max_version = Version(plugin.max_cci_version)
                if current_version > max_version:
                    result["compatible"] = False
                    result[
                        "message"
                    ] = f"Requires CumulusCI <= {plugin.max_cci_version}"
            except Exception:
                pass

        if plugin.deprecated:
            result[
                "message"
            ] = f"Plugin is deprecated: {plugin.deprecated_message or 'No reason given'}"

        return result


# Global registry instance
_registry: Optional[PluginRegistry] = None


def get_plugin_registry() -> PluginRegistry:
    """Get the global plugin registry instance.

    Returns:
        The global PluginRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry


def reset_plugin_registry() -> None:
    """Reset the global plugin registry.

    This is primarily useful for testing.
    """
    global _registry
    _registry = None
