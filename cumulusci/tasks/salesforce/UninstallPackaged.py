from cumulusci.salesforce_api.metadata import ApiRetrievePackaged
from cumulusci.tasks.salesforce import UninstallLocal
from cumulusci.utils import temporary_dir, zip_subfolder


class UninstallPackaged(UninstallLocal):

    task_options = {
        "package": {
            "description": "The package name to uninstall.  All metadata from the package will be retrieved and a custom destructiveChanges.xml package will be constructed and deployed to delete all deleteable metadata from the package.  Defaults to project__package__name",
            "required": True,
        },
        "purge_on_delete": {
            "description": "Sets the purgeOnDelete option for the deployment.  Defaults to True",
            "required": True,
        },
        "dry_run": {
            "description": "Perform a dry run of the operation without actually deleting any components, and display the components that would be deleted."
        },
    }

    def _init_options(self, kwargs):
        super(UninstallPackaged, self)._init_options(kwargs)
        if "package" not in self.options:
            self.options["package"] = self.project_config.project__package__name

    def _retrieve_packaged(self):
        retrieve_api = ApiRetrievePackaged(
            self,
            self.options["package"],
            self.project_config.project__package__api_version,
        )
        packaged = retrieve_api()
        packaged = zip_subfolder(packaged, self.options["package"])
        return packaged

    def _get_destructive_changes(self, path=None):
        self.logger.info(
            "Retrieving metadata in package {} from target org".format(
                self.options["package"]
            )
        )
        packaged = self._retrieve_packaged()

        with temporary_dir() as tempdir:
            packaged.extractall(tempdir)
            destructive_changes = super(
                UninstallPackaged, self
            )._get_destructive_changes(tempdir)

        self.logger.info(
            "Deleting metadata in package {} from target org".format(
                self.options["package"]
            )
        )
        return destructive_changes
