# CumulusCI Plugin Development Guide

This guide explains how to create plugins for CumulusCI that extend its functionality with custom tasks, flows, services, CLI commands, and Robot Framework libraries.

## Overview

The CumulusCI plugin system allows third-party packages to extend CumulusCI through:

-   **Custom Tasks**: Add new automation tasks
-   **Custom Flows**: Define reusable flow configurations
-   **Custom Services**: Add new service types for credentials
-   **CLI Commands**: Extend the `cci` command-line interface
-   **Robot Libraries**: Add Robot Framework keywords
-   **Hooks**: React to CumulusCI events (task completion, flow start, etc.)

```{note}
**Plugins vs. Sources**: Plugins are Python packages installed via pip that can extend CumulusCI with tasks, flows, services, CLI commands, Robot libraries, and hooks. They use the `@plugin:task_name` syntax. In contrast, [sources](tasks-and-flows-from-a-different-project) reference tasks and flows from other CumulusCI projects on GitHub using the `namespace:task_name` syntax. Use plugins when you need capabilities beyond tasks/flows or want to publish reusable extensions. See [Sources vs. Plugins](config.md#sources-vs-plugins) for a detailed comparison.
```

## Quick Start

### 1. Create Your Plugin Package

Create a new Python package with the following structure:

```
my-cci-plugin/
├── pyproject.toml
├── my_cci_plugin/
│   ├── __init__.py      # Plugin class
│   ├── tasks.py         # Custom tasks
│   ├── services.py      # Custom services (optional)
│   └── cli.py           # CLI commands (optional)
```

### 2. Define Your Plugin Class

```python
# my_cci_plugin/__init__.py

from cumulusci.core.plugins import CCIPlugin, PluginManifest, TrustLevel

class MyCCIPlugin(CCIPlugin):
    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="my-cci-plugin",
            version="1.0.0",
            description="My custom CumulusCI plugin",
            author="Your Name",
            homepage="https://github.com/yourname/my-cci-plugin",
            tasks={
                "my_task": "my_cci_plugin.tasks.MyTask",
            },
            required_trust_level=TrustLevel.STANDARD,
        )

    def on_load(self, runtime):
        """Called when the plugin is loaded."""
        print(f"My plugin loaded!")

    def on_unload(self):
        """Called when the plugin is unloaded."""
        print("My plugin unloaded!")
```

### 3. Register the Entry Point

In your `pyproject.toml`:

```toml
[project]
name = "my-cci-plugin"
version = "1.0.0"
dependencies = ["clariti-cumulusci>=4.6.0"]

[project.entry-points."cumulusci.plugins"]
my-cci-plugin = "my_cci_plugin:MyCCIPlugin"
```

### 4. Install and Use

```bash
pip install my-cci-plugin

# List available plugins
cci plugin list

# Run your plugin task
cci task run @my-cci-plugin:my_task
```

## Plugin Manifest

The `PluginManifest` describes your plugin's capabilities:

```python
PluginManifest(
    # Required
    name="my-plugin",              # Unique identifier
    version="1.0.0",               # Semantic version

    # Optional metadata
    description="What my plugin does",
    author="Your Name",
    homepage="https://...",

    # Extensions
    tasks={
        "task_name": "module.path.TaskClass",
    },
    flows={
        "flow_name": {
            "description": "Flow description",
            "steps": {...},
        },
    },
    services={
        "service_type": {
            "description": "Service description",
            "attributes": {...},
        },
    },
    cli_commands=["module.cli:cli_group"],  # Requires TRUSTED trust level
    robot_libraries={
        "LibraryName": "module.robot.Library",
    },

    # Trust and compatibility
    required_trust_level=TrustLevel.STANDARD,
    min_cci_version="4.6.0",
    max_cci_version=None,  # No upper limit
)
```

## Creating Custom Tasks

Tasks are the most common plugin extension:

```python
# my_cci_plugin/tasks.py

from cumulusci.core.tasks import BaseTask

class MyTask(BaseTask):
    task_docs = """
    Description of what my task does.
    """

    task_options = {
        "my_option": {
            "description": "An option for my task",
            "required": True,
        },
        "optional_option": {
            "description": "An optional option",
            "required": False,
            "default": "default_value",
        },
    }

    def _run_task(self):
        self.logger.info(f"Running with option: {self.options['my_option']}")
        # Your task logic here
        return {"result": "success"}
```

## Creating Custom Flows

Define flows in your manifest:

```python
flows={
    "my_flow": {
        "description": "My custom deployment flow",
        "steps": {
            "1": {"task": "my_task", "options": {"my_option": "value"}},
            "2": {"task": "deploy"},
            "3": {"flow": "config_dev"},
        },
    },
},
```

## Creating Custom Services

Services store credentials and configuration:

```python
# In manifest
services={
    "my_service": {
        "description": "Connection to My Service",
        "attributes": {
            "api_key": {
                "description": "API Key",
                "required": True,
                "sensitive": True,
            },
            "endpoint": {
                "description": "API Endpoint",
                "required": False,
                "default": "https://api.myservice.com",
            },
        },
    },
},
```

Access the service in your tasks:

```python
class MyServiceTask(BaseTask):
    def _run_task(self):
        service = self.project_config.keychain.get_service("my_service")
        api_key = service.config["api_key"]
        # Use the service...
```

## Using Hooks

Hooks let your plugin respond to CumulusCI events:

```python
from cumulusci.core.plugins import CCIPlugin, PluginManifest
from cumulusci.core.plugins.hooks import hookimpl

class MyPlugin(CCIPlugin):
    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(name="my-plugin", version="1.0.0")

    @hookimpl
    def cci_task_complete(self, task, result):
        """Called after any task completes."""
        if result.get("success"):
            print(f"Task completed successfully!")

    @hookimpl
    def cci_flow_start(self, flow, context):
        """Called before a flow starts."""
        print(f"Starting flow: {context.get('flow_name')}")

    @hookimpl
    def cci_org_connect(self, org_config, context):
        """Called when an org is connected."""
        print(f"Connected org: {context.get('org_name')}")
```

### Available Hooks

| Hook                                                | Description             |
| --------------------------------------------------- | ----------------------- |
| `cci_cli_init(runtime)`                             | CLI runtime initialized |
| `cci_flow_start(flow, context)`                     | Before flow execution   |
| `cci_flow_complete(flow, result)`                   | After flow completion   |
| `cci_task_start(task, context)`                     | Before task execution   |
| `cci_task_complete(task, result)`                   | After task completion   |
| `cci_org_connect(org_config, context)`              | Org connected           |
| `cci_service_connect(service_type, service_config)` | Service connected       |
| `cci_task_option_transform(task_name, options)`     | Transform task options  |

## Trust Levels

Plugins declare their required trust level:

| Level       | Capabilities                                              |
| ----------- | --------------------------------------------------------- |
| `UNTRUSTED` | Read-only access to configuration                         |
| `STANDARD`  | Can register tasks, flows, and services (default)         |
| `TRUSTED`   | Full access including CLI extension and credential access |

Users configure trust in `cumulusci.yml`:

```yaml
plugins:
    my-plugin:
        enabled: true
        trust_level: trusted
        config:
            custom_option: value
```

## CLI Commands (Trusted Only)

Plugins with `TRUSTED` trust level can add CLI commands:

```python
# my_cci_plugin/cli.py
import click

@click.group("my-plugin")
def cli_group():
    """My plugin commands."""
    pass

@cli_group.command()
def status():
    """Show plugin status."""
    click.echo("Plugin is working!")
```

Register in manifest:

```python
cli_commands=["my_cci_plugin.cli:cli_group"],
required_trust_level=TrustLevel.TRUSTED,
```

## Robot Framework Libraries

Add Robot Framework keywords:

```python
# my_cci_plugin/robot.py

class MyRobotLibrary:
    """Robot Framework library from my plugin."""

    def my_keyword(self, arg1):
        """A custom keyword.

        Arguments:
        - arg1: First argument
        """
        return f"Result: {arg1}"
```

Register in manifest:

```python
robot_libraries={
    "MyRobotLibrary": "my_cci_plugin.robot.MyRobotLibrary",
},
```

Use in Robot tests:

```robot
*** Settings ***
Library    cumulusci.robotframework.CumulusCI    ${ORG}

*** Test Cases ***
Use Plugin Library
    Import Plugin Library    MyRobotLibrary
    ${result}=    My Keyword    test_value
    Should Be Equal    ${result}    Result: test_value
```

## Configuration

Users enable and configure plugins in `cumulusci.yml`:

```yaml
plugins:
    my-plugin:
        enabled: true
        trust_level: standard
        config:
            api_endpoint: https://api.example.com
            feature_flag: true
```

Access configuration in your plugin:

```python
class MyPlugin(CCIPlugin):
    def on_load(self, runtime):
        endpoint = self.config.get("api_endpoint")
        if self.config.get("feature_flag"):
            # Enable feature...
```

## Best Practices

1. **Use semantic versioning** for your plugin version
2. **Document your tasks** using `task_docs` and `task_options`
3. **Handle errors gracefully** in hooks - don't break CumulusCI operations
4. **Declare minimum CCI version** if using features from specific versions
5. **Use STANDARD trust level** unless you need CLI or credential access
6. **Test your plugin** before publishing

## CLI Commands

Users interact with plugins via the `cci plugin` commands:

```bash
cci plugin list              # List installed plugins
cci plugin info <name>       # Show plugin details
cci plugin enable <name>     # Enable a plugin
cci plugin disable <name>    # Disable a plugin
cci plugin trust <name> --level trusted
cci plugin tasks             # List tasks from plugins
cci plugin flows             # List flows from plugins
```

## Publishing Your Plugin

1. Ensure your plugin follows the naming convention `cci-*` for auto-discovery
2. Publish to PyPI: `pip install build && python -m build && twine upload dist/*`
3. Users install with: `pip install your-cci-plugin`

## Example Plugins

See these example plugins for reference:

-   `cci-slack` - Slack notifications
-   `cci-jira` - JIRA integration

## Troubleshooting

### Plugin not discovered

-   Ensure the entry point is correctly defined in `pyproject.toml`
-   Run `cci plugin list --all` to see all discovered plugins

### Trust level error

-   Your plugin requires a higher trust level than configured
-   Update `cumulusci.yml` to grant the required trust level

### Hook not called

-   Ensure the `@hookimpl` decorator is applied
-   Check that your plugin is loaded (`cci plugin list`)
