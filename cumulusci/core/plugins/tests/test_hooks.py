"""Tests for cumulusci.core.plugins.hooks module."""

from cumulusci.core.plugins.hooks import (
    CCIHookSpec,
    HookManager,
    create_plugin_manager,
    get_hook_manager,
    hookimpl,
    reset_hook_manager,
)


class TestHookManager:
    """Tests for HookManager class."""

    def setup_method(self):
        """Reset hook manager before each test."""
        reset_hook_manager()

    def teardown_method(self):
        """Reset hook manager after each test."""
        reset_hook_manager()

    def test_create_hook_manager(self):
        """Test creating a hook manager."""
        manager = HookManager()
        assert manager.hook is not None
        assert manager.get_plugins() == []

    def test_register_plugin(self):
        """Test registering a plugin with hooks."""

        class TestHooks:
            task_complete_called = False

            @hookimpl
            def cci_task_complete(self, task, result):
                self.task_complete_called = True

        manager = HookManager()
        hooks = TestHooks()

        name = manager.register(hooks, name="test-hooks")
        assert name == "test-hooks"
        assert manager.is_registered(name="test-hooks")

    def test_unregister_plugin(self):
        """Test unregistering a plugin."""

        class TestHooks:
            @hookimpl
            def cci_cli_init(self, runtime):
                pass

        manager = HookManager()
        hooks = TestHooks()

        manager.register(hooks, name="test-hooks")
        assert manager.is_registered(name="test-hooks")

        manager.unregister(name="test-hooks")
        assert not manager.is_registered(name="test-hooks")

    def test_call_hook(self):
        """Test calling a hook."""

        class TestHooks:
            init_called = False
            received_runtime = None

            @hookimpl
            def cci_cli_init(self, runtime):
                self.init_called = True
                self.received_runtime = runtime

        manager = HookManager()
        hooks = TestHooks()
        manager.register(hooks)

        mock_runtime = object()
        manager.hook.cci_cli_init(runtime=mock_runtime)

        assert hooks.init_called
        assert hooks.received_runtime is mock_runtime

    def test_multiple_hooks(self):
        """Test multiple plugins responding to same hook."""
        results = []

        class Plugin1:
            @hookimpl
            def cci_flow_start(self, flow, context):
                results.append("plugin1")

        class Plugin2:
            @hookimpl
            def cci_flow_start(self, flow, context):
                results.append("plugin2")

        manager = HookManager()
        manager.register(Plugin1(), name="plugin1")
        manager.register(Plugin2(), name="plugin2")

        manager.hook.cci_flow_start(flow=None, context={})

        assert "plugin1" in results
        assert "plugin2" in results

    def test_list_plugin_names(self):
        """Test listing registered plugin names."""

        class TestHooks:
            @hookimpl
            def cci_cli_init(self, runtime):
                pass

        manager = HookManager()
        manager.register(TestHooks(), name="plugin-a")
        manager.register(TestHooks(), name="plugin-b")

        names = manager.list_plugin_names()
        assert "plugin-a" in names
        assert "plugin-b" in names


class TestGlobalHookManager:
    """Tests for global hook manager functions."""

    def setup_method(self):
        """Reset hook manager before each test."""
        reset_hook_manager()

    def teardown_method(self):
        """Reset hook manager after each test."""
        reset_hook_manager()

    def test_get_hook_manager_returns_singleton(self):
        """Test that get_hook_manager returns the same instance."""
        manager1 = get_hook_manager()
        manager2 = get_hook_manager()
        assert manager1 is manager2

    def test_reset_hook_manager(self):
        """Test resetting the global hook manager."""
        manager1 = get_hook_manager()
        reset_hook_manager()
        manager2 = get_hook_manager()
        assert manager1 is not manager2


class TestHookSpec:
    """Tests for CCIHookSpec class."""

    def test_hookspec_has_required_hooks(self):
        """Test that CCIHookSpec defines all required hooks."""
        spec = CCIHookSpec()

        # Verify all expected hooks exist
        assert hasattr(spec, "cci_cli_init")
        assert hasattr(spec, "cci_flow_start")
        assert hasattr(spec, "cci_flow_complete")
        assert hasattr(spec, "cci_task_start")
        assert hasattr(spec, "cci_task_complete")
        assert hasattr(spec, "cci_org_connect")
        assert hasattr(spec, "cci_service_connect")
        assert hasattr(spec, "cci_task_option_transform")


class TestCreatePluginManager:
    """Tests for create_plugin_manager function."""

    def test_creates_pluggy_manager(self):
        """Test that create_plugin_manager returns a configured pluggy manager."""
        pm = create_plugin_manager()
        assert pm is not None
        assert pm.project_name == "cumulusci"
