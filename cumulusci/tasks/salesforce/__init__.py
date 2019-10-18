# ORDER MATTERS!

# inherit from BaseTask
from cumulusci.tasks.salesforce.base_salesforce_task import BaseSalesforceTask

# inherit from BaseSalesforceTask
from cumulusci.tasks.salesforce.base_salesforce_api_task import BaseSalesforceApiTask
from cumulusci.tasks.salesforce.base_salesforce_metadata_api_task import (
    BaseSalesforceMetadataApiTask,
)

# inherit from BaseSalesforceApiTask
from cumulusci.tasks.salesforce.package_upload import PackageUpload
from cumulusci.tasks.salesforce.soql_query import SOQLQuery
from cumulusci.tasks.salesforce.create_community import CreateCommunity
from cumulusci.tasks.salesforce.list_communities import ListCommunities
from cumulusci.tasks.salesforce.list_community_templates import ListCommunityTemplates
from cumulusci.tasks.salesforce.publish_community import PublishCommunity

# inherit from BaseSalesforceMetadataApiTask
from cumulusci.tasks.salesforce.base_retrieve_metadata import BaseRetrieveMetadata
from cumulusci.tasks.salesforce.deploy import Deploy
from cumulusci.tasks.salesforce.get_installed_packages import GetInstalledPackages
from cumulusci.tasks.salesforce.update_dependencies import UpdateDependencies

# inherit from BaseSalesforceApiTask and use Deploy
from cumulusci.tasks.salesforce.ensure_record_types import EnsureRecordTypes

# inherit from BaseRetrieveMetadata
from cumulusci.tasks.salesforce.retrieve_packaged import RetrievePackaged
from cumulusci.tasks.salesforce.retrieve_reports_and_dashboards import (
    RetrieveReportsAndDashboards,
)
from cumulusci.tasks.salesforce.retrieve_unpackaged import RetrieveUnpackaged

# inherit from Deploy
from cumulusci.tasks.salesforce.base_uninstall_metadata import BaseUninstallMetadata
from cumulusci.tasks.salesforce.create_package import CreatePackage
from cumulusci.tasks.salesforce.deploy_bundles import DeployBundles
from cumulusci.tasks.salesforce.install_package_version import InstallPackageVersion
from cumulusci.tasks.salesforce.uninstall_package import UninstallPackage
from cumulusci.tasks.salesforce.update_admin_profile import UpdateAdminProfile

# inherit from BaseUninstallMetadata
from cumulusci.tasks.salesforce.uninstall_local import UninstallLocal

# inherit from UninstallLocal
from cumulusci.tasks.salesforce.uninstall_local_bundles import UninstallLocalBundles
from cumulusci.tasks.salesforce.uninstall_packaged import UninstallPackaged

# inherit from UninstallLocalBundles
from cumulusci.tasks.salesforce.uninstall_local_namespaced_bundles import (
    UninstallLocalNamespacedBundles,
)

# inherit from UninstallPackaged
from cumulusci.tasks.salesforce.uninstall_packaged_incremental import (
    UninstallPackagedIncremental,
)

__all__ = (
    "BaseSalesforceTask",
    "BaseSalesforceApiTask",
    "BaseSalesforceMetadataApiTask",
    "PackageUpload",
    "SOQLQuery",
    "CreateCommunity",
    "ListCommunities",
    "ListCommunityTemplates",
    "PublishCommunity",
    "BaseRetrieveMetadata",
    "Deploy",
    "GetInstalledPackages",
    "UpdateDependencies",
    "EnsureRecordTypes",
    "RetrievePackaged",
    "RetrieveReportsAndDashboards",
    "RetrieveUnpackaged",
    "BaseUninstallMetadata",
    "CreatePackage",
    "DeployBundles",
    "InstallPackageVersion",
    "UninstallPackage",
    "UpdateAdminProfile",
    "UninstallLocal",
    "UninstallLocalBundles",
    "UninstallPackaged",
    "UninstallLocalNamespacedBundles",
    "UninstallPackagedIncremental",
)
