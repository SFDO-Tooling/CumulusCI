from distutils.version import LooseVersion
from cumulusci.core.exceptions import PackageInstallError
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.utils import process_bool_arg
from cumulusci.salesforce_api.exceptions import MetadataApiError
from cumulusci.salesforce_api.package_zip import InstallPackageZipBuilder
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.tasks.salesforce import Deploy
from simple_salesforce.exceptions import SalesforceMalformedRequest


class InstallPackageVersion(BaseSalesforceApiTask, Deploy):
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
        "name_conflict_resolution": {
            "description": "Only for package version id based installation, sets the "
            "value of NameConflictResultion.  Valid values are Block or RenameMetadata "
            "and Block is the default.",
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

    def _init_task(self):
        BaseSalesforceApiTask._init_task(self)
        super()._init_task()

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
        elif version == "latest_beta":
            self.options["version"] = self.project_config.get_latest_version(beta=True)
        elif version == "previous":
            self.options["version"] = self.project_config.get_previous_version()
        self.options["activateRSS"] = process_bool_arg(self.options.get("activateRSS"))
        self.options["security_type"] = self.options.get("security_type", "FULL")
        if self.options["security_type"] not in ("FULL", "NONE", "PUSH"):
            raise TaskOptionsError(
                f"Unsupported value for security_type: {self.options['security_type']}"
            )

    def _get_api(self, path=None):
        package_zip = InstallPackageZipBuilder(
            namespace=self.options["namespace"],
            version=self.options["version"],
            activateRSS=self.options["activateRSS"],
            password=self.options.get("password"),
            securityType=self.options.get("security_type", "FULL"),
        )
        return self.api_class(self, package_zip(), purge_on_delete=False)

    def _run_task(self):
        self.logger.info(
            f"Installing {self.options['name']} release: {self.options['version']}"
        )
        self._retry()
        self.org_config.reset_installed_packages()

    def _is_version_id(self, version):
        return (
            version
            and not isinstance(version, LooseVersion)
            and version.lower().startswith("04t")
        )

    def _try(self):
        if self._is_version_id(self.options["version"]):
            # If version is a 04t package version id, install via PackageInstallRequest
            self._install_package_version()
        else:
            # Install via Metadata API deployment of InstalledPackage type
            api = self._get_api()
            api()

    def _install_package_version(self):
        PackageInstallRequest = self._get_tooling_object("PackageInstallRequest")
        self.request = PackageInstallRequest.create(
            {
                "EnableRss": self.options["activateRSS"],
                "NameConflictResolution": self.options.get(
                    "name_conflict_resolution", "Block"
                ),
                "Password": self.options.get("password"),
                "SecurityType": self.options["security_type"],
                "SubscriberPackageVersionKey": self.options["version"],
            }
        )
        self._poll()

    def _poll_action(self):
        request_id = self.request["id"]
        res = self.tooling.query(
            f"SELECT Errors, Status FROM PackageInstallRequest WHERE Id='{request_id}'"
        )
        request = res["records"][0]
        if request["Status"] == "IN_PROGRESS":
            self.logger.info("In Progress")
            return

        if request["Status"] == "SUCCESS":
            self.logger.info("Success")
            self.poll_complete = True
            return

        if request["Status"] == "ERROR":
            self.logger.error("Error installing package")
            self.poll_complete = True
            raise PackageInstallError(request["Errors"])

    def _is_retry_valid(self, e):
        if isinstance(e, MetadataApiError) and (
            "This package is not yet available" in str(e)
            or "InstalledPackage version number" in str(e)
        ):
            return True
        if (
            self._is_version_id(self.options["version"])
            and isinstance(e, SalesforceMalformedRequest)
            and e.content[0]["message"] == "invalid cross reference id"
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
                "source": step.project_config.source.frozenspec,
            }
        )
        return [ui_step]
