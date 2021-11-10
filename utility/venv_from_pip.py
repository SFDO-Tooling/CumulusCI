import subprocess
import sys
import venv
from pathlib import Path


def cumulusci_dir():
    """Get the root directory for storing persistent data (~/.cumulusci)

    Creates it if it doesn't exist yet.
    """
    config_dir = Path.home() / ".cumulusci"

    if not config_dir.exists():
        config_dir.mkdir(parents=True)

    return config_dir


def install():
    print("Creating CumulusCI Python installation")
    pythondir = cumulusci_dir() / "pythonbin"
    venv.create(
        str(pythondir),
        system_site_packages=False,
        clear=True,
        symlinks=False,
        with_pip=True,
        prompt=".cumulusci/pythonbin",
        # upgrade_deps=False,
    )

    python = None
    for dirname in ["bin", "Scripts"]:
        bindir = pythondir / dirname
        if bindir.exists():
            python = bindir / "python"

    if not python:
        print("Could not find venv!")
        return 1

    print("Updating pip")
    process = subprocess.run(
        [str(python), "-m", "pip", "install", "--upgrade", "pip"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    if process.returncode != 0:
        print(process.stderr)
        return process.returncode

    print("Installing CumulusCI from pip")
    process = subprocess.run(
        [str(python), "-m", "pip", "install", "cumulusci"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    if process.returncode != 0:
        print(process.stderr)
        return process.returncode

    print("CumulusCI installed correctly")
    return 0


sys.exit(install())
