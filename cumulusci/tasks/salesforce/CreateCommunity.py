from cumulusci.core.utils import deprecated_import

CreateCommunity = deprecated_import(
    "cumulusci.tasks.salesforce.create_community.CreateCommunity"
)

__all__ = ["CreateCommunity"]
