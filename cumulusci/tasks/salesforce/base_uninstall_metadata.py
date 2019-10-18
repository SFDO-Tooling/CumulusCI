from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.salesforce import Deploy
from cumulusci.salesforce_api.package_zip import DestructiveChangesZipBuilder


uninstall_task_options = Deploy.task_options.copy()
uninstall_task_options["purge_on_delete"] = {
    "description": "Sets the purgeOnDelete option for the deployment. Defaults to True"
}


class BaseUninstallMetadata(Deploy):
    task_options = uninstall_task_options

    def _init_options(self, kwargs):
        super(BaseUninstallMetadata, self)._init_options(kwargs)
        self.options["purge_on_delete"] = process_bool_arg(
            self.options.get("purge_on_delete", True)
        )

    def _get_api(self, path=None):
        destructive_changes = self._get_destructive_changes(path=path)
        if not destructive_changes:
            return
        package_zip = DestructiveChangesZipBuilder(
            destructive_changes, self.project_config.project__package__api_version
        )
        api = self.api_class(
            self, package_zip(), purge_on_delete=self.options["purge_on_delete"]
        )
        return api
