"""Tests for cumulusci.core.plugins.base module."""

import pytest

from cumulusci.core.plugins.base import (
    CCIPlugin,
    PluginInfo,
    PluginManifest,
    TrustLevel,
)


class TestTrustLevel:
    """Tests for TrustLevel enum."""

    def test_values(self):
        """Test trust level values."""
        assert TrustLevel.UNTRUSTED.value == "untrusted"
        assert TrustLevel.STANDARD.value == "standard"
        assert TrustLevel.TRUSTED.value == "trusted"

    def test_comparison_ge(self):
        """Test >= comparison."""
        assert TrustLevel.TRUSTED >= TrustLevel.STANDARD
        assert TrustLevel.STANDARD >= TrustLevel.UNTRUSTED
        assert TrustLevel.STANDARD >= TrustLevel.STANDARD

    def test_comparison_gt(self):
        """Test > comparison."""
        assert TrustLevel.TRUSTED > TrustLevel.STANDARD
        assert TrustLevel.STANDARD > TrustLevel.UNTRUSTED
        assert not TrustLevel.STANDARD > TrustLevel.STANDARD

    def test_comparison_le(self):
        """Test <= comparison."""
        assert TrustLevel.UNTRUSTED <= TrustLevel.STANDARD
        assert TrustLevel.STANDARD <= TrustLevel.TRUSTED
        assert TrustLevel.STANDARD <= TrustLevel.STANDARD

    def test_comparison_lt(self):
        """Test < comparison."""
        assert TrustLevel.UNTRUSTED < TrustLevel.STANDARD
        assert TrustLevel.STANDARD < TrustLevel.TRUSTED
        assert not TrustLevel.STANDARD < TrustLevel.STANDARD


class TestPluginManifest:
    """Tests for PluginManifest dataclass."""

    def test_minimal_manifest(self):
        """Test creating manifest with minimal required fields."""
        manifest = PluginManifest(name="test-plugin", version="1.0.0")
        assert manifest.name == "test-plugin"
        assert manifest.version == "1.0.0"
        assert manifest.description == ""
        assert manifest.tasks == {}
        assert manifest.flows == {}
        assert manifest.services == {}
        assert manifest.required_trust_level == TrustLevel.STANDARD

    def test_full_manifest(self):
        """Test creating manifest with all fields."""
        manifest = PluginManifest(
            name="full-plugin",
            version="2.0.0",
            description="A full test plugin",
            tasks={"task1": "plugin.tasks.Task1"},
            flows={"flow1": {"steps": {}}},
            services={"service1": {"description": "A service"}},
            cli_commands=["plugin.cli:cli_group"],
            robot_libraries={"MyLib": "plugin.robot.MyLib"},
            required_trust_level=TrustLevel.TRUSTED,
            min_cci_version="4.0.0",
            max_cci_version="5.0.0",
            homepage="https://example.com",
            author="Test Author",
        )
        assert manifest.tasks == {"task1": "plugin.tasks.Task1"}
        assert manifest.flows == {"flow1": {"steps": {}}}
        assert manifest.required_trust_level == TrustLevel.TRUSTED
        assert manifest.author == "Test Author"

    def test_manifest_validation_missing_name(self):
        """Test that manifest validation fails without name."""
        with pytest.raises(ValueError, match="Plugin name is required"):
            PluginManifest(name="", version="1.0.0")

    def test_manifest_validation_missing_version(self):
        """Test that manifest validation fails without version."""
        with pytest.raises(ValueError, match="Plugin version is required"):
            PluginManifest(name="test", version="")

    def test_to_dict(self):
        """Test converting manifest to dictionary."""
        manifest = PluginManifest(
            name="test-plugin",
            version="1.0.0",
            description="Test description",
        )
        data = manifest.to_dict()
        assert data["name"] == "test-plugin"
        assert data["version"] == "1.0.0"
        assert data["description"] == "Test description"
        assert data["required_trust_level"] == "standard"

    def test_from_dict(self):
        """Test creating manifest from dictionary."""
        data = {
            "name": "from-dict-plugin",
            "version": "3.0.0",
            "description": "Created from dict",
            "required_trust_level": "trusted",
        }
        manifest = PluginManifest.from_dict(data)
        assert manifest.name == "from-dict-plugin"
        assert manifest.version == "3.0.0"
        assert manifest.required_trust_level == TrustLevel.TRUSTED


class TestCCIPlugin:
    """Tests for CCIPlugin abstract base class."""

    def test_plugin_requires_manifest(self):
        """Test that plugin subclass must implement manifest property."""

        class IncompletePlugin(CCIPlugin):
            pass

        with pytest.raises(TypeError):
            IncompletePlugin()

    def test_plugin_with_manifest(self):
        """Test creating a valid plugin subclass."""

        class TestPlugin(CCIPlugin):
            @property
            def manifest(self) -> PluginManifest:
                return PluginManifest(
                    name="test-plugin",
                    version="1.0.0",
                )

        plugin = TestPlugin()
        assert plugin.name == "test-plugin"
        assert plugin.version == "1.0.0"
        assert plugin.enabled is False
        assert plugin.config == {}

    def test_plugin_lifecycle(self):
        """Test plugin lifecycle methods."""

        class LifecyclePlugin(CCIPlugin):
            on_load_called = False
            on_unload_called = False

            @property
            def manifest(self) -> PluginManifest:
                return PluginManifest(name="lifecycle", version="1.0.0")

            def on_load(self, runtime):
                self.on_load_called = True
                self.loaded_runtime = runtime

            def on_unload(self):
                self.on_unload_called = True

        plugin = LifecyclePlugin()
        mock_runtime = object()

        plugin.on_load(mock_runtime)
        assert plugin.on_load_called
        assert plugin.loaded_runtime is mock_runtime

        plugin.on_unload()
        assert plugin.on_unload_called

    def test_plugin_configure(self):
        """Test plugin configuration."""

        class ConfigPlugin(CCIPlugin):
            @property
            def manifest(self) -> PluginManifest:
                return PluginManifest(name="config-plugin", version="1.0.0")

        plugin = ConfigPlugin()
        config = {"key1": "value1", "key2": 42}
        plugin.configure(config)
        assert plugin.config == config


class TestPluginInfo:
    """Tests for PluginInfo dataclass."""

    def test_plugin_info_defaults(self):
        """Test PluginInfo with default values."""
        info = PluginInfo(
            name="test",
            entry_point="test.plugin:Plugin",
            module_name="test.plugin",
        )
        assert info.name == "test"
        assert info.is_loaded is False
        assert info.is_enabled is False
        assert info.error is None
        assert info.plugin_instance is None
        assert info.trust_level == TrustLevel.STANDARD

    def test_plugin_info_manifest_property(self):
        """Test that manifest property returns plugin's manifest."""

        class TestPlugin(CCIPlugin):
            @property
            def manifest(self) -> PluginManifest:
                return PluginManifest(name="test", version="1.0.0")

        plugin = TestPlugin()
        info = PluginInfo(
            name="test",
            entry_point="test:Plugin",
            module_name="test",
            plugin_instance=plugin,
        )
        assert info.manifest is not None
        assert info.manifest.name == "test"

    def test_plugin_info_manifest_none_when_not_loaded(self):
        """Test that manifest is None when plugin is not loaded."""
        info = PluginInfo(
            name="test",
            entry_point="test:Plugin",
            module_name="test",
        )
        assert info.manifest is None
