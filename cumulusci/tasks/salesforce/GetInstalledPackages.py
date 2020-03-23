from cumulusci.core.utils import deprecated_import

GetInstalledPackages = deprecated_import(
    "cumulusci.tasks.salesforce.get_installed_packages.GetInstalledPackages"
)

__all__ = ["GetInstalledPackages"]
