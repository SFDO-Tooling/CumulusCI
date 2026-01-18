#!/usr/bin/env python3
"""
Run GitHub Actions workflows locally using 'act'.

This script provides a convenient way to test GitHub Actions workflows
locally before pushing to GitHub.

Requirements:
    - act: https://github.com/nektos/act
    - Docker: Required by act to run containers

Installation:
    brew install act  # macOS
    # or see https://github.com/nektos/act#installation

Usage:
    python scripts/run_workflow.py feature_test
    python scripts/run_workflow.py --list
    python scripts/run_workflow.py feature_test --dry-run
    python scripts/run_workflow.py feature_test --job lint
    python scripts/run_workflow.py feature_test --event push
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Default configuration
DEFAULTS = {
    "workflow_dir": ".github/workflows",
    "var_file": ".vars",
    "secret_file": ".secrets",
    "container_arch": "linux/amd64",
    "platform": "ubuntu-latest=catthehacker/ubuntu:act-latest",
    "event": "pull_request",  # Default event - most workflows trigger on this
}

# Common GitHub Actions events
VALID_EVENTS = [
    "push",
    "pull_request",
    "pull_request_target",
    "workflow_dispatch",
    "schedule",
    "release",
    "issues",
    "issue_comment",
    "workflow_call",
]


def find_act() -> str:
    """Find the act binary."""
    act_path = os.environ.get("ACT", "act")
    if shutil.which(act_path):
        return act_path

    # Try common locations
    common_paths = [
        "/usr/local/bin/act",
        "/opt/homebrew/bin/act",
        os.path.expanduser("~/.local/bin/act"),
    ]
    for path in common_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    return "act"


def list_workflows(workflow_dir: str) -> list[Path]:
    """List all workflow files in the workflow directory."""
    workflow_path = Path(workflow_dir)
    if not workflow_path.exists():
        return []

    workflows = []
    for ext in ("*.yml", "*.yaml"):
        workflows.extend(workflow_path.glob(ext))

    return sorted(workflows, key=lambda p: p.name)


def resolve_workflow(name: str, workflow_dir: str) -> Path | None:
    """Resolve a workflow name to a file path."""
    workflow_path = Path(workflow_dir)

    # Direct path
    if Path(name).exists():
        return Path(name)

    # Try with directory prefix
    candidates = [
        workflow_path / name,
        workflow_path / f"{name}.yml",
        workflow_path / f"{name}.yaml",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    # Try with test- prefix if not already present
    if not name.startswith("test-"):
        prefixed = f"test-{name}"
        for ext in ("", ".yml", ".yaml"):
            candidate = workflow_path / f"{prefixed}{ext}"
            if candidate.exists():
                print(f"Resolved '{name}' to '{prefixed}'", file=sys.stderr)
                return candidate

    return None


def build_command(
    args: argparse.Namespace,
    workflow_path: Path,
    extra_args: list[str],
) -> list[str]:
    """Build the act command."""
    # Start with act and the event type (positional argument for act)
    cmd = [args.act_binary, args.event, "-W", str(workflow_path)]

    # Add var file if exists
    var_file = Path(args.var_file)
    if var_file.exists() and not args.no_var_file:
        cmd.extend(["--var-file", str(var_file)])
    elif not var_file.exists() and args.var_file != DEFAULTS["var_file"]:
        print(f"Warning: var file '{args.var_file}' not found", file=sys.stderr)

    # Add secret file if exists
    secret_file = Path(args.secret_file)
    if secret_file.exists() and not args.no_secret_file:
        cmd.extend(["--secret-file", str(secret_file)])
    elif not secret_file.exists() and args.secret_file != DEFAULTS["secret_file"]:
        print(f"Warning: secret file '{args.secret_file}' not found", file=sys.stderr)

    # Container architecture
    if args.container_arch:
        cmd.extend(["--container-architecture", args.container_arch])

    # Platform mapping
    if args.platform and not args.no_platform:
        cmd.extend(["-P", args.platform])

    # Matrix filters
    for matrix_filter in args.matrix:
        cmd.extend(["--matrix", matrix_filter])

    # Specific job
    if args.job:
        cmd.extend(["-j", args.job])

    # Verbose mode
    if args.verbose:
        cmd.append("-v")

    # Extra arguments passed through
    cmd.extend(extra_args)

    return cmd


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run GitHub Actions workflows locally using act",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  %(prog)s feature_test              Run the feature_test workflow (event: pull_request)
  %(prog)s --list                    List available workflows
  %(prog)s feature_test --job lint   Run only the 'lint' job
  %(prog)s feature_test --event push Run with 'push' event instead
  %(prog)s feature_test --dry-run    Show command without running

Default event: {DEFAULTS['event']}
  Most workflows use 'pull_request' or 'push' triggers.
  Jobs with conditions like 'if: github.event_name == pull_request'
  will only run when the matching event is specified.

Valid events: {', '.join(VALID_EVENTS)}

Environment variables:
  ACT              Path to act binary
  ACT_EVENT        Default event type (default: {DEFAULTS['event']})
  WORKFLOW_DIR     Workflow directory (default: {DEFAULTS['workflow_dir']})
  VAR_FILE         Path to variables file (default: {DEFAULTS['var_file']})
  SECRET_FILE      Path to secrets file (default: {DEFAULTS['secret_file']})
  CONTAINER_ARCH   Container architecture (default: {DEFAULTS['container_arch']})
  PLATFORM         Runner platform mapping
""",
    )

    parser.add_argument(
        "workflow",
        nargs="?",
        help="Workflow name or path to run",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available workflows",
    )
    parser.add_argument(
        "--event",
        "-e",
        default=os.environ.get("ACT_EVENT", DEFAULTS["event"]),
        help=f"GitHub event type to simulate (default: {DEFAULTS['event']})",
    )
    parser.add_argument(
        "--workflow-dir",
        default=os.environ.get("WORKFLOW_DIR", DEFAULTS["workflow_dir"]),
        help=f"Workflow directory (default: {DEFAULTS['workflow_dir']})",
    )
    parser.add_argument(
        "--var-file",
        default=os.environ.get("VAR_FILE", DEFAULTS["var_file"]),
        help=f"Path to variables file (default: {DEFAULTS['var_file']})",
    )
    parser.add_argument(
        "--secret-file",
        default=os.environ.get("SECRET_FILE", DEFAULTS["secret_file"]),
        help=f"Path to secrets file (default: {DEFAULTS['secret_file']})",
    )
    parser.add_argument(
        "--no-var-file",
        action="store_true",
        help="Skip adding var file",
    )
    parser.add_argument(
        "--no-secret-file",
        action="store_true",
        help="Skip adding secret file",
    )
    parser.add_argument(
        "--container-arch",
        default=os.environ.get("CONTAINER_ARCH", DEFAULTS["container_arch"]),
        help=f"Container architecture (default: {DEFAULTS['container_arch']})",
    )
    parser.add_argument(
        "--platform",
        default=os.environ.get("PLATFORM", DEFAULTS["platform"]),
        help=f"Runner platform mapping (default: {DEFAULTS['platform']})",
    )
    parser.add_argument(
        "--no-platform",
        action="store_true",
        help="Disable platform mapping",
    )
    parser.add_argument(
        "--matrix",
        "-m",
        action="append",
        default=[],
        help="Matrix filter (e.g., --matrix os:ubuntu-latest). Can be specified multiple times.",
    )
    parser.add_argument(
        "--act",
        dest="act_binary",
        default=find_act(),
        help="Path to act binary",
    )
    parser.add_argument(
        "--job",
        "-j",
        help="Run only this job",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Print command without executing",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    args, extra_args = parser.parse_known_args()

    # List workflows
    if args.list:
        workflows = list_workflows(args.workflow_dir)
        if not workflows:
            print(f"No workflows found in {args.workflow_dir}")
            return 1

        print("Available workflows:")
        for wf in workflows:
            print(f"  {wf.stem}")
        return 0

    # Require workflow name if not listing
    if not args.workflow:
        parser.error(
            "workflow name is required (use --list to see available workflows)"
        )

    # Validate event
    if args.event not in VALID_EVENTS:
        print(
            f"Warning: '{args.event}' is not a standard GitHub event", file=sys.stderr
        )
        print(f"Valid events: {', '.join(VALID_EVENTS)}", file=sys.stderr)

    # Resolve workflow
    workflow_path = resolve_workflow(args.workflow, args.workflow_dir)
    if not workflow_path:
        print(f"Error: Could not find workflow '{args.workflow}'", file=sys.stderr)
        print(f"Looked in: {args.workflow_dir}", file=sys.stderr)
        print("Use --list to see available workflows", file=sys.stderr)
        return 1

    # Check if act is available
    if not shutil.which(args.act_binary):
        print(f"Error: 'act' not found at '{args.act_binary}'", file=sys.stderr)
        print(
            "Install act: https://github.com/nektos/act#installation", file=sys.stderr
        )
        print("  brew install act  # macOS", file=sys.stderr)
        return 1

    # Build and run command
    cmd = build_command(args, workflow_path, extra_args)

    # Show event being used
    print(f"Event: {args.event}")
    print(f"+ {' '.join(cmd)}")

    if args.dry_run:
        print("Dry run - command not executed")
        return 0

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nInterrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
