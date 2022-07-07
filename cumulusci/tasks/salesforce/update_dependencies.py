from typing import List

import click

from cumulusci.core.dependencies.dependencies import (
    Dependency,
    PackageNamespaceVersionDependency,
    PackageVersionIdDependency,
    parse_dependencies,
)
from cumulusci.core.dependencies.resolvers import (
    DependencyResolutionStrategy,
    dependency_filter_ignore_deps,
    get_resolver_stack,
    get_static_dependencies,
)
from cumulusci.core.exceptions import CumulusCIException, TaskOptionsError
from cumulusci.core.tasks import BaseSalesforceTask
from cumulusci.core.utils import process_bool_arg
from cumulusci.salesforce_api.package_install import (
    PACKAGE_INSTALL_TASK_OPTIONS,
    PackageInstallOptions,
)


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
        "prefer_2gp_from_release_branch": {
            "description": "If True and this build is on a release branch (feature/NNN, where NNN is an integer), "
            "or a child branch of a release branch, resolve GitHub managed package dependencies to 2GP builds present on "
            "a matching release branch on the dependency."
        },
        "resolution_strategy": {
            "description": "The name of a sequence of resolution_strategy (from project__dependency_resolutions) to apply to dynamic dependencies."
        },
        "packages_only": {
            "description": "Install only packaged dependencies. Ignore all unmanaged metadata. Defaults to False."
        },
        "interactive": {
            "description": "If True, stop after identifying all dependencies and output the package Ids that will be installed. Defaults to False."
        },
        "base_package_url_format": {
            "description": "If `interactive` is set to True, display package Ids using a format string ({} will be replaced with the package Id)."
        },
        **{k: v for k, v in PACKAGE_INSTALL_TASK_OPTIONS.items() if k != "password"},
    }

    def _init_options(self, kwargs):
        super(UpdateDependencies, self)._init_options(kwargs)
        self.dependencies = parse_dependencies(
            self.options.get("dependencies")
            or self.project_config.project__dependencies
        )

        self.options["packages_only"] = process_bool_arg(
            self.options.get("packages_only") or False
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

        # Backwards-compatibility: if include_beta is set and True,
        # use the include_beta resolution strategy.
        include_beta = None
        if "include_beta" in self.options and process_bool_arg(
            self.options["include_beta"]
        ):
            include_beta = "include_beta"

        self.resolution_strategy = get_resolver_stack(
            self.project_config,
            include_beta or self.options.get("resolution_strategy") or "production",
        )

        # Backwards-compatibility: if `include_beta` is set and False,
        # remove the `latest_beta` resolver from the stack.
        # Note: this applies even if the resolution strategy is set
        # to a beta-y strategy.
        if DependencyResolutionStrategy.BETA_RELEASE_TAG in self.resolution_strategy:
            if "include_beta" in self.options and not process_bool_arg(
                self.options["include_beta"]
            ):
                self.resolution_strategy.remove(
                    DependencyResolutionStrategy.BETA_RELEASE_TAG
                )

        # Likewise remove 2GP resolution strategies if prefer_2gp_from_release_branch
        # is explicitly False
        resolvers_2gp = [
            DependencyResolutionStrategy.COMMIT_STATUS_PREVIOUS_RELEASE_BRANCH,
            DependencyResolutionStrategy.COMMIT_STATUS_RELEASE_BRANCH,
            DependencyResolutionStrategy.COMMIT_STATUS_EXACT_BRANCH,
            DependencyResolutionStrategy.BETA_RELEASE_TAG,
        ]

        if "prefer_2gp_from_release_branch" in self.options and not process_bool_arg(
            self.options["prefer_2gp_from_release_branch"]
        ):
            self.resolution_strategy = [
                r for r in self.resolution_strategy if r not in resolvers_2gp
            ]

        unsafe_prod_resolvers = [
            *resolvers_2gp,
            DependencyResolutionStrategy.BETA_RELEASE_TAG,
        ]

        if (
            self.org_config
            and not self.org_config.scratch
            and any(r in self.resolution_strategy for r in unsafe_prod_resolvers)
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

        self.install_options = PackageInstallOptions.from_task_options(self.options)

        # Interactivity options
        self.options["interactive"] = process_bool_arg(
            self.options.get("interactive") or False
        )
        self.options["base_package_url_format"] = (
            self.options.get("base_package_url_format") or "{}"
        )

    def _filter_dependencies(self, deps: List[Dependency]) -> List[Dependency]:
        return [
            dep
            for dep in deps
            if isinstance(
                dep, (PackageNamespaceVersionDependency, PackageVersionIdDependency)
            )
            or not self.options["packages_only"]
        ]

    def _run_task(self):
        if not self.dependencies:
            self.logger.info("Project has no dependencies, doing nothing")
            return

        self.logger.info("Resolving dependencies...")
        if "ignore_dependencies" in self.options:
            filter_function = dependency_filter_ignore_deps(
                self.options["ignore_dependencies"]
            )
        else:
            filter_function = None

        dependencies = self._filter_dependencies(
            get_static_dependencies(
                self.project_config,
                dependencies=self.dependencies,
                strategies=self.resolution_strategy,
                filter_function=filter_function,
            )
        )
        self.logger.info("Collected dependencies:")

        for d in dependencies:
            if isinstance(d, PackageVersionIdDependency):
                desc = self.options["base_package_url_format"].format(d.version_id)
            elif isinstance(d, PackageNamespaceVersionDependency):
                if d.version_id:
                    desc = self.options["base_package_url_format"].format(d.version_id)
                else:
                    desc = ""
            else:
                desc = "unpackaged"

            desc = f" ({desc})" if desc else desc
            self.logger.info(f"    {d}{desc}")

        if self.options["interactive"]:
            if not click.confirm("Continue to install dependencies?", default=True):
                raise CumulusCIException("Dependency installation was canceled.")

        for d in dependencies:
            self._install_dependency(d)

        self.org_config.reset_installed_packages()

    def _install_dependency(self, dependency):
        if isinstance(
            dependency, (PackageNamespaceVersionDependency, PackageVersionIdDependency)
        ):
            dependency.install(
                self.project_config, self.org_config, self.install_options
            )
        else:
            dependency.install(self.project_config, self.org_config)

    def freeze(self, step):
        if self.options["interactive"]:
            raise CumulusCIException(
                "update_dependencies cannot be frozen when `interactive` is True."
            )

        ui_options = self.task_config.config.get("ui_options", {})
        if "ignore_dependencies" in self.options:
            filter_function = dependency_filter_ignore_deps(
                self.options["ignore_dependencies"]
            )
        else:
            filter_function = None

        dependencies = self._filter_dependencies(
            get_static_dependencies(
                self.project_config,
                dependencies=self.dependencies,
                strategies=self.resolution_strategy,
                filter_function=filter_function,
            )
        )

        steps = []
        for i, dependency in enumerate(dependencies, start=1):
            if isinstance(
                dependency,
                (PackageNamespaceVersionDependency, PackageVersionIdDependency),
            ):
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
