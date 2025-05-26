from .base import (
    DynamicDependency,
    StaticDependency,
    Dependency,
    UnmanagedDependency,
    DependencyResolutionStrategy,
)
from .dependencies import (
    PackageNamespaceVersionDependency,
    PackageVersionIdDependency,
    UnmanagedZipURLDependency,
    add_dependency_class,
    add_dependency_pin_class,
    parse_dependencies,
)
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

__all__ = (
    "DynamicDependency",
    "StaticDependency",
    "Dependency",
    "UnmanagedDependency",
    "DependencyResolutionStrategy",
    "PackageNamespaceVersionDependency",
    "PackageVersionIdDependency",
    "UnmanagedZipURLDependency",
    "GitHubDynamicDependency",
    "GitHubDynamicSubfolderDependency",
    "UnmanagedGitHubRefDependency",
    "GitHubDependencyPin",
    "add_dependency_class",
    "add_dependency_pin_class",
    "parse_dependencies",
)
