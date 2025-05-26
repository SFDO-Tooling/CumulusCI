import functools
import io
import logging
import re
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from github3.exceptions import NotFoundError
from github3.git import Tag
from github3.repos.repo import Repository
from pydantic import root_validator, validator
from pydantic.networks import AnyUrl

import cumulusci.core.dependencies.base as base_dependency
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.dependencies.dependencies import parse_dependency
from cumulusci.core.exceptions import DependencyResolutionError
from cumulusci.core.versions import PackageType
from cumulusci.utils import download_extract_github_from_repo
from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load

PACKAGE_TYPE_RE = re.compile(r"^package_type: (.*)$", re.MULTILINE)
VERSION_ID_RE = re.compile(r"^version_id: (04t[a-zA-Z0-9]{12,15})$", re.MULTILINE)

logger = logging.getLogger(__name__)

VCS_GITHUB = "github"


def get_repo(github: str, context: BaseProjectConfig) -> Repository:
    try:
        repo = context.get_repo_from_url(github)
    except NotFoundError:
        repo = None

    if repo is None:
        raise DependencyResolutionError(
            f"We are unable to find the repository at {github}. Please make sure the URL is correct, that your GitHub user has read access to the repository, and that your GitHub personal access token includes the “repo” scope."
        )
    return repo


@functools.lru_cache(50)
def get_remote_project_config(repo: Repository, ref: str) -> BaseProjectConfig:
    contents = repo.file_contents("cumulusci.yml", ref=ref)
    contents_io = io.StringIO(contents.decoded.decode("utf-8"))
    contents_io.url = f"cumulusci.yml from {repo.owner}/{repo.name}"  # for logging
    return BaseProjectConfig(None, cci_safe_load(contents_io))


def get_package_data(config: BaseProjectConfig):
    return BaseProjectConfig.get_package_data(config)


def get_package_details_from_tag(
    tag: Tag,
) -> Tuple[Optional[str], Optional[PackageType]]:
    message = tag.message
    version_id = VERSION_ID_RE.search(message)
    if version_id:
        version_id = version_id.group(1)
    package_type = PACKAGE_TYPE_RE.search(message)
    if package_type:
        package_type = PackageType(package_type.group(1))

    return version_id, package_type


def _validate_github_parameters(values):
    if values.get("repo_owner") or values.get("repo_name"):
        logger.warning(
            "The repo_name and repo_owner keys are deprecated. Please use the github key."
        )

    assert (
        values.get("url")
        or values.get("github")
        or (values.get("repo_owner") and values.get("repo_name"))
    ), "Must specify `github` or `repo_owner` and `repo_name`"

    # Populate the `github` property if not already populated.
    if not values.get("github") and values.get("repo_name"):
        values[
            "github"
        ] = f"https://github.com/{values['repo_owner']}/{values['repo_name']}"
        values.pop("repo_owner")
        values.pop("repo_name")

    return values


class GitHubDependencyPin(base_dependency.DependencyPin):
    """Model representing a request to pin a GitHub dependency to a specific tag"""

    github: str
    tag: str

    def can_pin(self, d: "base_dependency.DynamicDependency") -> bool:
        return isinstance(d, BaseGitHubDependency) and d.github == self.github

    def pin(self, d: "BaseGitHubDependency", context: BaseProjectConfig):
        from cumulusci.core.dependencies.resolvers import (  # Circular imports
            GitHubTagResolver,
        )

        if d.tag and d.tag != self.tag:
            raise DependencyResolutionError(
                f"A pin is specified for {self.github}, but the dependency already has a tag specified."
            )
        d.tag = self.tag
        d.ref, d.package_dependency = GitHubTagResolver().resolve(d, context)


GitHubDependencyPin.update_forward_refs()


class BaseGitHubDependency(base_dependency.DynamicDependency, ABC):
    """Base class for dynamic dependencies that reference a GitHub repo."""

    pin_class = GitHubDependencyPin
    vcs: str = VCS_GITHUB

    github: Optional[AnyUrl] = None

    repo_owner: Optional[str] = None  # Deprecated - use full URL
    repo_name: Optional[str] = None  # Deprecated - use full URL

    tag: Optional[str] = None
    ref: Optional[str] = None

    @property
    @abstractmethod
    def is_unmanaged(self):
        pass

    @property
    def is_resolved(self):
        return bool(self.ref)

    @root_validator
    def check_deprecated_fields(cls, values):
        if values.get("repo_owner") or values.get("repo_name"):
            logger.warning(
                "The dependency keys `repo_owner` and `repo_name` are deprecated. Use the full repo URL with the `github` key instead."
            )
        return values

    @root_validator
    def check_complete(cls, values):
        assert values["ref"] is None, "Must not specify `ref` at creation."

        return _validate_github_parameters(values)

    @root_validator(pre=True)
    def sync_github_and_url(cls, values):
        # If only github is provided, set url to github
        if values.get("github") and not values.get("url"):
            values["url"] = values["github"]
        # If only url is provided, set github to url
        elif values.get("url") and not values.get("github"):
            values["github"] = values["url"]
        return values

    @property
    def name(self):
        return f"Dependency: {self.github}"


class GitHubDynamicSubfolderDependency(BaseGitHubDependency):
    """A dependency expressed by a reference to a subfolder of a GitHub repo, which needs
    to be resolved to a specific ref. This is always an unmanaged dependency."""

    subfolder: str
    namespace_inject: Optional[str] = None
    namespace_strip: Optional[str] = None

    @property
    def is_unmanaged(self):
        return True

    def flatten(self, context: BaseProjectConfig) -> List[base_dependency.Dependency]:
        """Convert to a static dependency after resolution"""

        if not self.is_resolved:
            raise DependencyResolutionError(
                f"Dependency {self} is not resolved and cannot be flattened."
            )

        return [
            UnmanagedGitHubRefDependency(
                github=self.github,
                ref=self.ref,
                subfolder=self.subfolder,
                namespace_inject=self.namespace_inject,
                namespace_strip=self.namespace_strip,
            )
        ]

    @property
    def name(self):
        return f"Dependency: {self.github}/{self.subfolder}"

    @property
    def description(self):
        loc = f" @{self.tag or self.ref}" if self.ref or self.tag else ""
        return f"{self.github}/{self.subfolder}{loc}"


class GitHubDynamicDependency(BaseGitHubDependency):
    """A dependency expressed by a reference to a GitHub repo, which needs
    to be resolved to a specific ref and/or package version."""

    unmanaged: bool = False
    namespace_inject: Optional[str] = None
    namespace_strip: Optional[str] = None
    password_env_name: Optional[str] = None

    skip: List[str] = []

    @property
    def is_unmanaged(self):
        return self.unmanaged

    @validator("skip", pre=True)
    def listify_skip(cls, v):
        if v and not isinstance(v, list):
            v = [v]
        return v

    @root_validator
    def check_unmanaged_values(cls, values):
        if not values.get("unmanaged") and (
            values.get("namespace_inject") or values.get("namespace_strip")
        ):
            raise ValueError(
                "The namespace_strip and namespace_inject fields require unmanaged = True"
            )

        return values

    def _flatten_unpackaged(
        self,
        repo: Repository,
        subfolder: str,
        skip: List[str],
        managed: bool,
        namespace: Optional[str],
    ) -> List[base_dependency.StaticDependency]:
        """Locate unmanaged dependencies from a repository subfolder (such as unpackaged/pre or unpackaged/post)"""
        unpackaged = []
        try:
            contents = repo.directory_contents(subfolder, return_as=dict, ref=self.ref)
        except NotFoundError:
            contents = None

        if contents:
            for dirname in sorted(contents.keys()):
                this_subfolder = f"{subfolder}/{dirname}"
                if this_subfolder in skip:
                    continue

                unpackaged.append(
                    UnmanagedGitHubRefDependency(
                        github=self.github,
                        ref=self.ref,
                        subfolder=this_subfolder,
                        unmanaged=not managed,
                        namespace_inject=namespace if namespace and managed else None,
                        namespace_strip=namespace
                        if namespace and not managed
                        else None,
                    )
                )

        return unpackaged

    def flatten(self, context: BaseProjectConfig) -> List[base_dependency.Dependency]:
        """Find more dependencies based on repository contents.

        Includes:
        - dependencies from cumulusci.yml
        - subfolders of unpackaged/pre
        - the contents of src, if this is not a managed package
        - subfolders of unpackaged/post
        """
        if not self.is_resolved:
            raise DependencyResolutionError(
                f"Dependency {self} is not resolved and cannot be flattened."
            )

        deps = []

        context.logger.info(f"Collecting dependencies from Github repo {self.github}")
        repo = get_repo(self.github, context)

        package_config = get_remote_project_config(repo, self.ref)
        _, namespace = get_package_data(package_config)

        # Parse upstream dependencies from the repo's cumulusci.yml
        # These may be unresolved or unflattened; if so, `get_static_dependencies()`
        # will manage them.
        dependencies = package_config.project__dependencies
        if dependencies:
            deps.extend([parse_dependency(d) for d in dependencies])
            if None in deps:
                raise DependencyResolutionError(
                    f"Unable to flatten dependency {self} because a transitive dependency could not be parsed."
                )

        # Check for unmanaged flag on a namespaced package
        managed = bool(namespace and not self.unmanaged)

        # Look for subfolders under unpackaged/pre
        # unpackaged/pre is always deployed unmanaged, no namespace manipulation.
        deps.extend(
            self._flatten_unpackaged(
                repo, "unpackaged/pre", self.skip, managed=False, namespace=None
            )
        )

        if not self.package_dependency:
            if managed:
                # We had an expectation of finding a package version and did not.
                raise DependencyResolutionError(
                    f"Could not find latest release for {self}"
                )

            # Deploy the project, if unmanaged.
            deps.append(
                UnmanagedGitHubRefDependency(
                    github=self.github,
                    ref=self.ref,
                    unmanaged=self.unmanaged,
                    namespace_inject=self.namespace_inject,
                    namespace_strip=self.namespace_strip,
                )
            )
        else:
            deps.append(self.package_dependency)

        # We always inject the project's namespace into unpackaged/post metadata if managed
        deps.extend(
            self._flatten_unpackaged(
                repo,
                "unpackaged/post",
                self.skip,
                managed=managed,
                namespace=namespace,
            )
        )

        return deps

    @property
    def description(self):
        unmanaged = " (unmanaged)" if self.unmanaged else ""
        loc = f" @{self.tag or self.ref}" if self.ref or self.tag else ""
        return f"{self.github}{unmanaged}{loc}"


class UnmanagedGitHubRefDependency(base_dependency.UnmanagedDependency):
    """Static dependency on unmanaged metadata in a specific GitHub ref and subfolder."""

    repo_owner: Optional[str] = None
    repo_name: Optional[str] = None

    # or
    github: Optional[AnyUrl] = None

    # and
    ref: str

    # for backwards compatibility only; currently unused
    filename_token: Optional[str] = None
    namespace_token: Optional[str] = None

    @root_validator
    def validate(cls, values):
        return _validate_github_parameters(values)

    def _get_zip_src(self, context):
        repo = get_repo(self.github, context)

        # We don't pass `subfolder` to download_extract_github_from_repo()
        # because we need to get the whole ref in order to
        # correctly handle any permutation of MDAPI/SFDX format,
        # with or without a subfolder specified.

        # install() will take care of that for us.
        return download_extract_github_from_repo(
            repo,
            ref=self.ref,
        )

    @property
    def name(self):
        subfolder = (
            f"/{self.subfolder}" if self.subfolder and self.subfolder != "src" else ""
        )
        return f"Deploy {self.github}{subfolder}"

    @property
    def description(self):
        subfolder = (
            f"/{self.subfolder}" if self.subfolder and self.subfolder != "src" else ""
        )

        return f"{self.github}{subfolder} @{self.ref}"
