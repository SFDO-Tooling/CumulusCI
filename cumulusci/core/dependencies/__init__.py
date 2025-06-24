# from .base import (
#     DynamicDependency,
#     StaticDependency,
#     Dependency,
#     UnmanagedDependency,
# )

from .dependencies import (
    PackageNamespaceVersionDependency,
    PackageVersionIdDependency,
    UnmanagedZipURLDependency,
    add_dependency_class,
    add_dependency_pin_class,
    parse_dependencies,
)

# from .resolvers import DependencyResolutionStrategy, AbstractResolver

from .github import (
    GitHubDynamicDependency,
    GitHubDynamicSubfolderDependency,
    UnmanagedGitHubRefDependency,
    GitHubDependencyPin,
)

add_dependency_class(UnmanagedGitHubRefDependency)
add_dependency_class(GitHubDynamicDependency)
add_dependency_class(GitHubDynamicSubfolderDependency)

add_dependency_pin_class(GitHubDependencyPin)

from .github_resolvers import VCS_GITHUB, GITHUB_RESOLVER_CLASSES
from .resolvers import update_resolver_classes

update_resolver_classes(VCS_GITHUB, GITHUB_RESOLVER_CLASSES)

__all__ = (
    #     "DynamicDependency",
    #     "StaticDependency",
    #     "Dependency",
    #     "UnmanagedDependency",
    #     "DependencyResolutionStrategy",
    #     "AbstractResolver",
    "PackageNamespaceVersionDependency",
    "PackageVersionIdDependency",
    "UnmanagedZipURLDependency",
    #     # "GitHubDynamicDependency",
    #     # "GitHubDynamicSubfolderDependency",
    #     # "UnmanagedGitHubRefDependency",
    #     # "GitHubDependencyPin",
    # "add_dependency_class",
    # "add_dependency_pin_class",
    "parse_dependencies",
    "update_resolver_classes",
)
