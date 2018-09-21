from cumulusci.core.utils import process_bool_arg
from cumulusci.salesforce_api.package_zip import UninstallPackageZipBuilder
from cumulusci.tasks.salesforce import Deploy


class UninstallPackage(Deploy):
    task_options = {
        "namespace": {
            "description": "The namespace of the package to uninstall.  Defaults to project__package__namespace",
            "required": True,
        },
        "purge_on_delete": {
            "description": "Sets the purgeOnDelete option for the deployment.  Defaults to True",
            "required": True,
        },
    }

    def _init_options(self, kwargs):
        super(UninstallPackage, self)._init_options(kwargs)
        if "namespace" not in self.options:
            self.options["namespace"] = self.project_config.project__package__namespace
        self.options["purge_on_delete"] = process_bool_arg(
            self.options.get("purge_on_delete", True)
        )

    def _get_api(self, path=None):
        package_zip = UninstallPackageZipBuilder(
            self.options["namespace"], self.project_config.project__package__api_version
        )
        return self.api_class(
            self, package_zip(), purge_on_delete=self.options["purge_on_delete"]
        )
