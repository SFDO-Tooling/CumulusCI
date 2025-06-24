import functools
from unittest import mock

import pytest

from cumulusci.core.config.tests.test_config import (
    DummyContents,
    DummyGithub,
    DummyRelease,
    DummyRepository,
)
from cumulusci.utils.git import split_repo_url


@pytest.fixture
def github():
    ROOT_REPO = DummyRepository(
        "SFDO-Tooling",
        "RootRepo",
        {
            "cumulusci.yml": DummyContents(
                b"""
    project:
        name: RootRepo
        package:
            name: RootRepo
            namespace: bar
        git:
            repo_url: https://github.com/SFDO-Tooling/CumulusCI-Test
        dependencies:
            - github: https://github.com/SFDO-Tooling/DependencyRepo
              password_env_name: DEP_PW
    """
            ),
            "unpackaged/pre": {"first": {}, "second": {}},
            "src": {"src": ""},
            "unpackaged/post": {"first": {}},
        },
        [
            DummyRelease("release/2.0", "2.0"),
            DummyRelease("release/1.5", "1.5"),
        ],
    )

    DEPENDENCY_REPO = DummyRepository(
        "SFDO-Tooling",
        "DependencyRepo",
        {
            "cumulusci.yml": DummyContents(
                b"""
    project:
        name: DependencyRepo
        package:
            name: DependencyRepo
            namespace: foo
        git:
            repo_url: https://github.com/SFDO-Tooling/CumulusCI-Test
    """
            ),
            "unpackaged/pre": {"top": {}},
            "src": {"src": ""},
            "unpackaged/post": {"top": {}},
        },
        [
            DummyRelease("release/1.1", "1.1"),
            DummyRelease("release/1.0", "1.0"),
        ],
    )

    # This repo contains an unparseable transitive dependency.
    ROOT_BAD_DEP_REPO = DummyRepository(
        "SFDO-Tooling",
        "RootRepoBadDep",
        {
            "cumulusci.yml": DummyContents(
                b"""
    project:
        name: RootRepo
        package:
            name: RootRepo
            namespace: bar
        git:
            repo_url: https://github.com/SFDO-Tooling/CumulusCI-Test
        dependencies:
            - bogus: foo
    """
            ),
        },
    )

    # This repo contains both beta and managed releases.
    RELEASES_REPO = DummyRepository(
        "SFDO-Tooling",
        "CumulusCI-Test-Dep",
        {
            "cumulusci.yml": DummyContents(
                b"""
    project:
        name: CumulusCI-Test-Dep
        package:
            name: CumulusCI-Test-Dep
            namespace: ccitestdep
        git:
            repo_url: https://github.com/SFDO-Tooling/CumulusCI-Test-Dep
    """
            ),
            "unpackaged/pre": {},
            "src": {},
            "unpackaged/post": {},
        },
        [
            DummyRelease("beta/2.1_Beta_1", "2.1 Beta 1"),
            DummyRelease("release/2.0", "2.0"),
            DummyRelease("release/1.0", "1.0"),
        ],
    )

    # This repo contains releases, but no `unmanaged/pre`
    NO_UNMANAGED_PRE_REPO = DummyRepository(
        "SFDO-Tooling",
        "NoUnmanagedPreRepo",
        {
            "cumulusci.yml": DummyContents(
                b"""
    project:
        name: NoUnmanagedPreRepo
        package:
            name: NoUnmanagedPreRepo
            namespace: foo
        git:
            repo_url: https://github.com/SFDO-Tooling/NoUnmanagedPreRepo
    """
            ),
            "src": {},
            "unpackaged/post": {},
        },
        [
            DummyRelease("beta/2.1_Beta_1", "2.1 Beta 1"),
            DummyRelease("release/2.0", "2.0"),
            DummyRelease("release/1.0", "1.0"),
        ],
    )

    CUMULUSCI_REPO = DummyRepository(
        "SFDO-Tooling",
        "CumulusCI",
        {},
        [
            DummyRelease("release/1.1", "1.1"),
            DummyRelease("beta-wrongprefix", "wrong"),
            DummyRelease("release/1.0", "1.0"),
            DummyRelease("beta/1.0-Beta_2", "1.0 (Beta 2)"),
            DummyRelease("beta/1.0-Beta_1", "1.0 (Beta 1)"),
        ],
    )

    # This repo contains no releases at all
    NO_RELEASES_REPO = DummyRepository(
        "SFDO-Tooling",
        "NoReleasesRepo",
        {
            "cumulusci.yml": DummyContents(
                b"""
    project:
        name: CumulusCI-Test
        package:
            name: CumulusCI-Test
    """
            ),
            "unpackaged/pre": {"pre": {}, "skip": {}},
            "src": {"src": ""},
            "unpackaged/post": {"post": {}, "skip": {}},
        },
        [],
    )

    # This repo contains a release, but no namespace
    UNMANAGED_REPO = DummyRepository(
        "SFDO-Tooling",
        "UnmanagedRepo",
        {
            "cumulusci.yml": DummyContents(
                b"""
    project:
        name: CumulusCI-Test
        package:
            name: CumulusCI-Test
    """
            ),
            "unpackaged/pre": {"pre": {}, "skip": {}},
            "src": {"src": ""},
            "unpackaged/post": {"post": {}, "skip": {}},
        },
        [
            DummyRelease("release/1.0", "1.0"),
        ],
    )

    TWO_GP_REPO = DummyRepository(
        "SFDO-Tooling",
        "TwoGPRepo",
        {
            "cumulusci.yml": DummyContents(
                b"""
    project:
        name: CumulusCI-2GP-Test
        package:
            name: CumulusCI-2GP-Test
            namespace: test_2gp
        git:
            2gp_context: "Nonstandard Package Status"
    """
            ),
            "unpackaged/pre": {"pre": {}, "skip": {}},
            "src": {"src": ""},
            "unpackaged/post": {"post": {}, "skip": {}},
        },
        releases=[DummyRelease("release/1.0", "1.0")],
        commits={
            "main_sha": mock.Mock(
                sha="main_sha",
                status=mock.Mock(
                    return_value=mock.Mock(
                        statuses=[
                            mock.Mock(
                                state="success",
                                context="Nonstandard Package Status",
                                description="version_id: 04t000000000005",
                            )
                        ]
                    )
                ),
            ),
            "feature/232_sha": mock.Mock(
                sha="feature/232_sha",
                parents=[{"sha": "parent_sha"}],
                status=mock.Mock(return_value=mock.Mock(statuses=[])),
            ),
            "parent_sha": mock.Mock(
                sha="parent_sha",
                parents=[],
                status=mock.Mock(
                    return_value=mock.Mock(
                        statuses=[
                            mock.Mock(
                                state="success",
                                context="Nonstandard Package Status",
                                description="version_id: 04t000000000000",
                            )
                        ]
                    )
                ),
            ),
            "feature/232__test_sha": mock.Mock(
                sha="feature/232__test_sha",
                parents=[],
                status=mock.Mock(
                    return_value=mock.Mock(
                        statuses=[
                            mock.Mock(
                                state="success",
                                context="Nonstandard Package Status",
                                description="version_id: 04t000000000001",
                            )
                        ]
                    )
                ),
            ),
        },
    )

    TWO_GP_MISSING_REPO = DummyRepository(
        "SFDO-Tooling",
        "TwoGPMissingRepo",
        {
            "cumulusci.yml": DummyContents(
                b"""
    project:
        name: CumulusCI-2GP-Test
        package:
            name: CumulusCI-2GP-Test
        git:
            2gp_context: "Nonstandard Package Status"
    """
            ),
            "unpackaged/pre": {"pre": {}, "skip": {}},
            "src": {"src": ""},
            "unpackaged/post": {"post": {}, "skip": {}},
        },
        releases=[],
        commits={
            "main_sha": mock.Mock(
                sha="main_sha",
                parents=[],
                status=mock.Mock(return_value=mock.Mock(statuses=[])),
            ),
            "feature/232_sha": mock.Mock(
                sha="feature/232_sha",
                parents=[{"sha": "parent_sha"}],
                status=mock.Mock(return_value=mock.Mock(statuses=[])),
            ),
            "parent_sha": mock.Mock(
                sha="parent_sha",
                parents=[],
                status=mock.Mock(return_value=mock.Mock(statuses=[])),
            ),
        },
    )

    def branch(which_repo, which_branch):
        branch = mock.Mock()
        branch.commit = which_repo.commit(f"{which_branch}_sha")
        branch.name = which_branch
        return branch

    TWO_GP_REPO.branch = mock.Mock(wraps=functools.partial(branch, TWO_GP_REPO))
    TWO_GP_MISSING_REPO.branch = mock.Mock(
        wraps=functools.partial(branch, TWO_GP_MISSING_REPO)
    )

    return DummyGithub(
        {
            "UnmanagedRepo": UNMANAGED_REPO,
            "CumulusCI": CUMULUSCI_REPO,
            "NoUnmanagedPreRepo": NO_UNMANAGED_PRE_REPO,
            "RootRepo": ROOT_REPO,
            "RootRepoBadDep": ROOT_BAD_DEP_REPO,
            "DependencyRepo": DEPENDENCY_REPO,
            "ReleasesRepo": RELEASES_REPO,
            "TwoGPRepo": TWO_GP_REPO,
            "TwoGPMissingRepo": TWO_GP_MISSING_REPO,
            "NoReleasesRepo": NO_RELEASES_REPO,
        }
    )


@pytest.fixture
def project_config(github, init_git_repo):
    pc = mock.Mock()
    pc.lookup.return_value = None

    pc.init_git_repo = init_git_repo

    def get_github_repo_side_effect(project_config, url):
        repo_mock = init_git_repo
        repo_mock.repo = github.repository(*split_repo_url(url))
        repo_mock.repo_url = url
        return repo_mock

    def get_repo_from_url(url):
        return github.repository(*split_repo_url(url))

    pc.get_repo_from_url = get_repo_from_url
    pc.get_github_repo_side_effect = get_github_repo_side_effect

    return pc


@pytest.fixture
@mock.patch("cumulusci.vcs.github.adapter.GitHubRepository._init_repo")
def init_git_repo(init_repo):
    from github3 import GitHub

    from cumulusci.vcs.github.adapter import GitHubRepository

    # from cumulusci.vcs.tests.dummy_service import DummyRepo
    pc = mock.Mock()
    pc.lookup.return_value = None

    repo = GitHubRepository(GitHub(), pc)
    return repo


@pytest.fixture
def patch_github_resolvers_get_github_repo():
    with mock.patch(
        "cumulusci.core.dependencies.github_resolvers.get_github_repo"
    ) as patched:
        yield patched


@pytest.fixture
def patch_github_dependencies_get_github_repo():
    with mock.patch("cumulusci.core.dependencies.github.get_github_repo") as patched:
        yield patched
