from cumulusci.core.utils import process_bool_arg
from cumulusci.salesforce_api.package_zip import DestructiveChangesZipBuilder
from cumulusci.tasks.salesforce import Deploy

uninstall_task_options = Deploy.task_options.copy()
uninstall_task_options["purge_on_delete"] = {
    "description": "Sets the purgeOnDelete option for the deployment. Defaults to True"
}
uninstall_task_options["dry_run"] = {
    "description": "Perform a dry run of the operation without actually deleting any components, and display the components that would be deleted."
}


class BaseUninstallMetadata(Deploy):
    task_options = uninstall_task_options

    def _init_options(self, kwargs):
        super(BaseUninstallMetadata, self)._init_options(kwargs)
        self.options["purge_on_delete"] = process_bool_arg(
            self.options.get("purge_on_delete", True)
        )
        self.options["dry_run"] = process_bool_arg(self.options.get("dry_run", False))

    def _get_api(self, path=None):
        destructive_changes = self._get_destructive_changes(path=path)
        if not destructive_changes:
            return
        if self.options["dry_run"]:
            self.logger.info(
                "Performing uninstall dry run. This destructive deployment was created:"
            )
            self.logger.info(destructive_changes)
            return

        package_zip = DestructiveChangesZipBuilder(
            destructive_changes, self.project_config.project__package__api_version
        )
        api = self.api_class(
            self, package_zip(), purge_on_delete=self.options["purge_on_delete"]
        )
        return api
