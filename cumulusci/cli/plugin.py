"""CLI commands for managing CumulusCI plugins."""

import click
from rich.console import Console
from rich.table import Table

from cumulusci.core.plugins import TrustLevel

from .runtime import pass_runtime


@click.group("plugin", help="Commands for managing CumulusCI plugins")
def plugin():
    pass


@plugin.command(name="list", help="List discovered and enabled plugins")
@click.option("--all", "show_all", is_flag=True, help="Show all discovered plugins")
@click.option("--json", "print_json", is_flag=True, help="Print as JSON")
@pass_runtime(require_project=False, require_keychain=False)
def plugin_list(runtime, show_all, print_json):
    """List installed and enabled plugins."""
    console = Console()

    discovered = runtime.plugin_manager.get_discovered_plugins()

    if print_json:
        import json

        data = {
            "discovered": [
                {
                    "name": info.name,
                    "entry_point": info.entry_point,
                    "is_loaded": info.is_loaded,
                    "is_enabled": info.is_enabled,
                    "error": info.error,
                    "trust_level": info.trust_level.value if info.trust_level else None,
                    "version": info.manifest.version if info.manifest else None,
                }
                for info in discovered.values()
            ]
        }
        console.print(json.dumps(data, indent=2))
        return

    if not discovered:
        console.print("[yellow]No plugins discovered.[/yellow]")
        console.print(
            "\nPlugins are installed as Python packages with "
            "'cumulusci.plugins' entry points."
        )
        return

    table = Table(title="CumulusCI Plugins")
    table.add_column("Name", style="cyan")
    table.add_column("Version")
    table.add_column("Status")
    table.add_column("Trust Level")
    table.add_column("Description")

    for name, info in sorted(discovered.items()):
        if not show_all and not info.is_enabled:
            continue

        version = info.manifest.version if info.manifest else "-"
        description = info.manifest.description[:50] if info.manifest else ""
        if info.manifest and len(info.manifest.description) > 50:
            description += "..."

        if info.error:
            status = f"[red]Error: {info.error[:30]}[/red]"
        elif info.is_loaded:
            status = "[green]Loaded[/green]"
        elif info.is_enabled:
            status = "[yellow]Enabled (not loaded)[/yellow]"
        else:
            status = "[dim]Disabled[/dim]"

        trust = info.trust_level.value if info.trust_level else "standard"

        table.add_row(name, version, status, trust, description)

    console.print(table)

    if not show_all:
        disabled_count = sum(1 for info in discovered.values() if not info.is_enabled)
        if disabled_count:
            console.print(
                f"\n[dim]{disabled_count} disabled plugin(s) not shown. "
                "Use --all to show all.[/dim]"
            )


@plugin.command(name="info", help="Show detailed information about a plugin")
@click.argument("plugin_name")
@click.option("--json", "print_json", is_flag=True, help="Print as JSON")
@pass_runtime(require_project=False, require_keychain=False)
def plugin_info(runtime, plugin_name, print_json):
    """Show detailed information about a specific plugin."""
    console = Console()

    discovered = runtime.plugin_manager.get_discovered_plugins()

    if plugin_name not in discovered:
        console.print(f"[red]Plugin '{plugin_name}' not found.[/red]")
        console.print("\nUse 'cci plugin list --all' to see available plugins.")
        return

    info = discovered[plugin_name]

    if print_json:
        import json

        data = {
            "name": info.name,
            "entry_point": info.entry_point,
            "module_name": info.module_name,
            "is_loaded": info.is_loaded,
            "is_enabled": info.is_enabled,
            "error": info.error,
            "trust_level": info.trust_level.value if info.trust_level else None,
        }
        if info.manifest:
            data["manifest"] = info.manifest.to_dict()
        console.print(json.dumps(data, indent=2))
        return

    console.print(f"\n[bold cyan]Plugin: {plugin_name}[/bold cyan]\n")

    if info.manifest:
        manifest = info.manifest
        console.print(f"  [bold]Version:[/bold] {manifest.version}")
        console.print(f"  [bold]Description:[/bold] {manifest.description}")
        if manifest.author:
            console.print(f"  [bold]Author:[/bold] {manifest.author}")
        if manifest.homepage:
            console.print(f"  [bold]Homepage:[/bold] {manifest.homepage}")
        console.print(
            f"  [bold]Required Trust Level:[/bold] {manifest.required_trust_level.value}"
        )
        if manifest.min_cci_version:
            console.print(f"  [bold]Min CCI Version:[/bold] {manifest.min_cci_version}")

        console.print(f"\n  [bold]Entry Point:[/bold] {info.entry_point}")

        if manifest.tasks:
            console.print(f"\n  [bold]Tasks ({len(manifest.tasks)}):[/bold]")
            for task_name in sorted(manifest.tasks.keys()):
                console.print(f"    - {task_name}")

        if manifest.flows:
            console.print(f"\n  [bold]Flows ({len(manifest.flows)}):[/bold]")
            for flow_name in sorted(manifest.flows.keys()):
                console.print(f"    - {flow_name}")

        if manifest.services:
            console.print(f"\n  [bold]Services ({len(manifest.services)}):[/bold]")
            for service_name in sorted(manifest.services.keys()):
                console.print(f"    - {service_name}")

        if manifest.robot_libraries:
            console.print(
                f"\n  [bold]Robot Libraries ({len(manifest.robot_libraries)}):[/bold]"
            )
            for lib_name in sorted(manifest.robot_libraries.keys()):
                console.print(f"    - {lib_name}")

        if manifest.cli_commands:
            console.print(
                f"\n  [bold]CLI Commands ({len(manifest.cli_commands)}):[/bold]"
            )
            for cmd in manifest.cli_commands:
                console.print(f"    - {cmd}")
    else:
        console.print(f"  [bold]Entry Point:[/bold] {info.entry_point}")
        console.print(f"  [bold]Module:[/bold] {info.module_name}")

    console.print("\n  [bold]Status:[/bold]")
    if info.error:
        console.print(f"    [red]Error: {info.error}[/red]")
    elif info.is_loaded:
        console.print("    [green]Loaded and active[/green]")
    elif info.is_enabled:
        console.print("    [yellow]Enabled but not loaded[/yellow]")
    else:
        console.print("    [dim]Disabled[/dim]")

    console.print(
        f"\n  [bold]Configured Trust Level:[/bold] "
        f"{info.trust_level.value if info.trust_level else 'standard'}"
    )


@plugin.command(name="enable", help="Enable a plugin")
@click.argument("plugin_name")
@click.option(
    "--trust-level",
    type=click.Choice(["untrusted", "standard", "trusted"]),
    default="standard",
    help="Trust level to grant the plugin",
)
@pass_runtime(require_project=True, require_keychain=False)
def plugin_enable(runtime, plugin_name, trust_level):
    """Enable a plugin for the current project.

    This modifies the project's cumulusci.yml to enable the plugin.
    """
    console = Console()

    discovered = runtime.plugin_manager.get_discovered_plugins()

    if plugin_name not in discovered:
        console.print(f"[red]Plugin '{plugin_name}' not found.[/red]")
        console.print("\nMake sure the plugin package is installed:")
        console.print(f"  pip install {plugin_name}")
        return

    # Check if plugin is already enabled
    plugin_configs = runtime.project_config.lookup("plugins") or {}
    if plugin_name in plugin_configs and plugin_configs[plugin_name].get(
        "enabled", True
    ):
        console.print(f"[yellow]Plugin '{plugin_name}' is already enabled.[/yellow]")
        return

    console.print(
        f"\nTo enable plugin '{plugin_name}', add the following to your cumulusci.yml:\n"
    )
    console.print("[cyan]plugins:[/cyan]")
    console.print(f"[cyan]  {plugin_name}:[/cyan]")
    console.print("[cyan]    enabled: true[/cyan]")
    console.print(f"[cyan]    trust_level: {trust_level}[/cyan]")

    console.print(
        "\n[green]After updating cumulusci.yml, run 'cci plugin list' to verify.[/green]"
    )


@plugin.command(name="disable", help="Disable a plugin")
@click.argument("plugin_name")
@pass_runtime(require_project=True, require_keychain=False)
def plugin_disable(runtime, plugin_name):
    """Disable a plugin for the current project.

    This provides guidance on modifying cumulusci.yml to disable the plugin.
    """
    console = Console()

    discovered = runtime.plugin_manager.get_discovered_plugins()

    if plugin_name not in discovered:
        console.print(f"[yellow]Plugin '{plugin_name}' is not installed.[/yellow]")
        return

    console.print(f"\nTo disable plugin '{plugin_name}', update your cumulusci.yml:\n")
    console.print("[cyan]plugins:[/cyan]")
    console.print(f"[cyan]  {plugin_name}:[/cyan]")
    console.print("[cyan]    enabled: false[/cyan]")

    console.print(
        "\n[green]After updating cumulusci.yml, run 'cci plugin list' to verify.[/green]"
    )


@plugin.command(name="trust", help="Set trust level for a plugin")
@click.argument("plugin_name")
@click.option(
    "--level",
    type=click.Choice(["untrusted", "standard", "trusted"]),
    required=True,
    help="Trust level to grant the plugin",
)
@pass_runtime(require_project=True, require_keychain=False)
def plugin_trust(runtime, plugin_name, level):
    """Set the trust level for a plugin.

    Trust levels control what a plugin can do:
    - untrusted: Read-only access to configuration
    - standard: Can register tasks, flows, and services (default)
    - trusted: Full access including CLI extension and credential access
    """
    console = Console()

    discovered = runtime.plugin_manager.get_discovered_plugins()

    if plugin_name not in discovered:
        console.print(f"[red]Plugin '{plugin_name}' not found.[/red]")
        return

    info = discovered[plugin_name]
    if info.manifest:
        required = info.manifest.required_trust_level
        new_level = TrustLevel(level)
        if required > new_level:
            console.print(
                f"[yellow]Warning: Plugin requires '{required.value}' trust level, "
                f"but you're setting '{level}'.[/yellow]"
            )
            console.print("The plugin may not function correctly with reduced trust.")

    console.print(
        f"\nTo set trust level for plugin '{plugin_name}', update your cumulusci.yml:\n"
    )
    console.print("[cyan]plugins:[/cyan]")
    console.print(f"[cyan]  {plugin_name}:[/cyan]")
    console.print("[cyan]    enabled: true[/cyan]")
    console.print(f"[cyan]    trust_level: {level}[/cyan]")

    console.print(
        "\n[green]After updating cumulusci.yml, run 'cci plugin list' to verify.[/green]"
    )


@plugin.command(name="tasks", help="List tasks provided by plugins")
@pass_runtime(require_project=False, require_keychain=False)
def plugin_tasks(runtime):
    """List all tasks provided by loaded plugins."""
    console = Console()

    all_tasks = runtime.plugin_manager.get_all_tasks()

    if not all_tasks:
        console.print("[yellow]No plugin tasks available.[/yellow]")
        return

    table = Table(title="Plugin Tasks")
    table.add_column("Task Name", style="cyan")
    table.add_column("Class Path")
    table.add_column("Plugin")

    loaded_plugins = runtime.plugin_manager.get_loaded_plugins()

    for task_name, class_path in sorted(all_tasks.items()):
        # Find which plugin provides this task
        plugin_name = "-"
        for name, plugin in loaded_plugins.items():
            if task_name in plugin.manifest.tasks:
                plugin_name = name
                break

        table.add_row(task_name, class_path, plugin_name)

    console.print(table)
    console.print(
        "\n[dim]Use these tasks with: cci task run @plugin_name:task_name[/dim]"
    )


@plugin.command(name="flows", help="List flows provided by plugins")
@pass_runtime(require_project=False, require_keychain=False)
def plugin_flows(runtime):
    """List all flows provided by loaded plugins."""
    console = Console()

    all_flows = runtime.plugin_manager.get_all_flows()

    if not all_flows:
        console.print("[yellow]No plugin flows available.[/yellow]")
        return

    table = Table(title="Plugin Flows")
    table.add_column("Flow Name", style="cyan")
    table.add_column("Plugin")
    table.add_column("Description")

    loaded_plugins = runtime.plugin_manager.get_loaded_plugins()

    for flow_name, flow_config in sorted(all_flows.items()):
        # Find which plugin provides this flow
        plugin_name = "-"
        for name, plugin in loaded_plugins.items():
            if flow_name in plugin.manifest.flows:
                plugin_name = name
                break

        description = flow_config.get("description", "")[:50]
        if len(flow_config.get("description", "")) > 50:
            description += "..."

        table.add_row(flow_name, plugin_name, description)

    console.print(table)
    console.print(
        "\n[dim]Use these flows with: cci flow run @plugin_name:flow_name[/dim]"
    )
