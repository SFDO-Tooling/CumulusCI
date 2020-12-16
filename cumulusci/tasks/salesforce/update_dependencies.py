from distutils.version import LooseVersion

from cumulusci.core.utils import process_bool_arg
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.salesforce_api.metadata import ApiDeploy
from cumulusci.salesforce_api.metadata import ApiRetrieveInstalledPackages
from cumulusci.salesforce_api.package_install import install_package_version
from cumulusci.salesforce_api.package_zip import InstallPackageZipBuilder
from cumulusci.salesforce_api.package_zip import MetadataPackageZipBuilder
from cumulusci.salesforce_api.package_zip import UninstallPackageZipBuilder
from cumulusci.tasks.salesforce.BaseSalesforceMetadataApiTask import (
    BaseSalesforceMetadataApiTask,
)
from cumulusci.utils import download_extract_zip
from cumulusci.utils import download_extract_github


class UpdateDependencies(BaseSalesforceMetadataApiTask):
    api_class = ApiDeploy
    name = "UpdateDependencies"
    task_options = {
        "dependencies": {
            "description": "List of dependencies to update. Defaults to project__dependencies. "
            "Each dependency is a dict with either 'github' set to a github repository URL "
            "or 'namespace' set to a Salesforce package namespace. "
            "Github dependencies may include 'tag' to install a particular git ref. "
            "Package dependencies may include 'version' to install a particular version."
        },
        "ignore_dependencies": {
            "description": "List of dependencies to be ignored, including if they are present as transitive "
            "dependencies. Dependencies can be specified using the 'github' or 'namespace' keys (all other keys "
            "are not used). Note that this can cause installations to fail if required prerequisites are not available."
        },
        "purge_on_delete": {
            "description": "Sets the purgeOnDelete option for the deployment. Defaults to True"
        },
        "include_beta": {
            "description": "Install the most recent release, even if beta. Defaults to False. "
            "This option is only supported for scratch orgs, "
            "to avoid installing a package that can't be upgraded in persistent orgs."
        },
        "allow_newer": {
            "description": "If the org already has a newer release, use it. Defaults to True."
        },
        "allow_uninstalls": {
            "description": "Allow uninstalling a beta release or newer final release "
            "in order to install the requested version. Defaults to False. "
            "Warning: Enabling this may destroy data."
        },
        "security_type": {
            "description": "Which users to install packages for (FULL = all users, NONE = admins only)"
        },
        "prefer_2gp_from_release_branch": {
            "description": "If True and this build is on a release branch (feature/NNN, where NNN is an integer), "
            "or a child branch of a release branch, resolve GitHub managed package dependencies to 2GP builds present on "
            "a matching release branch on the dependency."
        },
        "2gp_context": {
            "description": "The commit status where CumulusCI should locate a 2GP version id when using prefer_2gp_from_release_branch. "
            "This option is required when prefer_2gp_from_release_branch is True."
        },
    }

    def _init_options(self, kwargs):
        super(UpdateDependencies, self)._init_options(kwargs)
        self.options["purge_on_delete"] = process_bool_arg(
            self.options.get("purge_on_delete", True)
        )
        self.options["include_beta"] = process_bool_arg(
            self.options.get("include_beta", False)
        )
        self.options["dependencies"] = (
            self.options.get("dependencies")
            or self.project_config.project__dependencies
        )
        self.options["allow_newer"] = process_bool_arg(
            self.options.get("allow_newer", True)
        )
        self.options["allow_uninstalls"] = process_bool_arg(
            self.options.get("allow_uninstalls", False)
        )
        self.options["security_type"] = self.options.get("security_type", "FULL")
        if self.options["security_type"] not in ("FULL", "NONE", "PUSH"):
            raise TaskOptionsError(
                f"Unsupported value for security_type: {self.options['security_type']}"
            )
        self.options["prefer_2gp_from_release_branch"] = process_bool_arg(
            self.options.get("prefer_2gp_from_release_branch", False)
        )

        if (
            self.options["prefer_2gp_from_release_branch"]
            and "2gp_context" not in self.options
        ):
            raise TaskOptionsError(
                "Setting the prefer_2gp_from_release_branch option requires a 2gp_context."
            )

        if "ignore_dependencies" in self.options:
            if any(
                "github" not in dep and "namespace" not in dep
                for dep in self.options["ignore_dependencies"]
            ):
                raise TaskOptionsError(
                    "An invalid dependency was specified for ignore_dependencies."
                )

        if (
            self.org_config
            and self.options["include_beta"]
            and not self.org_config.scratch
        ):
            self.logger.warning(
                "The `include_beta` option is enabled but this not a scratch org.\n"
                "Setting `include_beta` to False to avoid installing beta package versions in a persistent org."
            )
            self.options["include_beta"] = False

    def _run_task(self):
        if not self.options["dependencies"]:
            self.logger.info("Project has no dependencies, doing nothing")
            return

        self.logger.info("Preparing static dependencies map")
        dependencies = self.project_config.get_static_dependencies(
            self.options["dependencies"],
            include_beta=self.options["include_beta"],
            ignore_deps=self.options.get("ignore_dependencies"),
            match_release_branch=self.options["prefer_2gp_from_release_branch"],
            context_2gp=self.options.get("2gp_context"),
        )

        self.installed = None
        self.uninstall_queue = []
        self.install_queue = []

        self.logger.info("Dependencies:")
        for line in self.project_config.pretty_dependencies(dependencies):
            self.logger.info(line)

        self._process_dependencies(dependencies)
        installs = []
        for dep in self.install_queue:
            if dep not in installs:
                installs.append(dep)

        self.install_queue = installs

        # Reverse the uninstall queue
        self.uninstall_queue.reverse()

        self._uninstall_dependencies()
        self._install_dependencies()
        self.org_config.reset_installed_packages()

    def _process_dependencies(self, dependencies):
        for dependency in dependencies:
            # Process child dependencies
            dependency_uninstalled = False
            subdependencies = dependency.get("dependencies")
            if subdependencies:
                count_uninstall = len(self.uninstall_queue)
                self._process_dependencies(subdependencies)
                if count_uninstall != len(self.uninstall_queue):
                    dependency_uninstalled = True

            # Process namespace dependencies (managed packages)
            if "namespace" in dependency:
                self._process_namespace_dependency(dependency, dependency_uninstalled)
            else:
                # zip_url or repo dependency
                self.install_queue.append(dependency)

        if self.uninstall_queue and not self.options["allow_uninstalls"]:
            raise TaskOptionsError(
                "Updating dependencies would require uninstalling these packages "
                "but uninstalls are not enabled: {}".format(
                    ", ".join(dep["namespace"] for dep in self.uninstall_queue)
                )
            )

    def _process_namespace_dependency(self, dependency, dependency_uninstalled=None):
        dependency_version = str(dependency["version"])

        if self.installed is None:
            self.installed = self._get_installed()

        if dependency["namespace"] in self.installed:
            # Some version is installed, check what to do
            installed_version = self.installed[dependency["namespace"]]
            required_version = LooseVersion(dependency_version)
            installed_version = LooseVersion(installed_version)

            if installed_version > required_version and self.options["allow_newer"]:
                # Avoid downgrading if allow_newer = True
                required_version = installed_version

            if required_version == installed_version and not dependency_uninstalled:
                self.logger.info(
                    "  {}: version {} already installed".format(
                        dependency["namespace"], dependency_version
                    )
                )
                return

            if "Beta" in installed_version.vstring:
                # Always uninstall Beta versions if required is different
                self.uninstall_queue.append(dependency)
                self.logger.info(
                    "  {}: Uninstall {} to upgrade to {}".format(
                        dependency["namespace"],
                        installed_version,
                        dependency["version"],
                    )
                )
            elif dependency_uninstalled:
                # If a dependency of this one needs to be uninstalled, always uninstall the package
                self.uninstall_queue.append(dependency)
                self.logger.info(
                    "  {}: Uninstall and Reinstall to allow downgrade of dependency".format(
                        dependency["namespace"]
                    )
                )
            elif required_version < installed_version:
                # Uninstall to downgrade
                self.uninstall_queue.append(dependency)
                self.logger.info(
                    "  {}: Downgrade from {} to {} (requires uninstall/install)".format(
                        dependency["namespace"],
                        installed_version,
                        dependency["version"],
                    )
                )
            else:
                self.logger.info(
                    "  {}: Upgrade from {} to {}".format(
                        dependency["namespace"],
                        installed_version,
                        dependency["version"],
                    )
                )
            self.install_queue.append(dependency)
        else:
            # Just a regular install
            self.logger.info(
                "  {}: Install version {}".format(
                    dependency["namespace"], dependency["version"]
                )
            )
            self.install_queue.append(dependency)

    def _get_installed(self):
        # @@@ use org_config.installed_packages instead
        self.logger.info("Retrieving list of packages from target org")
        api = ApiRetrieveInstalledPackages(self)
        return api()

    def _uninstall_dependencies(self):
        for dependency in self.uninstall_queue:
            self._uninstall_dependency(dependency)

    def _install_dependencies(self):
        for dependency in self.install_queue:
            self._install_dependency(dependency)

    # hooks for tests
    _download_extract_github = staticmethod(download_extract_github)
    _download_extract_zip = staticmethod(download_extract_zip)

    def _install_dependency(self, dependency):
        package_zip = None

        zip_src = None
        if "zip_url" in dependency:
            self.logger.info(
                "Deploying unmanaged metadata from /{} of {}".format(
                    dependency.get("subfolder") or "", dependency["zip_url"]
                )
            )
            zip_src = self._download_extract_zip(
                dependency["zip_url"], subfolder=dependency.get("subfolder")
            )
        elif "repo_name" in dependency:
            self.logger.info(
                "Deploying unmanaged metadata from /{} of {}/{}".format(
                    dependency["subfolder"],
                    dependency["repo_owner"],
                    dependency["repo_name"],
                )
            )
            gh_for_repo = self.project_config.get_github_api(
                dependency["repo_owner"], dependency["repo_name"]
            )
            zip_src = self._download_extract_github(
                gh_for_repo,
                dependency["repo_owner"],
                dependency["repo_name"],
                dependency["subfolder"],
                ref=dependency.get("ref"),
            )

        if zip_src:
            # determine whether to inject namespace prefixes or not
            options = dependency.copy()
            if "unmanaged" not in options:
                namespace = options.get("namespace_inject")
                options["unmanaged"] = (
                    not namespace
                ) or namespace not in self.org_config.installed_packages

            package_zip = MetadataPackageZipBuilder.from_zipfile(
                zip_src, options=dependency, logger=self.logger
            ).as_base64()
        elif "namespace" in dependency:
            self.logger.info(
                "Installing {} version {}".format(
                    dependency["namespace"], dependency["version"]
                )
            )
            package_zip = InstallPackageZipBuilder(
                dependency["namespace"],
                dependency["version"],
                securityType=self.options["security_type"],
            )()

        if package_zip:
            api = self.api_class(
                self, package_zip, purge_on_delete=self.options["purge_on_delete"]
            )
            return api()
        elif "version_id" in dependency:
            self.logger.info(f"Installing {dependency['version_id']}")
            install_package_version(self.project_config, self.org_config, dependency)
        else:
            raise TaskOptionsError(f"Could not find package for {dependency}")

    def _uninstall_dependency(self, dependency):
        self.logger.info("Uninstalling {}".format(dependency["namespace"]))
        package_zip = UninstallPackageZipBuilder(
            dependency["namespace"], self.project_config.project__package__api_version
        )
        api = self.api_class(
            self, package_zip(), purge_on_delete=self.options["purge_on_delete"]
        )
        return api()

    def freeze(self, step):
        ui_options = self.task_config.config.get("ui_options", {})
        dependencies = self.project_config.get_static_dependencies(
            self.options["dependencies"],
            include_beta=self.options["include_beta"],
            ignore_deps=self.options.get("ignore_dependencies"),
        )
        steps = []
        for i, dependency in enumerate(self._flatten(dependencies), start=1):
            name = dependency.pop("name", None)
            if "namespace" in dependency:
                kind = "managed"
                name = name or "Install {} {}".format(
                    dependency["namespace"], dependency["version"]
                )
            else:
                kind = "metadata"
                name = name or "Deploy {}".format(dependency["subfolder"])
            task_config = {
                "options": self.options.copy(),
                "checks": self.task_config.checks or [],
            }
            task_config["options"]["dependencies"] = [dependency]
            ui_step = {"name": name, "kind": kind, "is_required": True}
            ui_step.update(ui_options.get(i, {}))
            ui_step.update(
                {
                    "path": "{}.{}".format(step.path, i),
                    "step_num": "{}.{}".format(step.step_num, i),
                    "task_class": self.task_config.class_path,
                    "task_config": task_config,
                    "source": step.project_config.source.frozenspec,
                }
            )
            steps.append(ui_step)
        return steps

    def _flatten(self, dependencies):
        result = []
        for dependency in dependencies:
            subdeps = dependency.pop("dependencies", [])
            for subdep in self._flatten(subdeps):
                if subdep not in result:
                    result.append(subdep)
            if dependency not in result:
                result.append(dependency)
        return result
