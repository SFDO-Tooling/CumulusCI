from cumulusci.core.utils import deprecated_import

RetrievePackaged = deprecated_import(
    "cumulusci.tasks.salesforce.retrieve_packaged.RetrievePackaged"
)

__all__ = ["RetrievePackaged"]
