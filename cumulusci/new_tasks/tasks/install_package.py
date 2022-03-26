from logging import Logger
from typing import Literal, Optional, Union

import click
import pydantic

from cumulusci.core.config import BaseProjectConfig, OrgConfig
from cumulusci.core.dependencies.dependencies import (
    GitHubDynamicDependency,
    PackageNamespaceVersionDependency,
    PackageVersionIdDependency,
)
from cumulusci.core.dependencies.resolvers import get_resolver_stack
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.github import find_previous_release
from cumulusci.new_tasks.registry import task
from cumulusci.salesforce_api.package_install import PackageInstallOptions


class BaseInstallPackageOptions(pydantic.BaseModel):
    # Pydantic's bool parsing may not be *exactly* the same as parse_bool_arg()
    interactive: bool = False
    base_package_url_format: str = "{}"
    password_env_name: Optional[str]


class InstallPackageOptions(
    BaseInstallPackageOptions, PackageInstallOptions, pydantic.BaseModel
):
    version: pydantic.constr(regex=r"04t[a-zA-Z0-9]{12,15}")  # noqa: F722
    name: Optional[str]
    version_number: Optional[str]


class InstallPackageOptionsNS(
    BaseInstallPackageOptions, PackageInstallOptions, pydantic.BaseModel
):
    version: pydantic.constr(regex=r"[0-9]+(\.[0-9]+)+")  # noqa: F722
    namespace: str
    name: Optional[str]
    version_id: Optional[str]


Options = Union[InstallPackageOptions, InstallPackageOptionsNS]


class InstallPackageDynamicOptions(
    BaseInstallPackageOptions, PackageInstallOptions, pydantic.BaseModel
):
    version: Literal["latest", "latest_beta", "previous"]

    # repo is a fixture
    # freeze() must return one of the classes in `options_models` below.
    def freeze(self, project: BaseProjectConfig) -> Options:
        github = f"https://github.com/{project.repo_owner}/{project.repo_name}"

        dependency = None
        if self.version in ["latest", "latest_beta"]:
            strategy = "include_beta" if self.version == "latest_beta" else "production"
            dependency = GitHubDynamicDependency(github=github)
            dependency.resolve(project, get_resolver_stack(project, strategy))
        elif self.version == "previous":
            release = find_previous_release(
                project.get_repo(),
                project.project__git__prefix_release,
            )
            dependency = GitHubDynamicDependency(github=github, tag=release.tag_name)
            dependency.resolve(
                project,
                get_resolver_stack(project, "production"),
            )

        if dependency:
            if dependency.package_dependency:
                # Handle 2GP and 1GP releases in a backwards-compatible way.
                if isinstance(
                    dependency.package_dependency, PackageNamespaceVersionDependency
                ):
                    opts = self.dict() | {
                        "version": dependency.package_dependency.version,
                        "version_id": dependency.package_dependency.version_id,
                        "namespace": dependency.package_dependency.namespace,
                    }

                    return InstallPackageOptionsNS(
                        **opts,
                    )
                elif isinstance(
                    dependency.package_dependency, PackageVersionIdDependency
                ):
                    opts = self.dict() | {
                        "version": dependency.package_dependency.version_id,
                        "version_number": dependency.package_dependency.version_number,
                    }
                    return InstallPackageOptions(
                        **opts,
                    )

        raise CumulusCIException(
            f"The release for {self.version} does not identify a package version."
        )


@task
class InstallPackage:
    """Do the thing"""

    options: Options

    class Meta:
        # CumulusCI will try to parse options with each class in order.
        # This allows for versioned backwards compatibility.
        # Dynamic options models will be tried first.
        # Union types are allowable for multiple legal options
        options_models = [InstallPackageOptions, InstallPackageOptionsNS]
        dynamic_options_models = [InstallPackageDynamicOptions]
        return_model = None
        task_id = "cumulusci.new_tasks.InstallPackage"
        idempotent = True
        name = "Install Package"

    def __init__(self, options: Options):
        self.options = options

    def run(
        self,
        org: OrgConfig,
        logger: Logger,
        project: BaseProjectConfig,
    ) -> None:

        dep = None
        if isinstance(self.options, InstallPackageOptions):
            dep = PackageVersionIdDependency(
                version_id=self.options.version,
                package_name=self.options.name,
                version_number=self.options.version_number,
                password_env_name=self.options.password_env_name,
            )
        elif isinstance(self.options, InstallPackageOptionsNS):
            dep = PackageNamespaceVersionDependency(
                namespace=self.options.namespace,
                version=self.options.version,
                package_name=self.options.name,
                version_id=self.options.version_id,
                password_env_name=self.options.password_env_name,
            )
        else:
            # pragma: no cover
            # unreachable
            raise CumulusCIException("Invalid options")

        if self.options.interactive:
            if dep.version_id:
                package_desc = self.options.base_package_url_format.format(
                    dep.version_id
                )
            else:
                package_desc = str(dep)
            logger.info("Package to install: {}".format(package_desc))
            if not click.confirm("Continue to install dependencies?", default=True):
                raise CumulusCIException("Dependency installation was canceled.")

        dep.install(project, org, self.options)  # todo: retry options

        org.reset_installed_packages()
