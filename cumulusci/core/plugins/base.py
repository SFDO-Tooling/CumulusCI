"""Base classes and types for the CumulusCI plugin system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from cumulusci.core.runtime import BaseCumulusCI


class TrustLevel(Enum):
    """Trust levels for plugins.

    Trust levels control what a plugin can do:
    - UNTRUSTED: Read-only access to configuration
    - STANDARD: Can register tasks, flows, and services (default)
    - TRUSTED: Full access including CLI extension and credential access
    """

    UNTRUSTED = "untrusted"
    STANDARD = "standard"
    TRUSTED = "trusted"

    def __ge__(self, other: "TrustLevel") -> bool:
        """Compare trust levels for >= operator."""
        order = [TrustLevel.UNTRUSTED, TrustLevel.STANDARD, TrustLevel.TRUSTED]
        return order.index(self) >= order.index(other)

    def __gt__(self, other: "TrustLevel") -> bool:
        """Compare trust levels for > operator."""
        order = [TrustLevel.UNTRUSTED, TrustLevel.STANDARD, TrustLevel.TRUSTED]
        return order.index(self) > order.index(other)

    def __le__(self, other: "TrustLevel") -> bool:
        """Compare trust levels for <= operator."""
        return not self.__gt__(other)

    def __lt__(self, other: "TrustLevel") -> bool:
        """Compare trust levels for < operator."""
        return not self.__ge__(other)


@dataclass
class PluginManifest:
    """Manifest describing a plugin's capabilities and requirements.

    Attributes:
        name: Unique identifier for the plugin
        version: Plugin version string
        description: Human-readable description
        tasks: Mapping of task names to class paths
        flows: Mapping of flow names to flow configurations
        services: Mapping of service type names to service definitions
        cli_commands: List of CLI command entry points
        robot_libraries: Mapping of library names to class paths
        required_trust_level: Minimum trust level required for the plugin
        min_cci_version: Minimum CumulusCI version required
        max_cci_version: Maximum CumulusCI version supported (optional)
        homepage: URL to plugin homepage or documentation
        author: Plugin author name or organization
    """

    name: str
    version: str
    description: str = ""
    tasks: Dict[str, str] = field(default_factory=dict)
    flows: Dict[str, dict] = field(default_factory=dict)
    services: Dict[str, dict] = field(default_factory=dict)
    cli_commands: List[str] = field(default_factory=list)
    robot_libraries: Dict[str, str] = field(default_factory=dict)
    required_trust_level: TrustLevel = TrustLevel.STANDARD
    min_cci_version: Optional[str] = None
    max_cci_version: Optional[str] = None
    homepage: Optional[str] = None
    author: Optional[str] = None

    def __post_init__(self):
        """Validate manifest after initialization."""
        if not self.name:
            raise ValueError("Plugin name is required")
        if not self.version:
            raise ValueError("Plugin version is required")

    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to a dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "tasks": self.tasks,
            "flows": self.flows,
            "services": self.services,
            "cli_commands": self.cli_commands,
            "robot_libraries": self.robot_libraries,
            "required_trust_level": self.required_trust_level.value,
            "min_cci_version": self.min_cci_version,
            "max_cci_version": self.max_cci_version,
            "homepage": self.homepage,
            "author": self.author,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginManifest":
        """Create a manifest from a dictionary."""
        trust_level = data.get("required_trust_level", "standard")
        if isinstance(trust_level, str):
            trust_level = TrustLevel(trust_level)

        return cls(
            name=data["name"],
            version=data["version"],
            description=data.get("description", ""),
            tasks=data.get("tasks", {}),
            flows=data.get("flows", {}),
            services=data.get("services", {}),
            cli_commands=data.get("cli_commands", []),
            robot_libraries=data.get("robot_libraries", {}),
            required_trust_level=trust_level,
            min_cci_version=data.get("min_cci_version"),
            max_cci_version=data.get("max_cci_version"),
            homepage=data.get("homepage"),
            author=data.get("author"),
        )


class CCIPlugin(ABC):
    """Abstract base class for CumulusCI plugins.

    All plugins must extend this class and implement the manifest property.
    Plugins can optionally override the on_load and on_unload methods to
    perform initialization and cleanup.

    Example:
        class MyPlugin(CCIPlugin):
            @property
            def manifest(self) -> PluginManifest:
                return PluginManifest(
                    name="my-plugin",
                    version="1.0.0",
                    description="My custom plugin",
                    tasks={
                        "my_task": "my_plugin.tasks.MyTask",
                    },
                )

            def on_load(self, runtime):
                self.logger.info("Plugin loaded!")
    """

    def __init__(self):
        """Initialize the plugin."""
        self._runtime: Optional["BaseCumulusCI"] = None
        self._enabled: bool = False
        self._config: Dict[str, Any] = {}

    @property
    @abstractmethod
    def manifest(self) -> PluginManifest:
        """Return the plugin's manifest.

        The manifest describes the plugin's capabilities, including
        tasks, flows, services, CLI commands, and Robot Framework libraries.
        """
        ...

    @property
    def name(self) -> str:
        """Return the plugin name from the manifest."""
        return self.manifest.name

    @property
    def version(self) -> str:
        """Return the plugin version from the manifest."""
        return self.manifest.version

    @property
    def runtime(self) -> Optional["BaseCumulusCI"]:
        """Return the CumulusCI runtime instance."""
        return self._runtime

    @runtime.setter
    def runtime(self, value: Optional["BaseCumulusCI"]) -> None:
        """Set the CumulusCI runtime instance."""
        self._runtime = value

    @property
    def enabled(self) -> bool:
        """Return whether the plugin is currently enabled."""
        return self._enabled

    @property
    def config(self) -> Dict[str, Any]:
        """Return the plugin's configuration from cumulusci.yml."""
        return self._config

    def on_load(self, runtime: "BaseCumulusCI") -> None:
        """Called when the plugin is loaded.

        Override this method to perform initialization when the plugin
        is loaded. The runtime object provides access to project config,
        keychain, and other CumulusCI services.

        Args:
            runtime: The CumulusCI runtime instance
        """
        pass

    def on_unload(self) -> None:
        """Called when the plugin is unloaded.

        Override this method to perform cleanup when the plugin is
        disabled or CumulusCI shuts down.
        """
        pass

    def configure(self, config: Dict[str, Any]) -> None:
        """Apply configuration to the plugin.

        This is called after on_load with the plugin's configuration
        from cumulusci.yml.

        Args:
            config: Plugin configuration dictionary
        """
        self._config = config

    def _set_runtime(self, runtime: "BaseCumulusCI") -> None:
        """Set the runtime instance (called by PluginManager)."""
        self._runtime = runtime

    def _set_enabled(self, enabled: bool) -> None:
        """Set the enabled state (called by PluginManager)."""
        self._enabled = enabled


@dataclass
class PluginInfo:
    """Information about a discovered plugin.

    This is used to store metadata about plugins before they are loaded,
    including their entry point and whether they are enabled.
    """

    name: str
    entry_point: str
    module_name: str
    is_loaded: bool = False
    is_enabled: bool = False
    error: Optional[str] = None
    plugin_instance: Optional[CCIPlugin] = None
    trust_level: TrustLevel = TrustLevel.STANDARD

    @property
    def manifest(self) -> Optional[PluginManifest]:
        """Return the plugin's manifest if loaded."""
        if self.plugin_instance:
            return self.plugin_instance.manifest
        return None
