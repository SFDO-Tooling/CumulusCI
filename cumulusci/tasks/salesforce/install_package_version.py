from cumulusci.core.dependencies.dependencies import (
    GitHubDynamicDependency,
    PackageInstallOptions,
    PackageNamespaceVersionDependency,
    PackageVersionIdDependency,
)
from cumulusci.core.dependencies.resolvers import get_resolver_stack
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.github import find_previous_release
from cumulusci.salesforce_api.package_install import (
    DEFAULT_PACKAGE_RETRY_OPTIONS,
    PACKAGE_INSTALL_TASK_OPTIONS,
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
        "version_number": {
            "description": "If installing a package using an 04t version Id, display this version "
            "number to the user and in logs. Has no effect otherwise."
        },
        "activateRSS": {
            "description": "Deprecated. Use activate_remote_site_settings instead."
        },
        "retries": {"description": "Number of retries (default=5)"},
        "retry_interval": {
            "description": "Number of seconds to wait before the next retry (default=5),"
        },
        "retry_interval_add": {
            "description": "Number of seconds to add before each retry (default=30),"
        },
        **PACKAGE_INSTALL_TASK_OPTIONS,
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
            if isinstance(version, str) and version.startswith("04t"):
                self.options["name"] = "Package"
            elif (
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

        dependency = None
        github = f"https://github.com/{self.project_config.repo_owner}/{self.project_config.repo_name}"

        if version in ["latest", "latest_beta"]:
            strategy = "include_beta" if version == "latest_beta" else "production"
            dependency = GitHubDynamicDependency(github=github)
            dependency.resolve(
                self.project_config, get_resolver_stack(self.project_config, strategy)
            )
        elif version == "previous":
            release = find_previous_release(
                self.project_config.get_repo(),
                self.project_config.project__git__prefix_release,
            )
            dependency = GitHubDynamicDependency(github=github, tag=release.tag_name)
            dependency.resolve(
                self.project_config,
                get_resolver_stack(self.project_config, "production"),
            )
        elif isinstance(version, (float, int)):
            self.logger.warning(
                f"The `version` option is specified as a number ({version}). "
                "Please specify as a quoted string to avoid ambiguous results."
            )
            self.options["version"] = str(version)

        if dependency:
            if dependency.package_dependency:
                # Handle 2GP and 1GP releases in a backwards-compatible way.
                if isinstance(
                    dependency.package_dependency, PackageNamespaceVersionDependency
                ):
                    self.options["version"] = dependency.package_dependency.version
                elif isinstance(
                    dependency.package_dependency, PackageVersionIdDependency
                ):
                    self.options["version"] = dependency.package_dependency.version_id
                    self.options[
                        "version_number"
                    ] = dependency.package_dependency.version_number
            else:
                raise CumulusCIException(
                    f"The release for {version} does not identify a package version."
                )

        if "activateRSS" in self.options:
            self.logger.warning(
                "The activateRSS option is deprecated. Please use activate_remote_site_settings."
            )
            self.options["activate_remote_site_settings"] = self.options["activateRSS"]
            del self.options["activateRSS"]

        self.install_options = PackageInstallOptions.from_task_options(self.options)

    def _run_task(self):
        version = self.options["version"]

        if version.startswith("04t"):
            dep = PackageVersionIdDependency(
                version_id=version, package_name=self.options["name"]
            )
            if "version_number" in self.options:
                dep.version_number = self.options["version_number"]
            dep.install(
                self.project_config,
                self.org_config,
                self.install_options,
                self.retry_options,
            )
        else:
            dep = PackageNamespaceVersionDependency(
                namespace=self.options["namespace"],
                version=version,
                package_name=self.options["name"],
            )
            dep.install(
                self.project_config,
                self.org_config,
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
            "name": f"Install {name} {options.get('version_number') or options['version']}",
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
