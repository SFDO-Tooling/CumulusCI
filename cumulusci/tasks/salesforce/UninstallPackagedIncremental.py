from cumulusci.core.utils import deprecated_import

UninstallPackagedIncremental = deprecated_import(
    "cumulusci.tasks.salesforce.uninstall_packaged_incremental.UninstallPackagedIncremental"
)

__all__ = ["UninstallPackagedIncremental"]
