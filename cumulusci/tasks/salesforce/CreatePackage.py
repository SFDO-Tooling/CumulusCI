from cumulusci.core.utils import deprecated_import

CreatePackage = deprecated_import(
    "cumulusci.tasks.salesforce.create_package.CreatePackage"
)

__all__ = ["CreatePackage"]
