from cumulusci.core.utils import deprecated_import

UninstallLocalNamespacedBundles = deprecated_import(
    "cumulusci.tasks.salesforce.uninstall_local_namespaced_bundles.UninstallLocalNamespacedBundles"
)

__all__ = ["UninstallLocalNamespacedBundles"]
