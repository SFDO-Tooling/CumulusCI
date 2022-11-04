import sys

import click
import pkg_resources
import sarge

from .runtime import pass_runtime


@click.group("robot", help="Commands for working with Robot Framework")
def robot():
    pass


# Commands for group: robot


@robot.command(
    name="install_playwright",
    help="Install libraries necessary to use playwright with robot framework",
)
@pass_runtime(require_project=False, require_keychain=False)  # maybe not needed...
@click.option("-n", "--dry_run", is_flag=True)
def robot_install_playwright(runtime, dry_run):
    _require_npm()
    if _is_package_installed("robotframework-browser"):
        click.echo("Playwright support seems to already have been installed")
    else:
        _install_browser_library(dry_run)
        _initialize_browser_library(dry_run)


@robot.command(
    name="uninstall_playwright",
    help="Uninstalls the robotframework-browser package and node modules",
)
def robot_uninstall_playwright():
    """Attempt to uninstall playwright"""
    p1 = sarge.Command([sys.executable, "-m", "Browser.entry", "clean-node"])
    p2 = sarge.Command(
        [sys.executable, "-m", "pip", "uninstall", "robotframework-browser", "--yes"]
    )

    click.echo("removing node modules...")
    click.echo(f"running {' '.join(p1.args)}")
    p1.run()
    click.echo("removing python module robotframework-browser...")
    click.echo(f"running {' '.join(p2.args)}")
    p2.run()
    if p1.returncode or p2.returncode:
        raise click.ClickException("Some files might not have been uninstalled")
    click.echo("uninstallation is complete")


def _install_browser_library(dry_run=False):
    pip_cmd = [sys.executable, "-m", "pip", "install", "robotframework-browser"]
    click.echo("installing robotframework-browser ...")
    if dry_run:
        click.echo(f"would run {' '.join(pip_cmd)}")
    else:
        click.echo(f"running '{' '.join(pip_cmd)}' ...")
        c = sarge.Capture()
        p = sarge.Command(pip_cmd, shell=False, stdout=c, stderr=c)
        p.run()
        if p.returncode:
            click.echo(c.text)
            raise click.ClickException("robotframework-browser was not installed")
        click.echo("robotframework-browser has been installed")


def _initialize_browser_library(dry_run=False):
    """Call the browser library's initialization function

    There is a command line tool to do it, but it might not be
    installed, or might be installed somewhere that is not on
    the path. This method is documneted in the README and should
    work as long as the library is installed.
    """

    browser_cmd = [sys.executable, "-m", "Browser.entry", "init"]
    if dry_run:
        click.echo(f"would run {' '.join(browser_cmd)}")
    else:
        click.echo(f"running {' '.join(browser_cmd)}")
        c = sarge.Capture()
        p = sarge.Command(browser_cmd, shell=False, stdout=c, stderr=c)
        p.run()
        if p.returncode:
            click.echo(c.text)
            raise click.ClickException("unable to initialize browser library")
        click.echo("Browser library has been initialized.")


def _require_npm():
    """Raises an exception if npm can't be run"""

    c = sarge.Capture()
    # Note: the string version of the command is used here because
    # on windows it can't find "npm" if we use the list form of
    # the command. Silly Windows.
    p = sarge.Command("npm --version", shell=True, stdout=c, stderr=c)
    p.run()
    if p.returncode:
        click.echo(c.text)
        raise click.ClickException(
            "Unable to find a usable npm. Have you installed Node.js?"
        )


def _is_package_installed(package_name):
    """Return True if the given package is installed"""
    # technique shamelessly stolen from https://stackoverflow.com/a/44210735/7432
    return package_name in {pkg.key for pkg in pkg_resources.working_set}
