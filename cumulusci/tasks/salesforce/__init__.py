# ORDER MATTERS!

# inherit from BaseTask
from cumulusci.tasks.salesforce.BaseSalesforceTask import BaseSalesforceTask

# inherit from BaseSalesforceTask
from cumulusci.tasks.salesforce.BaseSalesforceApiTask import BaseSalesforceApiTask
from cumulusci.tasks.salesforce.BaseSalesforceMetadataApiTask import BaseSalesforceMetadataApiTask

# inherit from BaseSalesforceApiTask
from cumulusci.tasks.salesforce.PackageUpload import PackageUpload
from cumulusci.tasks.salesforce.SOQLQuery import SOQLQuery

# inherit from BaseSalesforceMetadataApiTask
from cumulusci.tasks.salesforce.BaseRetrieveMetadata import BaseRetrieveMetadata
from cumulusci.tasks.salesforce.Deploy import Deploy
from cumulusci.tasks.salesforce.GetInstalledPackages import GetInstalledPackages
from cumulusci.tasks.salesforce.UpdateDependencies import UpdateDependencies

# inherit from BaseRetrieveMetadata
from cumulusci.tasks.salesforce.RetrievePackaged import RetrievePackaged
from cumulusci.tasks.salesforce.RetrieveReportsAndDashboards import RetrieveReportsAndDashboards
from cumulusci.tasks.salesforce.RetrieveUnpackaged import RetrieveUnpackaged

# inherit from Deploy
from cumulusci.tasks.salesforce.BaseUninstallMetadata import BaseUninstallMetadata
from cumulusci.tasks.salesforce.CreatePackage import CreatePackage
from cumulusci.tasks.salesforce.DeployBundles import DeployBundles
from cumulusci.tasks.salesforce.InstallPackageVersion import InstallPackageVersion
from cumulusci.tasks.salesforce.UninstallPackage import UninstallPackage
from cumulusci.tasks.salesforce.UpdateAdminProfile import UpdateAdminProfile

# inherit from BaseUninstallMetadata
from cumulusci.tasks.salesforce.UninstallLocal import UninstallLocal

# inherit from UninstallLocal
from cumulusci.tasks.salesforce.UninstallLocalBundles import UninstallLocalBundles
from cumulusci.tasks.salesforce.UninstallPackaged import UninstallPackaged

# inherit from UninstallLocalBundles
from cumulusci.tasks.salesforce.UninstallLocalNamespacedBundles import UninstallLocalNamespacedBundles

# inherit from UninstallPackaged
from cumulusci.tasks.salesforce.UninstallPackagedIncremental import UninstallPackagedIncremental
