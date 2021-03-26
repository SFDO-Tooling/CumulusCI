from pydantic import ValidationError

from cumulusci.core.dependencies.dependencies import PackageInstallOptions
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.utils import process_bool_arg
from cumulusci.salesforce_api.package_install import (
    DEFAULT_PACKAGE_RETRY_OPTIONS,
    install_package_by_namespace_version,
    install_package_by_version_id,
)
from cumulusci.tasks.salesforce.BaseSalesforceApiTask import BaseSalesforceApiTask


class InstallPackageVersion(BaseSalesforceApiTask):
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
        "security_type": {
            "description": "Which users to install package for (FULL = all users, NONE = admins only)"
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        if "namespace" not in self.options:
            self.options["namespace"] = self.project_config.project__package__namespace
        version = self.options.get("version")

        # `name` is shown in the logs and in MetaDeploy
        # Populate a reasonable default. Note that if we're deploying a different package
        # than our own, we should not show the name of this repo's package.
        if "name" not in self.options:
            if (
                self.options["namespace"]
                == self.project_config.project__package__namespace
            ):
                self.options["name"] = (
                    self.project_config.project__package__name_managed
                    or self.project_config.project__package__name
                    or self.options["namespace"]
                )
            else:
                self.options["name"] = self.options["namespace"]

        self.retry_options = DEFAULT_PACKAGE_RETRY_OPTIONS.copy()
        if "retries" in self.options:
            self.retry_options["retries"] = self.options["retries"]
        if "retry_interval" in self.options:
            self.retry_options["retry_interval"] = self.options["retry_interval"]
        if "retry_interval_add" in self.options:
            self.retry_options["retry_interval_add"] = self.options[
                "retry_interval_add"
            ]

        # TODO: This should be centralized somewhere in the `dependencies` module,
        # along with the same code working with `sources`.
        # We're not using resolution strategies here - we could be,
        # and this task could be a thin layer on top of update_dependencies.
        if version == "latest":
            self.options["version"] = self.project_config.get_latest_version()
        elif version == "latest_beta":
            self.options["version"] = self.project_config.get_latest_version(beta=True)
        elif version == "previous":
            self.options["version"] = self.project_config.get_previous_version()

        # Ensure that this option is frozen in case the defaults ever change.
        self.options["security_type"] = self.options.get("security_type") or "FULL"
        try:
            self.install_options = PackageInstallOptions(
                activate_remote_site_settings=process_bool_arg(
                    self.options.get("activateRSS") or False
                ),
                password=self.options.get("password"),
                security_type=self.options["security_type"],
            )
        except ValidationError as e:
            raise TaskOptionsError(f"Invalid options: {e}")

    def _run_task(self):
        version = self.options["version"]
        self.logger.info(f"Installing {self.options['name']} {version}")

        if isinstance(version, str) and version.startswith("04t"):
            install_package_by_version_id(
                self.project_config,
                self.org_config,
                version,
                self.install_options,
                self.retry_options,
            )
        else:
            install_package_by_namespace_version(
                self.project_config,
                self.org_config,
                self.options["namespace"],
                version,
                self.install_options,
                self.retry_options,
            )

        self.org_config.reset_installed_packages()

    def freeze(self, step):
        options = self.options.copy()
        options["version"] = str(options["version"])
        name = options.pop("name")
        task_config = {"options": options, "checks": self.task_config.checks or []}
        ui_step = {
            "name": f"Install {name} {options['version']}",
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
                "source": step.project_config.source.frozenspec,
            }
        )
        return [ui_step]
