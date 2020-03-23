from cumulusci.core.utils import deprecated_import

DeployBundles = deprecated_import(
    "cumulusci.tasks.salesforce.deploy_bundles.DeployBundles"
)

__all__ = ["DeployBundles"]
