from cumulusci.core.utils import deprecated_import

UninstallLocalBundles = deprecated_import(
    "cumulusci.tasks.salesforce.uninstall_local_bundles.UninstallLocalBundles"
)

__all__ = ["UninstallLocalBundles"]
