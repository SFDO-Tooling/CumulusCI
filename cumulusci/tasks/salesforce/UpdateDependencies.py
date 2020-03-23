from cumulusci.core.utils import deprecated_import

UpdateDependencies = deprecated_import(
    "cumulusci.tasks.salesforce.update_dependencies.UpdateDependencies"
)

__all__ = ["UpdateDependencies"]
