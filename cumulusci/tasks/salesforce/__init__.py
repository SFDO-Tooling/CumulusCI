import sys

# ORDER MATTERS!

# inherit from BaseTask
from cumulusci.tasks.salesforce.BaseSalesforceTask import BaseSalesforceTask

# inherit from BaseSalesforceTask
from cumulusci.tasks.salesforce.BaseSalesforceApiTask import BaseSalesforceApiTask
from cumulusci.tasks.salesforce.BaseSalesforceMetadataApiTask import (
    BaseSalesforceMetadataApiTask,
)

# inherit from BaseSalesforceApiTask
from cumulusci.tasks.salesforce.package_upload import PackageUpload
from cumulusci.tasks.salesforce.SOQLQuery import SOQLQuery
from cumulusci.tasks.salesforce.CreateCommunity import CreateCommunity
from cumulusci.tasks.salesforce.ListCommunities import ListCommunities
from cumulusci.tasks.salesforce.ListCommunityTemplates import ListCommunityTemplates
from cumulusci.tasks.salesforce.PublishCommunity import PublishCommunity
from cumulusci.tasks.salesforce.custom_settings import LoadCustomSettings
from cumulusci.tasks.salesforce.trigger_handlers import SetTDTMHandlerStatus

# inherit from BaseSalesforceMetadataApiTask
from cumulusci.tasks.salesforce.BaseRetrieveMetadata import BaseRetrieveMetadata
from cumulusci.tasks.salesforce.Deploy import Deploy
from cumulusci.tasks.salesforce.GetInstalledPackages import GetInstalledPackages
from cumulusci.tasks.salesforce.UpdateDependencies import UpdateDependencies

# inherit from BaseSalesforceApiTask and use Deploy
from cumulusci.tasks.salesforce.EnsureRecordTypes import EnsureRecordTypes

# inherit from BaseRetrieveMetadata
from cumulusci.tasks.salesforce.RetrievePackaged import RetrievePackaged
from cumulusci.tasks.salesforce.RetrieveReportsAndDashboards import (
    RetrieveReportsAndDashboards,
)
from cumulusci.tasks.salesforce.RetrieveUnpackaged import RetrieveUnpackaged

# inherit from Deploy
from cumulusci.tasks.salesforce.BaseUninstallMetadata import BaseUninstallMetadata
from cumulusci.tasks.salesforce.CreatePackage import CreatePackage
from cumulusci.tasks.salesforce.DeployBundles import DeployBundles
from cumulusci.tasks.salesforce.InstallPackageVersion import InstallPackageVersion
from cumulusci.tasks.salesforce.UninstallPackage import UninstallPackage

# Backwards-compatibility for UpdateAdminProfile/UpdateProfile
from cumulusci.tasks.salesforce.update_profile import (
    ProfileGrantAllAccess,
    UpdateProfile,
    UpdateAdminProfile,
)
from cumulusci.tasks.salesforce import update_profile

sys.modules["cumulusci.tasks.salesforce.UpdateAdminProfile"] = update_profile

# inherit from BaseUninstallMetadata
from cumulusci.tasks.salesforce.UninstallLocal import UninstallLocal

# inherit from UninstallLocal
from cumulusci.tasks.salesforce.UninstallLocalBundles import UninstallLocalBundles
from cumulusci.tasks.salesforce.UninstallPackaged import UninstallPackaged

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
