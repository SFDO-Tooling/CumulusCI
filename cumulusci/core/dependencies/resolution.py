from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.dependencies.dependencies import Dependency
from typing import List
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


def get_static_dependencies(
    self,
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

        # TODO: unique the dependencies.
        dependencies = list(
            filter(
                itertools.chain([d.flatten(context) for d in dependencies]),
                lambda d: not self._should_ignore_dependency(d, ignore_deps),
            )
        )

    return dependencies


def _should_ignore_dependency(self, dependency, ignore_deps):
    # TODO: reimplement
    if not ignore_deps:
        return False

    if "github" in dependency:
        return dependency["github"] in [dep.get("github") for dep in ignore_deps]
    elif "namespace" in dependency:
        return dependency["namespace"] in [dep.get("namespace") for dep in ignore_deps]

    return False
