from cumulusci.core.utils import deprecated_import

ListCommunities = deprecated_import(
    "cumulusci.tasks.salesforce.list_communities.ListCommunities"
)

__all__ = ["ListCommunities"]
