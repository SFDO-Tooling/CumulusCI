from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.metadata.package import PackageXmlGenerator
from cumulusci.tasks.salesforce import UninstallLocalBundles


class UninstallLocalNamespacedBundles(UninstallLocalBundles):

    task_options = {
        "path": {
            "description": "The path to a directory containing the metadata bundles (subdirectories) to uninstall",
            "required": True,
        },
        "managed": {
            "description": "If True, will insert the actual namespace prefix.  Defaults to False or no namespace"
        },
        "namespace": {
            "description": "The namespace to replace the token with if in managed mode. Defaults to project__package__namespace"
        },
        "filename_token": {
            "description": "The path to the parent directory containing the metadata bundles directories",
            "required": True,
        },
        "purge_on_delete": {
            "description": "Sets the purgeOnDelete option for the deployment.  Defaults to True",
            "required": True,
        },
    }

    def _init_options(self, kwargs):
        super(UninstallLocalNamespacedBundles, self)._init_options(kwargs)

        self.options["managed"] = process_bool_arg(self.options.get("managed", False))
        if "namespace" not in self.options:
            self.options["namespace"] = self.project_config.project__package__namespace
        self.options["purge_on_delete"] = process_bool_arg(
            self.options.get("purge_on_delete", True)
        )

    def _get_destructive_changes(self, path=None):
        if not path:
            path = self.options["path"]

        generator = PackageXmlGenerator(
            directory=path,
            api_version=self.project_config.project__package__api_version,
            delete=True,
        )
        namespace = ""
        if self.options["managed"]:
            if self.options["namespace"]:
                namespace = self.options["namespace"] + "__"

        destructive_changes = generator()
        destructive_changes = destructive_changes.replace(
            self.options["filename_token"], namespace
        )

        return destructive_changes
