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


def runsubprocess(args):
    process = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    FIXME = True  # remove this
    if process.returncode != 0 or FIXME:
        print(process.stdout)
        print(process.stderr)

    if process.returncode != 0:
        raise AssertionError(f"{args} : {process.returncode}")


def install():

    print("Creating CumulusCI Python installation")
    pythondir = cumulusci_dir() / "cci_python_env"

    # actually this workaround doesn't make sense so I need to get
    # to the bottom of this.
    # symlinks = (
    #     True if sys.platform == "darwin" else False
    # )  # https://bugs.python.org/issue38705

    venv.create(
        str(pythondir),
        system_site_packages=False,
        clear=True,
        symlinks=False,
        with_pip=True,
        prompt=".cumulusci/cci_python_env",
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
    runsubprocess(
        [str(python), "-m", "pip", "install", "--upgrade", "pip"],
    )

    print("Installing CumulusCI from pip")
    runsubprocess(
        [str(python), "-m", "pip", "install", "cumulusci"],
    )

    # print("Installing pipx")
    # runsubprocess(
    #     [str(python), "-m", "pip", "install", "pipx"],
    # )

    # runsubprocess(
    #     [str(python), "-m", "pipx", "ensurepath"],
    # )

    # print("Installing CumulusCI from pipx")
    # runsubprocess(
    #     [str(python), "-m", "pipx", "install", "cumulusci"],
    # )

    print("CumulusCI venv created!")
    return 0


sys.exit(install())
