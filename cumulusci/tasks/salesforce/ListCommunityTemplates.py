from cumulusci.core.utils import deprecated_import

ListCommunityTemplates = deprecated_import(
    "cumulusci.tasks.salesforce.list_community_templates.ListCommunityTemplates"
)

__all__ = ["ListCommunityTemplates"]
