from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.dependencies.dependencies import (
    Dependency,
    GitHubDynamicDependency,
    ManagedPackageDependency,
)
from typing import Iterable, List
from cumulusci.core.dependencies.resolvers import DependencyResolutionStrategy
import itertools

# We have three total jobs to do:
# - Resolve dynamic dependencies to a ref, and optionally a managed package version
# - Flatten dependencies into fully-specified steps
# - Install flattened dependencies

# This module takes over jobs 1 and 2 from ProjectConfig
# Dependency objects will have an `install()` method that calls to services elsewhere,
# satisfying job 3.


# project:
#    resolutions:
#        stacks:
#           allow_betas:
#            - 2gp_exact_match
#            - managed_beta
#            - managed_release
#           2gp_pref:
#            - 2gp_exact_match
#            - managed_release
#        default_stack: latest_prod


# How should per-dependency resolver specification interact with the project-level
# specification used by the lowest-level dependency?
#    dependencies:
#        - github: https://foo/
#          resolver_stack: latest_beta


def get_resolver_stack(
    context: BaseProjectConfig, name: str
) -> List[DependencyResolutionStrategy]:
    stacks = context.project__resolvers
    if stacks and name in stacks:
        return [DependencyResolutionStrategy(n) for n in stacks[name]]

    raise CumulusCIException(f"Resolver stack {name} was not found.")


def get_static_dependencies(
    dependencies: List[Dependency],
    strategies: List[DependencyResolutionStrategy],
    context: BaseProjectConfig,
    ignore_deps: List[dict] = None,
):
    """Resolves the project -> dependencies section of cumulusci.yml
    to convert dynamic github dependencies into static dependencies
    by inspecting the referenced repositories.

    Keyword arguments:
    :param dependencies: a list of dependencies to resolve
    :param ignore_deps: if provided, ignore the specified dependencies wherever found.
    """

    while any(not d.is_flattened or not d.is_resolved for d in dependencies):
        for d in dependencies:
            if not d.is_resolved:
                d.resolve(context, strategies)

        def unique(it: Iterable):
            seen = set()

            for each in it:
                if each not in seen:
                    seen.add(each)
                    yield each

        dependencies = list(
            unique(
                itertools.chain(
                    [
                        d.flatten(context)
                        for d in dependencies
                        if not _should_ignore_dependency(d, ignore_deps or [])
                    ]
                ),
            )
        )

    # Make sure, if we had no flattening or resolving to do, that we apply the ignore list.
    return [
        d for d in dependencies if not _should_ignore_dependency(d, ignore_deps or [])
    ]


def _should_ignore_dependency(dependency: Dependency, ignore_deps: List[dict]):
    if not ignore_deps:
        return False

    ignore_github = [d["github"] for d in ignore_deps if "github" in d]
    ignore_namespace = [d["namespace"] for d in ignore_deps if "namespace" in d]

    if isinstance(dependency, ManagedPackageDependency) and dependency.namespace:
        return dependency.namespace in ignore_namespace
    if isinstance(dependency, GitHubDynamicDependency) and dependency.github:
        return dependency.github in ignore_github

    return False
