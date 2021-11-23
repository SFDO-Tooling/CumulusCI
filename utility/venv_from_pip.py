import os
import shutil
import subprocess
import sys
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


def find_python(ccipythondir):
    for dirname in ["bin", "Scripts"]:
        bindir = ccipythondir / dirname
        if bindir.exists():
            for filename in ["python", "python3", "python.exe"]:
                python = bindir / filename
                if python.exists():
                    return python
            if not python.exists():
                raise AssertionError(
                    f"Cannot find Python in {bindir}: {list(bindir.iterdir())}"
                )
    return python


def install():

    print("Creating CumulusCI Python installation")
    ccipythondir = cumulusci_dir() / "cci_python_env"

    # Normal venv doesn't work with dynamically linked binaries.
    # https://bugs.python.org/issue38705

    # venv.create(
    #     str(ccipythondir),
    #     system_site_packages=False,
    #     clear=True,
    #     symlinks=False,
    #     with_pip=True,
    #     prompt=".cumulusci/cci_python_env",
    #     # upgrade_deps=False,
    # )

    # using a python build with static binaries is another solution,
    # but this works.

    bindir = Path(sys.executable).parent
    installpythonroot = bindir.parent

    if ccipythondir.exists():
        shutil.rmtree(ccipythondir)
    shutil.copytree(installpythonroot, ccipythondir, symlinks=True)

    python = find_python(ccipythondir)
    if not python:
        raise AssertionError(
            f"Cannot find Python dir in {ccipythondir}: {list(ccipythondir.iterdir())}"
        )

    def runpip(args):
        return runsubprocess([str(python), "-I", "-m", "pip", *args])

    print("Updating pip")
    runpip(
        ["install", "--upgrade", "pip", "userpath"],
    )

    print("Installing CumulusCI from pip")
    runpip(
        ["install", "cumulusci"],
    )

    plugin_requirements = ccipythondir / "plugin_requirements.txt"
    if plugin_requirements.exists():
        runpip(
            ["install", "-r", plugin_requirements],
        )

    rundir = ccipythondir / "run"
    rundir.mkdir(exist_ok=True)
    if os.name == "posix":
        path = "bin"
        programs = ["cci", "snowfakery", "snowbench"]
    else:
        path = "Scripts"
        programs = [
            "cci.exe",
            "snowfakery.exe",
            "snowbench.exe",
        ]
    for executable in programs:
        source = ccipythondir / path / executable
        target = rundir / executable
        assert source.exists(), str(source)
        source.rename(target)

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
