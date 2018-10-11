from builtins import str
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
from cumulusci.utils import zip_inject_namespace
from cumulusci.utils import zip_strip_namespace
from cumulusci.utils import zip_tokenize_namespace


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

        self.installed = self._get_installed()
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

    def _process_namespace_dependency(self, dependency, dependency_uninstalled=None):
        dependency_version = str(dependency["version"])

        if dependency["namespace"] in self.installed:
            # Some version is installed, check what to do
            installed_version = self.installed[dependency["namespace"]]
            if dependency_version == installed_version and not dependency_uninstalled:
                self.logger.info(
                    "  {}: version {} already installed".format(
                        dependency["namespace"], dependency_version
                    )
                )
                return

            required_version = LooseVersion(dependency_version)
            installed_version = LooseVersion(installed_version)

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

    def _install_dependency(self, dependency):
        if "zip_url" or "repo" in dependency:
            package_zip = None
            if "zip_url" in dependency:
                self.logger.info(
                    "Deploying unmanaged metadata from /{} of {}".format(
                        dependency["subfolder"], dependency["zip_url"]
                    )
                )
                package_zip = download_extract_zip(
                    dependency["zip_url"], subfolder=dependency.get("subfolder")
                )
            elif "repo" in dependency:
                self.logger.info(
                    "Deploying unmanaged metadata from /{} of {}".format(
                        dependency["subfolder"], dependency["repo"].full_name
                    )
                )
                package_zip = download_extract_github(
                    dependency["repo"],
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
                    package_zip = zip_tokenize_namespace(
                        package_zip,
                        namespace=dependency["namespace_tokenize"],
                        logger=self.logger,
                    )

                if dependency.get("namespace_inject"):
                    self.logger.info(
                        "Replacing namespace tokens with {}".format(
                            "{}__".format(dependency["namespace_inject"])
                        )
                    )
                    package_zip = zip_inject_namespace(
                        package_zip,
                        namespace=dependency["namespace_inject"],
                        managed=not dependency.get("unmanaged"),
                        namespaced_org=self.options["namespaced_org"],
                        logger=self.logger,
                    )

                if dependency.get("namespace_strip"):
                    self.logger.info(
                        "Removing namespace prefix {}__ from all files and filenames".format(
                            "{}__".format(dependency["namespace_strip"])
                        )
                    )
                    package_zip = zip_strip_namespace(
                        package_zip,
                        namespace=dependency["namespace_strip"],
                        logger=self.logger,
                    )

                package_zip = ZipfilePackageZipBuilder(package_zip)()

            elif "namespace" in dependency:
                self.logger.info(
                    "Installing {} version {}".format(
                        dependency["namespace"], dependency["version"]
                    )
                )
                package_zip = InstallPackageZipBuilder(
                    dependency["namespace"], dependency["version"]
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
