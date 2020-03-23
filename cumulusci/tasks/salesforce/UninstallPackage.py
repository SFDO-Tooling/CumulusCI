from cumulusci.core.utils import deprecated_import

UninstallPackage = deprecated_import(
    "cumulusci.tasks.salesforce.uninstall_package.UninstallPackage"
)

__all__ = ["UninstallPackage"]
