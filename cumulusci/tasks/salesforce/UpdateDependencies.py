import functools
from distutils.version import LooseVersion

from cumulusci.core.utils import process_bool_arg
from cumulusci.core.config import ScratchOrgConfig
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.salesforce_api.metadata import ApiDeploy
from cumulusci.salesforce_api.metadata import ApiRetrieveInstalledPackages
from cumulusci.salesforce_api.package_zip import InstallPackageZipBuilder
from cumulusci.salesforce_api.package_zip import UninstallPackageZipBuilder
from cumulusci.salesforce_api.package_zip import ZipfilePackageZipBuilder
from cumulusci.tasks.salesforce import BaseSalesforceMetadataApiTask
from cumulusci.utils import download_extract_zip
from cumulusci.utils import download_extract_github
from cumulusci.utils import inject_namespace
from cumulusci.utils import strip_namespace
from cumulusci.utils import process_text_in_zipfile
from cumulusci.utils import tokenize_namespace


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
        "namespaced_org": {
            "description": "If True, the changes namespace token injection on any dependencies so tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org."
        },
        "purge_on_delete": {
            "description": "Sets the purgeOnDelete option for the deployment. Defaults to True"
        },
        "include_beta": {
            "description": "Install the most recent release, even if beta. Defaults to False."
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
    }

    def _init_options(self, kwargs):
        super(UpdateDependencies, self)._init_options(kwargs)
        self.options["purge_on_delete"] = process_bool_arg(
            self.options.get("purge_on_delete", True)
        )
        self.options["namespaced_org"] = process_bool_arg(
            self.options.get("namespaced_org", False)
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

    def _run_task(self):
        if not self.options["dependencies"]:
            self.logger.info("Project has no dependencies, doing nothing")
            return

        if self.options["include_beta"] and not isinstance(
            self.org_config, ScratchOrgConfig
        ):
            raise TaskOptionsError(
                "Target org must be a scratch org when `include_beta` is true."
            )

        self.logger.info("Preparing static dependencies map")
        dependencies = self.project_config.get_static_dependencies(
            self.options["dependencies"], include_beta=self.options["include_beta"]
        )

        self.installed = None
        self.uninstall_queue = []
        self.install_queue = []

        self.logger.info("Dependencies:")
        for line in self.project_config.pretty_dependencies(dependencies):
            self.logger.info(line)

        self._process_dependencies(dependencies)

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
        if "zip_url" or "repo_name" in dependency:
            package_zip = None
            if "zip_url" in dependency:
                self.logger.info(
                    "Deploying unmanaged metadata from /{} of {}".format(
                        dependency["subfolder"], dependency["zip_url"]
                    )
                )
                package_zip = self._download_extract_zip(
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
                package_zip = self._download_extract_github(
                    gh_for_repo,
                    dependency["repo_owner"],
                    dependency["repo_name"],
                    dependency["subfolder"],
                    ref=dependency.get("ref"),
                )

            if package_zip:
                if dependency.get("namespace_tokenize"):
                    self.logger.info(
                        "Replacing namespace prefix {}__ in files and filenames with namespace token strings".format(
                            "{}__".format(dependency["namespace_tokenize"])
                        )
                    )
                    package_zip = process_text_in_zipfile(
                        package_zip,
                        functools.partial(
                            tokenize_namespace,
                            namespace=dependency["namespace_tokenize"],
                            logger=self.logger,
                        ),
                    )

                if dependency.get("namespace_inject"):
                    self.logger.info(
                        "Replacing namespace tokens with {}".format(
                            "{}__".format(dependency["namespace_inject"])
                        )
                    )
                    package_zip = process_text_in_zipfile(
                        package_zip,
                        functools.partial(
                            inject_namespace,
                            namespace=dependency["namespace_inject"],
                            managed=not dependency.get("unmanaged"),
                            namespaced_org=self.options["namespaced_org"],
                            logger=self.logger,
                        ),
                    )

                if dependency.get("namespace_strip"):
                    self.logger.info(
                        "Removing namespace prefix {}__ from all files and filenames".format(
                            "{}__".format(dependency["namespace_strip"])
                        )
                    )
                    package_zip = process_text_in_zipfile(
                        package_zip,
                        functools.partial(
                            strip_namespace,
                            namespace=dependency["namespace_strip"],
                            logger=self.logger,
                        ),
                    )

                package_zip = ZipfilePackageZipBuilder(package_zip)()

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

        api = self.api_class(
            self, package_zip, purge_on_delete=self.options["purge_on_delete"]
        )
        return api()

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
            self.options["dependencies"], include_beta=self.options["include_beta"]
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
