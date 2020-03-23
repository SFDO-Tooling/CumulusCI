from cumulusci.core.utils import deprecated_import

UninstallLocal = deprecated_import(
    "cumulusci.tasks.salesforce.uninstall_local.UninstallLocal"
)

__all__ = ["UninstallLocal"]
