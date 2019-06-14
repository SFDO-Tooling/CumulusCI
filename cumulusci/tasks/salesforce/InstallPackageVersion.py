from cumulusci.core.utils import process_bool_arg
from cumulusci.salesforce_api.exceptions import MetadataApiError
from cumulusci.salesforce_api.package_zip import InstallPackageZipBuilder
from cumulusci.tasks.salesforce import Deploy


class InstallPackageVersion(Deploy):
    task_options = {
        "name": {
            "description": "The name of the package to install.  Defaults to project__package__name_managed",
            "required": False,
        },
        "namespace": {
            "description": "The namespace of the package to install.  Defaults to project__package__namespace",
            "required": True,
        },
        "version": {
            "description": 'The version of the package to install.  "latest" and "latest_beta" can be used to trigger lookup via Github Releases on the repository.',
            "required": True,
        },
        "activateRSS": {
            "description": "If True, preserve the isActive state of "
            "Remote Site Settings and Content Security Policy "
            "in the package. Default: False."
        },
        "password": {"description": "The package password. Optional."},
        "retries": {"description": "Number of retries (default=5)"},
        "retry_interval": {
            "description": "Number of seconds to wait before the next retry (default=5),"
        },
        "retry_interval_add": {
            "description": "Number of seconds to add before each retry (default=30),"
        },
    }

    def _init_options(self, kwargs):
        super(InstallPackageVersion, self)._init_options(kwargs)
        if "namespace" not in self.options:
            self.options["namespace"] = self.project_config.project__package__namespace
        if "name" not in self.options:
            self.options["name"] = (
                self.project_config.project__package__name_managed
                or self.project_config.project__package__name
                or self.options["namespace"]
            )
        if "retries" not in self.options:
            self.options["retries"] = 5
        if "retry_interval" not in self.options:
            self.options["retry_interval"] = 5
        if "retry_interval_add" not in self.options:
            self.options["retry_interval_add"] = 30
        version = self.options.get("version")
        if version == "latest":
            self.options["version"] = self.project_config.get_latest_version()
            self.logger.info(
                "Installing latest release: {}".format(self.options["version"])
            )
        elif version == "latest_beta":
            self.options["version"] = self.project_config.get_latest_version(beta=True)
            self.logger.info(
                "Installing latest beta release: {}".format(self.options["version"])
            )
        elif version == "previous":
            self.options["version"] = self.project_config.get_previous_version()
            self.logger.info(
                "Installing previous release: {}".format(self.options["version"])
            )
        self.options["activateRSS"] = process_bool_arg(self.options.get("activateRSS"))

    def _get_api(self, path=None):
        package_zip = InstallPackageZipBuilder(
            namespace=self.options["namespace"],
            version=self.options["version"],
            activateRSS=self.options["activateRSS"],
            password=self.options.get("password"),
        )
        return self.api_class(self, package_zip(), purge_on_delete=False)

    def _run_task(self):
        self._retry()

    def _try(self):
        api = self._get_api()
        api()

    def _is_retry_valid(self, e):
        if isinstance(e, MetadataApiError) and (
            "This package is not yet available" in str(e)
            or "InstalledPackage version number" in str(e)
        ):
            return True

    def freeze(self, step):
        options = self.options.copy()
        options["version"] = str(options["version"])
        name = options.pop("name")
        task_config = {"options": options, "checks": self.task_config.checks or []}
        ui_step = {
            "name": "Install {} {}".format(name, options["version"]),
            "kind": "managed",
            "is_required": True,
        }
        ui_step.update(step.task_config.get("ui_options", {}))
        ui_step.update(
            {
                "path": step.path,
                "step_num": str(step.step_num),
                "task_class": self.task_config.class_path,
                "task_config": task_config,
            }
        )
        return [ui_step]
