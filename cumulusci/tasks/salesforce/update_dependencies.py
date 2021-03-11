from cumulusci.salesforce_api.package_install import ManagedPackageInstallOptions
from cumulusci.core.tasks import BaseSalesforceTask
from cumulusci.core.dependencies.dependencies import (
    DependencyResolutionStrategy,
    ManagedPackageDependency,
    parse_dependencies,
    get_resolver_stack,
    get_static_dependencies,
)

from cumulusci.core.utils import process_bool_arg
from cumulusci.core.exceptions import TaskOptionsError


class UpdateDependencies(BaseSalesforceTask):
    name = "UpdateDependencies"
    task_options = {
        "dependencies": {
            "description": "List of dependencies to update. Defaults to project__dependencies. "
            "Each dependency is a dict with either 'github' set to a github repository URL "
            "or 'namespace' set to a Salesforce package namespace. "
            "GitHub dependencies may include 'tag' to install a particular git ref. "
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
        "allow_newer": {"description": "Deprecated. This option has no effect."},
        "security_type": {
            "description": "Which users to install packages for (FULL = all users, NONE = admins only)"
        },
        "prefer_2gp_from_release_branch": {
            "description": "If True and this build is on a release branch (feature/NNN, where NNN is an integer), "
            "or a child branch of a release branch, resolve GitHub managed package dependencies to 2GP builds present on "
            "a matching release branch on the dependency."
        },
        "resolution_strategy": {
            "description": "The name of a sequence of resolution_strategy (from project__dependency_resolutions) to apply to dynamic dependencies."
        },
    }

    def _init_options(self, kwargs):
        super(UpdateDependencies, self)._init_options(kwargs)
        self.dependencies = parse_dependencies(
            self.options.get("dependencies")
            or self.project_config.project__dependencies
        )

        self.options["security_type"] = self.options.get("security_type", "FULL")
        if self.options["security_type"] not in ("FULL", "NONE", "PUSH"):
            raise TaskOptionsError(
                f"Unsupported value for security_type: {self.options['security_type']}"
            )

        if "allow_uninstalls" in self.options or "allow_newer" in self.options:
            self.logger.warning(
                "The allow_uninstalls and allow_newer options for update_dependencies are no longer supported. "
                "CumulusCI will not attempt to uninstall packages and newer versions are always allowed."
            )

        if "ignore_dependencies" in self.options:
            if any(
                "github" not in dep and "namespace" not in dep
                for dep in self.options["ignore_dependencies"]
            ):
                raise TaskOptionsError(
                    "An invalid dependency was specified for ignore_dependencies."
                )

        # TODO: default strategy to preproduction if include_beta is True
        # Log warning.
        self.resolution_strategy = get_resolver_stack(
            self.project_config, self.options.get("resolution_strategy") or "production"
        )

        # Be backwards-compatible: if `include_beta` is set and False,
        # remove the `latest_beta` resolver from the stack.
        if (
            DependencyResolutionStrategy.STRATEGY_BETA_RELEASE_TAG
            in self.resolution_strategy
        ):
            if "include_beta" in self.options and not process_bool_arg(
                self.options.get("include_beta", False)
            ):
                self.resolution_strategy.remove(
                    DependencyResolutionStrategy.STRATEGY_BETA_RELEASE_TAG
                )

        # Likewise remove 2GP resolution strategies if prefer_2gp_from_release_branch
        # is explicitly False
        resolvers_2gp = [
            DependencyResolutionStrategy.STRATEGY_2GP_PREVIOUS_RELEASE_BRANCH,
            DependencyResolutionStrategy.STRATEGY_2GP_RELEASE_BRANCH,
            DependencyResolutionStrategy.STRATEGY_2GP_EXACT_BRANCH,
            DependencyResolutionStrategy.STRATEGY_BETA_RELEASE_TAG,
        ]

        if "prefer_2gp_from_release_branch" in self.options and not process_bool_arg(
            self.options.get("prefer_2gp_from_release_branch", False)
        ):
            self.resolution_strategy = [
                r for r in self.resolution_strategy if r not in resolvers_2gp
            ]

        unsafe_prod_resolvers = [
            *resolvers_2gp,
            DependencyResolutionStrategy.STRATEGY_BETA_RELEASE_TAG,
        ]
        if not self.org_config.scratch and any(
            r in self.resolution_strategy for r in unsafe_prod_resolvers
        ):
            self.logger.warning(
                "Target org is a persistent org; removing Beta resolvers. Consider selecting the `production` resolver stack."
            )
            self.resolution_strategy = [
                r for r in self.resolution_strategy if r not in unsafe_prod_resolvers
            ]

        if (
            "prefer_2gp_from_release_branch" in self.options
            or "include_beta" in self.options
        ):
            self.logger.warning(
                "The include_beta and prefer_2gp_from_release_branch options "
                "for update_dependencies are deprecated. Use resolution strategies instead."
            )

        self.install_options = ManagedPackageInstallOptions(
            security_type=self.options.get("security_type", "FULL"),
        )

    def _run_task(self):
        if not self.dependencies:
            self.logger.info("Project has no dependencies, doing nothing")
            return

        self.logger.info("Resolving dependencies...")
        dependencies = get_static_dependencies(
            self.dependencies,
            self.resolution_strategy,
            self.project_config,
            ignore_deps=self.options.get("ignore_dependencies"),
        )
        self.logger.info("Collected dependencies:")

        for d in dependencies:
            self.logger.info(f"    {d}")

        for d in dependencies:
            self._install_dependency(d)

        self.org_config.reset_installed_packages()

    def _install_dependency(self, dependency):
        if isinstance(dependency, ManagedPackageDependency):
            if dependency.version and "Beta" in dependency.version:
                version_string = dependency.version.split(" ")[0]
                beta = dependency.version.split(" ")[-1].strip(")")
                version = f"{version_string}b{beta}"
            else:
                version = dependency.version

            if (
                dependency.package_version_id
                and dependency.package_version_id
                not in self.org_config.installed_packages
            ) or (
                not self.org_config.has_minimum_package_version(
                    dependency.namespace,
                    version,
                )
            ):
                dependency.install(
                    self.project_config, self.org_config, self.install_options
                )
            else:
                self.logger.info(
                    f"{dependency} or a newer version is already installed; skipping."
                )
        else:
            dependency.install(self.project_config, self.org_config)

    def freeze(self, step):
        ui_options = self.task_config.config.get("ui_options", {})
        dependencies = get_static_dependencies(
            self.dependencies,
            self.resolution_strategy,
            self.project_config,
            ignore_deps=self.options.get("ignore_dependencies"),
        )

        steps = []
        for i, dependency in enumerate(dependencies, start=1):
            if isinstance(dependency, ManagedPackageDependency):
                kind = "managed"
            else:
                kind = "metadata"

            task_config = {
                "options": self.options.copy(),
                "checks": self.task_config.checks or [],
            }
            task_config["options"]["dependencies"] = [
                dependency.dict(exclude_none=True)
            ]
            ui_step = {"name": dependency.name, "kind": kind, "is_required": True}
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
