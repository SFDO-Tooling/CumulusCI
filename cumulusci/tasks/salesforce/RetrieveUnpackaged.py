from cumulusci.core.utils import deprecated_import

RetrieveUnpackaged = deprecated_import(
    "cumulusci.tasks.salesforce.retrieve_unpackaged.RetrieveUnpackaged"
)

__all__ = ["RetrieveUnpackaged"]
