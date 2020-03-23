from cumulusci.core.utils import deprecated_import

UninstallPackaged = deprecated_import(
    "cumulusci.tasks.salesforce.uninstall_packaged.UninstallPackaged"
)

__all__ = ["UninstallPackaged"]
