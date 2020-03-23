from cumulusci.core.utils import deprecated_import

PublishCommunity = deprecated_import(
    "cumulusci.tasks.salesforce.publish_community.PublishCommunity"
)

__all__ = ["PublishCommunity"]
