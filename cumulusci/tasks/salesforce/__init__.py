import sys
from cumulusci.core.utils import deprecated_import

# ORDER MATTERS!

# Please do not add more tasks to this file! Refer to them in their
# real module home. The amount of runtime it taskes to load all of these
# tasks is measurable and their inter-dependencies can cause problems.

# inherit from BaseTask
from cumulusci.tasks.salesforce.BaseSalesforceTask import BaseSalesforceTask

# inherit from BaseSalesforceTask
from cumulusci.tasks.salesforce.BaseSalesforceApiTask import BaseSalesforceApiTask
from cumulusci.tasks.salesforce.BaseSalesforceMetadataApiTask import (
    BaseSalesforceMetadataApiTask,
)

# inherit from BaseSalesforceApiTask
PackageUpload = deprecated_import(
    "cumulusci.tasks.salesforce.package_upload.PackageUpload"
)
SOQLQuery = deprecated_import("cumulusci.tasks.salesforce.soql_query.SOQLQuery")
CreateCommunity = deprecated_import(
    "cumulusci.tasks.salesforce.create_community.CreateCommunity"
)
ListCommunities = deprecated_import(
    "cumulusci.tasks.salesforce.list_communities.ListCommunities"
)
ListCommunityTemplates = deprecated_import(
    "cumulusci.tasks.salesforce.list_community_templates.ListCommunityTemplates"
)
PublishCommunity = deprecated_import(
    "cumulusci.tasks.salesforce.publish_community.PublishCommunity"
)
from cumulusci.tasks.salesforce.custom_settings import LoadCustomSettings
from cumulusci.tasks.salesforce.trigger_handlers import SetTDTMHandlerStatus

# inherit from BaseSalesforceMetadataApiTask
from cumulusci.tasks.salesforce.BaseRetrieveMetadata import BaseRetrieveMetadata

Deploy = deprecated_import("cumulusci.tasks.salesforce.deploy_metadata.Deploy")
GetInstalledPackages = deprecated_import(
    "cumulusci.tasks.salesforce.get_installed_packages.GetInstalledPackages"
)
UpdateDependencies = deprecated_import(
    "cumulusci.tasks.salesforce.update_dependencies.UpdateDependencies"
)

# inherit from BaseSalesforceApiTask and use Deploy
EnsureRecordTypes = deprecated_import(
    "cumulusci.tasks.salesforce.ensure_record_types.EnsureRecordTypes"
)

# inherit from BaseRetrieveMetadata
RetrievePackaged = deprecated_import(
    "cumulusci.tasks.salesforce.retrieve_packaged.RetrievePackaged"
)
from cumulusci.tasks.salesforce.RetrieveReportsAndDashboards import (
    RetrieveReportsAndDashboards,
)

RetrieveUnpackaged = deprecated_import(
    "cumulusci.tasks.salesforce.retrieve_unpackaged.RetrieveUnpackaged"
)

# inherit from Deploy
from cumulusci.tasks.salesforce.BaseUninstallMetadata import BaseUninstallMetadata

CreatePackage = deprecated_import(
    "cumulusci.tasks.salesforce.create_package.CreatePackage"
)
DeployBundles = deprecated_import(
    "cumulusci.tasks.salesforce.deploy_bundles.DeployBundles"
)
InstallPackageVersion = deprecated_import(
    "cumulusci.tasks.salesforce.install_package_version.InstallPackageVersion"
)
UninstallPackage = deprecated_import(
    "cumulusci.tasks.salesforce.uninstall_package.UninstallPackage"
)

# Backwards-compatibility for UpdateAdminProfile/UpdateProfile
from cumulusci.tasks.salesforce.update_profile import (
    ProfileGrantAllAccess,
    UpdateProfile,
    UpdateAdminProfile,
)
from cumulusci.tasks.salesforce import update_profile

sys.modules["cumulusci.tasks.salesforce.UpdateAdminProfile"] = update_profile

# inherit from BaseUninstallMetadata
UninstallLocal = deprecated_import(
    "cumulusci.tasks.salesforce.uninstall_local.UninstallLocal"
)

# inherit from UninstallLocal
UninstallLocalBundles = deprecated_import(
    "cumulusci.tasks.salesforce.uninstall_local_bundles.UninstallLocalBundles"
)
UninstallPackaged = deprecated_import(
    "cumulusci.tasks.salesforce.uninstall_packaged.UninstallPackaged"
)

# inherit from UninstallLocalBundles
from cumulusci.tasks.salesforce.UninstallLocalNamespacedBundles import (
    UninstallLocalNamespacedBundles,
)

# inherit from UninstallPackaged
from cumulusci.tasks.salesforce.UninstallPackagedIncremental import (
    UninstallPackagedIncremental,
)

# flake 8 hacks to prevent pre commit rejection
flake8Hack = (
    BaseSalesforceTask,
    BaseSalesforceApiTask,
    BaseSalesforceMetadataApiTask,
    PackageUpload,
    SOQLQuery,
    CreateCommunity,
    ListCommunities,
    ListCommunityTemplates,
    PublishCommunity,
    BaseRetrieveMetadata,
    Deploy,
    GetInstalledPackages,
    UpdateDependencies,
    EnsureRecordTypes,
    RetrievePackaged,
    RetrieveReportsAndDashboards,
    RetrieveUnpackaged,
    BaseUninstallMetadata,
    CreatePackage,
    DeployBundles,
    InstallPackageVersion,
    UninstallPackage,
    UpdateProfile,
    UpdateAdminProfile,
    ProfileGrantAllAccess,
    UninstallLocal,
    UninstallLocalBundles,
    UninstallPackaged,
    UninstallLocalNamespacedBundles,
    UninstallPackagedIncremental,
    LoadCustomSettings,
    SetTDTMHandlerStatus,
)
