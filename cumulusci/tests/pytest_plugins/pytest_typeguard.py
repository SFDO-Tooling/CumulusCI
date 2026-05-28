import sys
import warnings


def pytest_sessionstart(session):
    if sys.version_info >= (3, 14):
        warnings.warn(
            "pytest_typeguard plugin is disabled on Python 3.14+ until typeguard "
            "is upgraded to 4.x (typeguard 2.13.3 uses removed ast.Str). "
            "See pyproject.toml TODO.",
            stacklevel=2,
        )
        return
    from typeguard.importhook import install_import_hook

    install_import_hook(packages=["cumulusci"])
