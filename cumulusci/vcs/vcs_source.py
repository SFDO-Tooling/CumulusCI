import os
import shutil
from abc import ABC, abstractmethod
from typing import Type

import fs

from cumulusci.core.exceptions import DependencyResolutionError, VcsNotFoundError
from cumulusci.core.utils import import_global
from cumulusci.utils import download_extract_vcs_from_repo
from cumulusci.utils.yaml.cumulusci_yml import VCSSourceModel, VCSSourceRelease

# To avoid circular dependency error
# from cumulusci.core.config import BaseProjectConfig
# from cumulusci.vcs.base import VCSService
# from cumulusci.vcs.models import AbstractRepo


class VCSSource(ABC):
    """Abstract base class for VCS sources.
    This class defines the interface for VCS sources and provides
    common functionality for working with VCS sources.
    Subclasses should implement the methods and properties defined here.
    """

    _registry = {}
    # project_config : BaseProjectConfig
    spec: VCSSourceModel
    vcs: str
    url: str
    location: str
    # repo: AbstractRepo
    repo_owner: str
    repo_name: str
    # vcs_service: VCSService

    def __init__(self, project_config, spec: VCSSourceModel):
        self.project_config = project_config
        self.spec = spec
        self.vcs = spec.vcs
        self.url = spec.url
        self.location = self.url

        if self.url.endswith(".git"):
            self.url = self.url[:-4]

        self._resolve_repo()

    def _resolve_repo(self):
        from cumulusci.vcs.base import VCSService

        self.vcs_service: VCSService = self.get_vcs_service()

        try:
            from cumulusci.vcs.models import AbstractRepo

            self.repo: AbstractRepo = self.vcs_service.get_repository(
                options={"repository_url": self.url}
            )
        except VcsNotFoundError:
            raise DependencyResolutionError(
                f"We are unable to find the repository at {self.url}. Please make sure the URL is correct, that your GitHub user has read access to the repository, and that your GitHub personal access token includes the “repo” scope."
            )

        self._set_additional_repo_config()

        self.resolve()

    @classmethod
    def register(cls, vcs_type: str, subclass: str):
        """Register a subclass of VCSSource with a specific type name.
        This allows the VCSSource class to create instances of the subclass
        based on the type name specified in the VCSSourceModel.
        Args:
            vcs_type (str): The vcs type name to register the subclass with, ex: 'github'.
            subclass (str): The subclass to register, ex: 'cumulusci.core.source.GitHubSource'.
        """
        cls._registry[vcs_type] = subclass

    @classmethod
    def registered_source_models(cls):
        """Returns a list of registered classes.
        return:
            [GitHubSource, ...].
        """
        return_list = []
        for source_klass_path in cls._registry.values():
            if source_klass_path:
                source_klass = import_global(source_klass_path)
                if issubclass(source_klass, VCSSource):
                    return_list.append(source_klass.source_model())
        return return_list

    @classmethod
    def create(cls, project_config, spec: VCSSourceModel):
        source_klass_path = cls._registry.get(spec.vcs, None)
        if source_klass_path:
            source_klass = import_global(source_klass_path)
            if issubclass(source_klass, VCSSource):
                return source_klass(project_config, spec)

        raise ValueError(f"No child class found for type_name={spec.vcs}")

    @classmethod
    @abstractmethod
    def source_model(self) -> Type[VCSSourceModel]:
        raise NotImplementedError("Subclasses should implement source_model")

    @abstractmethod
    def get_vcs_service(self):
        raise NotImplementedError("Subclasses should implement get_vcs_service")

    @abstractmethod
    def __repr__(self):
        raise NotImplementedError(
            "Subclasses should implement __repr__ to provide a string representation of the VCS source."
        )

    @abstractmethod
    def __str__(self):
        raise NotImplementedError(
            "Subclasses should implement __str__ to provide a string representation of the VCS source."
        )

    @abstractmethod
    def __hash__(self):
        raise NotImplementedError(
            "Subclasses should implement __hash__ to provide a hash value for the VCS source."
        )

    @abstractmethod
    def get_ref(self):
        raise NotImplementedError(
            "Subclasses should implement get_ref to retrieve the reference information."
        )

    @abstractmethod
    def get_tag(self):
        raise NotImplementedError(
            "Subclasses should implement get_tag to retrieve the tag information."
        )

    @abstractmethod
    def get_branch(self):
        raise NotImplementedError(
            "Subclasses should implement get_branch to retrieve the branch information."
        )

    @abstractmethod
    def get_release_tag(self):
        raise NotImplementedError(
            "Subclasses should implement get_release_tag to retrieve the release tag information."
        )

    def _set_additional_repo_config(self):
        ### Subclasses can override this method to set additional configuration on the repo.
        """Set additional configuration on the repo."""
        pass

    def resolve(self):
        from cumulusci.vcs.bootstrap import find_latest_release, find_previous_release

        """Resolve a VCS source into a specific commit.

        The spec must include:
        - vcs: the VCS repository type (e.g., GitHub, Bitbucket, ADO)
        - url: the URL of the VCS repository

        It's recommended that the source include:
        - resolution_strategy: [production | preproduction | <strategy-name>]

        The spec may instead be specific about the desired ref or release:
        - commit: a commit hash
        - ref: a Git ref
        - branch: a Git branch
        - tag: a Git tag
        - release: "latest" | "previous" | "latest_beta"

        If none of these are specified, CumulusCI will use the resolution strategy "production"
        to locate the appropriate release or ref.
        """
        ref = None
        self.branch = None
        # These branches preserve some existing behavior: when a source is set to
        # a specific tag or release, there's no fallback, as there would be
        # if we were subsumed within the dependency resolution machinery.

        # If the user was _not_ specific, we will use the full resolution stack,
        # including fallback behaviors.
        if self.spec.commit:
            self.commit = self.description = self.spec.commit
            return
        elif self.spec.ref:
            ref = self.get_ref()
        elif self.spec.tag:
            ref = self.get_tag()
        elif self.spec.branch:
            self.branch = self.spec.branch
            ref = self.get_branch()
        elif self.spec.release:
            release = None
            if self.spec.release is VCSSourceRelease.LATEST:
                release = find_latest_release(self.repo, include_beta=False)
            elif self.spec.release is VCSSourceRelease.LATEST_BETA:
                release = find_latest_release(self.repo, include_beta=True)
            elif self.spec.release is VCSSourceRelease.PREVIOUS:
                release = find_previous_release(self.repo)
            if release is None:
                raise DependencyResolutionError(
                    f"Could not find release {self.spec.release}."
                )
            ref = release.tag_ref_name
        else:
            # Avoid circular import issues
            from cumulusci.core.dependencies.resolvers import (
                get_resolver_stack,
                resolve_dependency,
            )

            dynamic_dependency_cls = self.vcs_service.dynamic_dependency_class

            # Use resolution strategies to find the right commit.
            dep = dynamic_dependency_cls(url=self.spec.url)
            dep.set_repo(self.repo)

            resolve_dependency(
                dep,
                self.project_config,
                get_resolver_stack(self.project_config, self.spec.resolution_strategy),
            )

            self.commit = self.description = dep.ref
            return

        self.description = ref[6:] if ref.startswith("heads/") else ref
        self.commit = self.repo.get_ref(ref).sha

    def fetch(self):
        """Fetch the archive of the specified commit and construct its project config."""
        with self.project_config.open_cache(
            fs.path.join("projects", self.repo.repo_name, self.commit)
        ) as path:
            zf = download_extract_vcs_from_repo(self.repo, ref=self.commit)
            try:
                zf.extractall(path)
            except Exception:
                # make sure we don't leave an incomplete cache
                shutil.rmtree(path)
                raise

        project_config = self.project_config.construct_subproject_config(
            repo_info={
                "root": os.path.realpath(path),
                "owner": self.repo.repo_owner,
                "name": self.repo.repo_name,
                "url": self.url,
                "commit": self.commit,
                # Note: we currently only pass the branch if it was explicitly
                # included in the source spec. If the commit was found another way,
                # we aren't looking up what branches have that commit as their head.
                "branch": self.branch,
            }
        )
        return project_config

    @property
    def frozenspec(self):
        """Return a spec to reconstruct this source at the current commit"""
        # TODO: The branch name is lost when freezing the source for MetaDeploy.
        # We could include it here, but it would fail validation when GitHubSourceModel
        # parses it due to having both commit and branch.
        return {
            "vcs": self.vcs,
            "url": self.url,
            "commit": self.commit,
            "description": self.description,
        }

    @property
    def allow_remote_code(self) -> bool:
        return self.spec.allow_remote_code


VCSSource.register("github", "cumulusci.core.source.github.GitHubSource")
VCSSource.register(
    "github_enterprise", "cumulusci.core.source.github.GitHubEnterpriseSource"
)
