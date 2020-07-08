"""Salesforce tasks

This package uses a lazy import system inspired by werkzeug
(for startup speed and to avoid problems with import cycles).
We should be able to replace LazyModule with a module-level __getattr__
one we drop support for Python 3.6.
"""


from types import ModuleType
import sys


class LazyModule(ModuleType):
    def __init__(self, origins):
        self._origins = origins

    def __getattr__(self, name):
        if name in self._origins:
            print(f"getattr: {name}")
            origin = self._origins[name]
            module = __import__(origin, None, None, [name])
            setattr(self, name, getattr(module, name))
        return ModuleType.__getattribute__(self, name)


new_module = sys.modules[__name__] = LazyModule(
    {
        "BaseRetrieveMetadata": "cumulusci.tasks.salesforce.BaseRetrieveMetadata",
        "BaseSalesforceTask": "cumulusci.tasks.salesforce.BaseSalesforceTask",
        "BaseSalesforceApiTask": "cumulusci.tasks.salesforce.BaseSalesforceApiTask",
        "BaseSalesforceMetadataApiTask": "cumulusci.tasks.salesforce.BaseSalesforceMetadataApiTask",
        "BaseUninstallMetadata": "cumulusci.tasks.salesforce.BaseUninstallMetadata",
        "CreateCommunity": "cumulusci.tasks.salesforce.CreateCommunity",
        "CreatePackage": "cumulusci.tasks.salesforce.CreatePackage",
        "Deploy": "cumulusci.tasks.salesforce.Deploy",
        "DeployBundles": "cumulusci.tasks.salesforce.DeployBundles",
        "EnsureRecordTypes": "cumulusci.tasks.salesforce.EnsureRecordTypes",
        "GetInstalledPackages": "cumulusci.tasks.preflight.packages",
        "InstallPackageVersion": "cumulusci.tasks.salesforce.InstallPackageVersion",
        "ListCommunities": "cumulusci.tasks.salesforce.ListCommunities",
        "ListCommunityTemplates": "cumulusci.tasks.salesforce.ListCommunityTemplates",
        "LoadCustomSettings": "cumulusci.tasks.salesforce.custom_settings",
        "PackageUpload": "cumulusci.tasks.salesforce.package_upload",
        "ProfileGrantAllAccess": "cumulusci.tasks.salesforce.update_profile",
        "PublishCommunity": "cumulusci.tasks.salesforce.PublishCommunity",
        "RetrievePackaged": "cumulusci.tasks.salesforce.RetrievePackaged",
        "RetrieveReportsAndDashboards": "cumulusci.tasks.salesforce.RetrieveReportsAndDashboards",
        "RetrieveUnpackaged": "cumulusci.tasks.salesforce.RetrieveUnpackaged",
        "SOQLQuery": "cumulusci.tasks.salesforce.SOQLQuery",
        "SetTDTMHandlerStatus": "cumulusci.tasks.salesforce.trigger_handlers",
        "UninstallLocal": "cumulusci.tasks.salesforce.UninstallLocal",
        "UninstallLocalBundles": "cumulusci.tasks.salesforce.UninstallLocalBundles",
        "UninstallLocalNamespacedBundles": "cumulusci.tasks.salesforce.UninstallLocalNamespacedBundles",
        "UninstallPackage": "cumulusci.tasks.salesforce.UninstallPackage",
        "UninstallPackaged": "cumulusci.tasks.salesforce.UninstallPackaged",
        "UninstallPackagedIncremental": "cumulusci.tasks.salesforce.UninstallPackagedIncremental",
        "UpdateDependencies": "cumulusci.tasks.salesforce.UpdateDependencies",
        "UpdateProfile": "cumulusci.tasks.salesforce.update_profile",
        "UpdateAdminProfile": "cumulusci.tasks.salesforce.update_profile",
    }
)
new_module.__dict__.update(
    {
        "__doc__": __doc__,
        "__file__": __file__,
        "__path__": __path__,
        "__spec__": __spec__,
        "__all__": tuple(new_module._origins),
    }
)
