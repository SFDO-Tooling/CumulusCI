from typeguard.importhook import install_import_hook


def pytest_sessionstart(session):
    install_import_hook(packages=["cumulusci"])
