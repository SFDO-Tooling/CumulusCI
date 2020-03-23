from cumulusci.core.utils import deprecated_import

Deploy = deprecated_import("cumulusci.tasks.salesforce.deploy_metadata.Deploy")

__all__ = ["Deploy"]
