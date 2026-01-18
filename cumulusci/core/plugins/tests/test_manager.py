"""Tests for cumulusci.core.plugins.manager module."""

import pytest

from cumulusci.core.plugins.base import CCIPlugin, PluginManifest, TrustLevel
from cumulusci.core.plugins.exceptions import PluginNotFoundError
from cumulusci.core.plugins.hooks import reset_hook_manager
from cumulusci.core.plugins.manager import (
    PluginManager,
    get_plugin_manager,
    reset_plugin_manager,
)


class SamplePlugin(CCIPlugin):
    """Sample plugin for testing."""

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="sample-plugin",
            version="1.0.0",
            description="A sample test plugin",
            tasks={"sample_task": "sample.tasks.SampleTask"},
            flows={"sample_flow": {"steps": {}}},
            services={"sample_service": {"description": "Sample service"}},
            robot_libraries={"SampleLib": "sample.robot.SampleLib"},
        )


class TrustedPlugin(CCIPlugin):
    """Plugin requiring trusted access."""

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="trusted-plugin",
            version="1.0.0",
            required_trust_level=TrustLevel.TRUSTED,
            cli_commands=["trusted.cli:cli_group"],
        )


class TestPluginManager:
    """Tests for PluginManager class."""

    def setup_method(self):
        """Reset managers before each test."""
        reset_plugin_manager()
        reset_hook_manager()

    def teardown_method(self):
        """Reset managers after each test."""
        reset_plugin_manager()
        reset_hook_manager()

    def test_create_manager(self):
        """Test creating a plugin manager."""
        manager = PluginManager()
        assert manager.runtime is None
        assert manager.get_discovered_plugins() == {}
        assert manager.get_loaded_plugins() == {}

    def test_is_plugin_enabled_default(self):
        """Test plugin enabled check with default behavior."""
        manager = PluginManager()

        # Plugins starting with cci- are auto-enabled
        assert manager.is_plugin_enabled("cci-test") is True
        # Other plugins are not auto-enabled
        assert manager.is_plugin_enabled("my-plugin") is False

    def test_is_plugin_enabled_with_config(self):
        """Test plugin enabled check with configuration."""
        manager = PluginManager()
        manager.load_plugin_configs(
            {
                "my-plugin": {"enabled": True},
                "disabled-plugin": {"enabled": False},
            }
        )

        assert manager.is_plugin_enabled("my-plugin") is True
        assert manager.is_plugin_enabled("disabled-plugin") is False

    def test_get_plugin_trust_level_default(self):
        """Test default trust level is STANDARD."""
        manager = PluginManager()
        assert manager.get_plugin_trust_level("any-plugin") == TrustLevel.STANDARD

    def test_get_plugin_trust_level_from_config(self):
        """Test trust level from configuration."""
        manager = PluginManager()
        manager.load_plugin_configs(
            {
                "trusted-plugin": {"trust_level": "trusted"},
                "untrusted-plugin": {"trust_level": "untrusted"},
            }
        )

        assert manager.get_plugin_trust_level("trusted-plugin") == TrustLevel.TRUSTED
        assert (
            manager.get_plugin_trust_level("untrusted-plugin") == TrustLevel.UNTRUSTED
        )

    def test_get_plugin_config(self):
        """Test getting plugin configuration."""
        manager = PluginManager()
        manager.load_plugin_configs(
            {
                "my-plugin": {
                    "enabled": True,
                    "config": {"key1": "value1", "key2": 42},
                },
            }
        )

        config = manager.get_plugin_config("my-plugin")
        assert config == {"key1": "value1", "key2": 42}

    def test_get_plugin_config_empty(self):
        """Test getting config for unconfigured plugin."""
        manager = PluginManager()
        assert manager.get_plugin_config("unknown-plugin") == {}

    def test_get_all_tasks_empty(self):
        """Test getting tasks when no plugins are loaded."""
        manager = PluginManager()
        assert manager.get_all_tasks() == {}

    def test_get_all_flows_empty(self):
        """Test getting flows when no plugins are loaded."""
        manager = PluginManager()
        assert manager.get_all_flows() == {}

    def test_get_all_services_empty(self):
        """Test getting services when no plugins are loaded."""
        manager = PluginManager()
        assert manager.get_all_services() == {}

    def test_get_all_robot_libraries_empty(self):
        """Test getting robot libraries when no plugins are loaded."""
        manager = PluginManager()
        assert manager.get_all_robot_libraries() == {}

    def test_get_all_cli_commands_empty(self):
        """Test getting CLI commands when no plugins are loaded."""
        manager = PluginManager()
        assert manager.get_all_cli_commands() == []

    def test_unload_plugin_not_found(self):
        """Test unloading a plugin that isn't loaded raises error."""
        manager = PluginManager()
        with pytest.raises(PluginNotFoundError):
            manager.unload_plugin("not-loaded")


class TestGlobalPluginManager:
    """Tests for global plugin manager functions."""

    def setup_method(self):
        """Reset plugin manager before each test."""
        reset_plugin_manager()

    def teardown_method(self):
        """Reset plugin manager after each test."""
        reset_plugin_manager()

    def test_get_plugin_manager_returns_singleton(self):
        """Test that get_plugin_manager returns the same instance."""
        manager1 = get_plugin_manager()
        manager2 = get_plugin_manager()
        assert manager1 is manager2

    def test_reset_plugin_manager(self):
        """Test resetting the global plugin manager."""
        manager1 = get_plugin_manager()
        reset_plugin_manager()
        manager2 = get_plugin_manager()
        assert manager1 is not manager2
