from typing import List, Optional, Tuple
from unittest import mock

import pytest
from pydantic import ValidationError

from cumulusci.core.config import UniversalConfig
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.dependencies.dependencies import (
    DependencyResolutionStrategy,
    DynamicDependency,
    GitHubBetaReleaseTagResolver,
    GitHubDynamicDependency,
    GitHubReleaseBranchCommitStatusResolver,
    GitHubReleaseBranchExactMatchCommitStatusResolver,
    GitHubReleaseBranchResolver,
    GitHubReleaseTagResolver,
    GitHubTagResolver,
    GitHubUnmanagedHeadResolver,
    PackageNamespaceVersionDependency,
    PackageVersionIdDependency,
    Resolver,
    StaticDependency,
    UnmanagedGitHubRefDependency,
    UnmanagedZipURLDependency,
    get_resolver,
    get_resolver_stack,
    get_static_dependencies,
    parse_dependency,
)
from cumulusci.core.exceptions import CumulusCIException, DependencyResolutionError
from cumulusci.core.tests.test_config import (
    DummyContents,
    DummyGithub,
    DummyRelease,
    DummyRepository,
)
from cumulusci.salesforce_api.package_install import (
    DEFAULT_PACKAGE_RETRY_OPTIONS,
    PackageInstallOptions,
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
    """
            ),
            "unpackaged/pre": {"first": {}, "second": {}},
            "src": {"src": ""},
            "unpackaged/post": {"first": {}},
        },
        [
            DummyRelease("release/2.0", "2.0"),
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
            "main_sha": mock.Mock(sha="main_sha"),
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

    def branch(which_branch):
        branch = mock.Mock()
        branch.commit = TWO_GP_REPO.commit(f"{which_branch}_sha")
        return branch

    TWO_GP_REPO.branch = mock.Mock(wraps=branch)

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
        }
    )


@pytest.fixture
def project_config(github):
    pc = mock.Mock()

    def get_repo_from_url(url):
        return github.repository(*split_repo_url(url))

    pc.get_repo_from_url = get_repo_from_url

    return pc


class ConcreteDynamicDependency(DynamicDependency):
    ref: Optional[str]
    resolved: Optional[bool] = False

    @property
    def is_resolved(self):
        return self.resolved

    def resolve(
        self, context: BaseProjectConfig, strategies: List[DependencyResolutionStrategy]
    ):
        super().resolve(context, strategies)
        self.resolved = True

    @property
    def name(self):
        return ""

    @property
    def description(self):
        return ""


class MockResolver(Resolver):
    def __init__(
        self,
        resolve_ref: Optional[str] = None,
        resolve_dep: Optional[StaticDependency] = None,
    ):
        self.ref = resolve_ref
        self.dep = resolve_dep

    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        return bool(self.dep and self.ref)

    def resolve(
        self, dep: DynamicDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[StaticDependency]]:
        return self.ref, self.dep


class MockBadResolver(Resolver):
    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        return True

    def resolve(
        self, dep: DynamicDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[StaticDependency]]:
        raise DependencyResolutionError("Bad resolver")


class TestDynamicDependency:
    @mock.patch("cumulusci.core.dependencies.dependencies.get_resolver")
    def test_dynamic_dependency(self, get_resolver):
        d = ConcreteDynamicDependency()
        resolvers = [
            MockResolver(),
            MockResolver(
                "aaaaaaaaaaaaaaaa",
                PackageNamespaceVersionDependency(namespace="foo", version="1.0"),
            ),
        ]
        get_resolver.side_effect = resolvers

        d.resolve(
            mock.Mock(),
            [
                DependencyResolutionStrategy.STRATEGY_UNMANAGED_HEAD,
                DependencyResolutionStrategy.STRATEGY_COMMIT_STATUS_PREVIOUS_RELEASE_BRANCH,
            ],
        )

        assert d.managed_dependency == PackageNamespaceVersionDependency(
            namespace="foo", version="1.0"
        )
        assert d.ref == "aaaaaaaaaaaaaaaa"

    @mock.patch("cumulusci.core.dependencies.dependencies.get_resolver")
    def test_dynamic_dependency__twice(self, get_resolver):
        d = ConcreteDynamicDependency()
        resolvers = [
            mock.Mock(
                wraps=MockResolver(
                    "aaaaaaaaaaaaaaaa",
                    PackageNamespaceVersionDependency(namespace="foo", version="1.0"),
                )
            ),
        ]
        get_resolver.side_effect = resolvers

        d.resolve(
            mock.Mock(),
            [
                DependencyResolutionStrategy.STRATEGY_UNMANAGED_HEAD,
                DependencyResolutionStrategy.STRATEGY_COMMIT_STATUS_PREVIOUS_RELEASE_BRANCH,
            ],
        )

        assert d.is_resolved
        resolvers[0].resolve.assert_called_once()

    @mock.patch("cumulusci.core.dependencies.dependencies.get_resolver")
    def test_dynamic_dependency_resolution_fails(self, get_resolver):
        d = ConcreteDynamicDependency()
        resolvers = [MockBadResolver()]
        get_resolver.side_effect = resolvers

        with pytest.raises(DependencyResolutionError):
            d.resolve(
                mock.Mock(), [DependencyResolutionStrategy.STRATEGY_UNMANAGED_HEAD]
            )

    @mock.patch("cumulusci.core.dependencies.dependencies.get_resolver")
    def test_dynamic_dependency_resolution_no_results(self, get_resolver):
        d = ConcreteDynamicDependency()
        resolvers = [MockResolver("", None)]
        get_resolver.side_effect = resolvers

        with pytest.raises(DependencyResolutionError):
            d.resolve(
                mock.Mock(), [DependencyResolutionStrategy.STRATEGY_UNMANAGED_HEAD]
            )


class TestGitHubDynamicDependency:
    def test_create_repo_url(self):
        gh = GitHubDynamicDependency(github="https://github.com/Test/TestRepo")
        assert gh.repo_owner == "Test"
        assert gh.repo_name == "TestRepo"

    def test_create_repo_name(self):
        gh = GitHubDynamicDependency(repo_owner="Test", repo_name="TestRepo")
        assert gh.github == "https://github.com/Test/TestRepo"

    def test_create_failure(self):
        with pytest.raises(ValidationError):
            GitHubDynamicDependency(repo_owner="Test")

        with pytest.raises(ValidationError):
            GitHubDynamicDependency(
                github="http://github.com/Test/TestRepo", tag="tag/1.0", ref="aaaaa"
            )

        with pytest.raises(ValidationError):
            GitHubDynamicDependency(
                github="http://github.com/Test/TestRepo", namespace_inject="foo"
            )

    def test_flatten(self, project_config):
        gh = GitHubDynamicDependency(github="https://github.com/SFDO-Tooling/RootRepo")
        gh.ref = "aaaaa"
        gh.managed_dependency = PackageNamespaceVersionDependency(
            namespace="bar", version="2.0"
        )

        assert gh.flatten(project_config) == [
            GitHubDynamicDependency(
                github="https://github.com/SFDO-Tooling/DependencyRepo"
            ),
            UnmanagedGitHubRefDependency(
                github="https://github.com/SFDO-Tooling/RootRepo",
                subfolder="unpackaged/pre/first",
                unmanaged=True,
                ref="aaaaa",
            ),
            UnmanagedGitHubRefDependency(
                github="https://github.com/SFDO-Tooling/RootRepo",
                subfolder="unpackaged/pre/second",
                unmanaged=True,
                ref="aaaaa",
            ),
            PackageNamespaceVersionDependency(namespace="bar", version="2.0"),
            UnmanagedGitHubRefDependency(
                github="https://github.com/SFDO-Tooling/RootRepo",
                subfolder="unpackaged/post/first",
                unmanaged=False,
                ref="aaaaa",
                namespace_inject="bar",
            ),
        ]

    def test_flatten__skip(self, project_config):
        gh = GitHubDynamicDependency(
            github="https://github.com/SFDO-Tooling/RootRepo",
            skip=["unpackaged/pre/first"],
        )
        gh.ref = "aaaaa"
        gh.managed_dependency = PackageNamespaceVersionDependency(
            namespace="bar", version="2.0"
        )

        assert gh.flatten(project_config) == [
            GitHubDynamicDependency(
                github="https://github.com/SFDO-Tooling/DependencyRepo"
            ),
            UnmanagedGitHubRefDependency(
                github="https://github.com/SFDO-Tooling/RootRepo",
                subfolder="unpackaged/pre/second",
                unmanaged=True,
                ref="aaaaa",
            ),
            PackageNamespaceVersionDependency(namespace="bar", version="2.0"),
            UnmanagedGitHubRefDependency(
                github="https://github.com/SFDO-Tooling/RootRepo",
                subfolder="unpackaged/post/first",
                unmanaged=False,
                ref="aaaaa",
                namespace_inject="bar",
            ),
        ]

    def test_flatten__not_found(self, project_config):
        gh = GitHubDynamicDependency(
            github="https://github.com/SFDO-Tooling/NoUnmanagedPreRepo",
        )
        gh.ref = "aaaaa"
        gh.managed_dependency = PackageNamespaceVersionDependency(
            namespace="foo", version="2.0"
        )

        assert gh.flatten(project_config) == [
            PackageNamespaceVersionDependency(namespace="foo", version="2.0"),
        ]

    def test_flatten__unresolved(self):
        context = mock.Mock()
        gh = GitHubDynamicDependency(repo_owner="Test", repo_name="TestRepo")

        with pytest.raises(DependencyResolutionError) as e:
            gh.flatten(context)

        assert "is not resolved" in str(e)

    def test_flatten__bad_transitive_dep(self, project_config):
        gh = GitHubDynamicDependency(repo_owner="Test", repo_name="RootRepoBadDep")
        gh.ref = "aaaa"

        with pytest.raises(DependencyResolutionError) as e:
            gh.flatten(project_config)

        assert "transitive dependency could not be parsed" in str(e)

    def test_flatten__unmanaged_src(self, project_config):
        gh = GitHubDynamicDependency(
            github="https://github.com/SFDO-Tooling/RootRepo",
            unmanaged=True,
        )
        gh.ref = "aaaaa"

        assert gh.flatten(project_config) == [
            GitHubDynamicDependency(
                github="https://github.com/SFDO-Tooling/DependencyRepo"
            ),
            UnmanagedGitHubRefDependency(
                github="https://github.com/SFDO-Tooling/RootRepo",
                subfolder="unpackaged/pre/first",
                unmanaged=True,
                ref="aaaaa",
            ),
            UnmanagedGitHubRefDependency(
                github="https://github.com/SFDO-Tooling/RootRepo",
                subfolder="unpackaged/pre/second",
                unmanaged=True,
                ref="aaaaa",
            ),
            UnmanagedGitHubRefDependency(
                github="https://github.com/SFDO-Tooling/RootRepo",
                subfolder="src",
                unmanaged=True,
                ref="aaaaa",
            ),
            UnmanagedGitHubRefDependency(
                github="https://github.com/SFDO-Tooling/RootRepo",
                subfolder="unpackaged/post/first",
                unmanaged=True,
                ref="aaaaa",
                namespace_strip="bar",
            ),
        ]

    def test_flatten__no_release(self, project_config):
        gh = GitHubDynamicDependency(
            github="https://github.com/SFDO-Tooling/RootRepo",
            unmanaged=False,
        )
        gh.ref = "aaaaa"

        with pytest.raises(DependencyResolutionError) as e:
            gh.flatten(project_config)

        assert "Could not find latest release" in str(e)


class TestPackageNamespaceVersionDependency:
    @mock.patch(
        "cumulusci.core.dependencies.dependencies.install_package_by_namespace_version"
    )
    def test_install(self, install_package_by_namespace_version):
        m = PackageNamespaceVersionDependency(namespace="test", version="1.0")

        context = mock.Mock()
        org = mock.Mock()

        m.install(context, org)

        install_package_by_namespace_version.assert_called_once_with(
            context,
            org,
            m.namespace,
            m.version,
            PackageInstallOptions(),
            retry_options=DEFAULT_PACKAGE_RETRY_OPTIONS,
        )

    @mock.patch(
        "cumulusci.core.dependencies.dependencies.install_package_by_namespace_version"
    )
    def test_install__custom_options(self, install_package_by_namespace_version):
        m = PackageNamespaceVersionDependency(namespace="foo", version="1.0")

        context = mock.Mock()
        org = mock.Mock()
        opts = PackageInstallOptions(password="test")

        m.install(context, org, options=opts)

        install_package_by_namespace_version.assert_called_once_with(
            context,
            org,
            m.namespace,
            m.version,
            opts,
            retry_options=DEFAULT_PACKAGE_RETRY_OPTIONS,
        )

    def test_name(self):
        assert (
            str(PackageNamespaceVersionDependency(namespace="foo", version="1.0"))
            == "Install foo 1.0"
        )

    def test_package_name(self):
        assert (
            PackageNamespaceVersionDependency(
                namespace="foo", version="1.0", package_name="Foo"
            ).package
            == "Foo"
        )

        assert (
            PackageNamespaceVersionDependency(namespace="foo", version="1.0").package
            == "foo"
        )


class TestPackageVersionIdDependency:
    @mock.patch(
        "cumulusci.core.dependencies.dependencies.install_package_by_version_id"
    )
    def test_install(self, install_package_by_version_id):
        m = PackageVersionIdDependency(version_id="04t000000000000")

        context = mock.Mock()
        org = mock.Mock()

        m.install(context, org)

        install_package_by_version_id.assert_called_once_with(
            context,
            org,
            m.version_id,
            PackageInstallOptions(),
            retry_options=DEFAULT_PACKAGE_RETRY_OPTIONS,
        )

    @mock.patch(
        "cumulusci.core.dependencies.dependencies.install_package_by_version_id"
    )
    def test_install__custom_options(self, install_package_by_version_id):
        m = PackageVersionIdDependency(version_id="04t000000000000")

        context = mock.Mock()
        org = mock.Mock()
        opts = PackageInstallOptions(password="test")

        m.install(context, org, options=opts)

        install_package_by_version_id.assert_called_once_with(
            context,
            org,
            m.version_id,
            opts,
            retry_options=DEFAULT_PACKAGE_RETRY_OPTIONS,
        )

    def test_name(self):
        assert (
            str(
                PackageVersionIdDependency(
                    package_name="foo", version_id="04t000000000000"
                )
            )
            == "Install foo 04t000000000000"
        )

    def test_package_name(self):
        assert (
            PackageVersionIdDependency(version_id="04t000000000000").package
            == "Unknown Package"
        )


class TestUnmanagedGitHubRefDependency:
    def test_validation(self):
        with pytest.raises(ValidationError):
            UnmanagedGitHubRefDependency(github="http://github.com", repo_owner="Test")

        u = UnmanagedGitHubRefDependency(
            github="https://github.com/Test/TestRepo", ref="aaaaaaaa"
        )
        assert u.repo_owner == "Test"
        assert u.repo_name == "TestRepo"

        u = UnmanagedGitHubRefDependency(
            repo_owner="Test", repo_name="TestRepo", ref="aaaaaaaa"
        )
        assert u.github == "https://github.com/Test/TestRepo"

    @mock.patch(
        "cumulusci.core.dependencies.dependencies.download_extract_github_from_repo"
    )
    @mock.patch("cumulusci.core.dependencies.dependencies.MetadataPackageZipBuilder")
    @mock.patch("cumulusci.core.dependencies.dependencies.ApiDeploy")
    def test_install(self, api_deploy_mock, zip_builder_mock, download_mock):
        d = UnmanagedGitHubRefDependency(
            github="http://github.com/Test/TestRepo", ref="aaaaaaaa"
        )

        context = mock.Mock()
        org = mock.Mock()
        d.install(context, org)

        download_mock.assert_called_once_with(
            context.get_repo_from_url.return_value, None, ref=d.ref
        )
        zip_builder_mock.from_zipfile.assert_called_once_with(
            download_mock.return_value,
            options={
                "unmanaged": None,  # TODO: is this bad for this task?
                "namespace_inject": None,
                "namespace_strip": None,
            },
            logger=mock.ANY,  # the logger
        )
        api_deploy_mock.assert_called_once_with(
            mock.ANY,  # The context object is checked below
            zip_builder_mock.from_zipfile.return_value.as_base64.return_value,
        )
        mock_task = api_deploy_mock.call_args_list[0][0][0]
        assert mock_task.org_config == org
        assert mock_task.project_config == context

        api_deploy_mock.return_value.assert_called_once()

    def test_get_unmanaged(self):
        org = mock.Mock()
        org.installed_packages = {"foo": "1.0"}
        assert (
            UnmanagedGitHubRefDependency(
                github="http://github.com/Test/TestRepo", ref="aaaa", unmanaged=True
            )._get_unmanaged(org)
            is True
        )
        assert (
            UnmanagedGitHubRefDependency(
                github="http://github.com/Test/TestRepo",
                ref="aaaa",
                namespace_inject="foo",
            )._get_unmanaged(org)
            is False
        )
        assert (
            UnmanagedGitHubRefDependency(
                github="http://github.com/Test/TestRepo",
                ref="aaaa",
                namespace_inject="bar",
            )._get_unmanaged(org)
            is True
        )

    def test_name(self):
        assert (
            str(
                UnmanagedGitHubRefDependency(
                    github="http://github.com/Test/TestRepo",
                    subfolder="unpackaged/pre/first",
                    ref="aaaa",
                )
            )
            == "Deploy http://github.com/Test/TestRepo/unpackaged/pre/first"
        )

        assert (
            str(
                UnmanagedGitHubRefDependency(
                    github="http://github.com/Test/TestRepo",
                    ref="aaaa",
                )
            )
            == "Deploy http://github.com/Test/TestRepo"
        )


class TestUnmanagedZipURLDependency:
    @mock.patch("cumulusci.core.dependencies.dependencies.download_extract_zip")
    @mock.patch("cumulusci.core.dependencies.dependencies.MetadataPackageZipBuilder")
    @mock.patch("cumulusci.core.dependencies.dependencies.ApiDeploy")
    def test_install(self, api_deploy_mock, zip_builder_mock, download_mock):
        d = UnmanagedZipURLDependency(zip_url="http://foo.com", subfolder="bar")

        context = mock.Mock()
        org = mock.Mock()
        d.install(context, org)

        download_mock.assert_called_once_with(d.zip_url, subfolder=d.subfolder)

        zip_builder_mock.from_zipfile.assert_called_once_with(
            download_mock.return_value,
            options={
                "unmanaged": None,  # TODO: is this bad for this task?
                "namespace_inject": None,
                "namespace_strip": None,
            },
            logger=mock.ANY,  # the logger
        )
        api_deploy_mock.assert_called_once_with(
            mock.ANY,  # The context object is checked below
            zip_builder_mock.from_zipfile.return_value.as_base64.return_value,
        )
        mock_task = api_deploy_mock.call_args_list[0][0][0]
        assert mock_task.org_config == org
        assert mock_task.project_config == context

        api_deploy_mock.return_value.assert_called_once()

    def test_get_unmanaged(self):
        org = mock.Mock()
        org.installed_packages = {"foo": "1.0"}
        assert (
            UnmanagedZipURLDependency(
                zip_url="http://foo.com", unmanaged=True
            )._get_unmanaged(org)
            is True
        )
        assert (
            UnmanagedZipURLDependency(
                zip_url="http://foo.com", namespace_inject="foo"
            )._get_unmanaged(org)
            is False
        )
        assert (
            UnmanagedZipURLDependency(
                zip_url="http://foo.com", namespace_inject="bar"
            )._get_unmanaged(org)
            is True
        )

    def test_name(self):
        assert (
            str(UnmanagedZipURLDependency(zip_url="http://foo.com", subfolder="bar"))
            == "Deploy http://foo.com /bar"
        )


class TestParseDependency:
    def test_parse_managed_package_dep(self):
        m = parse_dependency({"version": "1.0", "namespace": "foo"})

        assert isinstance(m, PackageNamespaceVersionDependency)

        m = parse_dependency({"version_id": "04t000000000000"})

        assert isinstance(m, PackageVersionIdDependency)

    def test_parse_github_dependency(self):
        g = parse_dependency({"github": "https://github.com/Test/TestRepo"})
        assert isinstance(g, GitHubDynamicDependency)

        g = parse_dependency({"repo_owner": "Test", "repo_name": "TestRepo"})
        assert isinstance(g, GitHubDynamicDependency)

    def test_parse_unmanaged_dependency(self):
        u = parse_dependency(
            {"repo_owner": "Test", "repo_name": "TestRepo", "ref": "aaaaaaaa"}
        )
        assert isinstance(u, UnmanagedGitHubRefDependency)

        u = parse_dependency(
            {"github": "https://github.com/Test/TestRepo", "ref": "aaaaaaaa"}
        )
        assert isinstance(u, UnmanagedGitHubRefDependency)

        u = parse_dependency(
            {
                "zip_url": "https://github.com/Test/TestRepo",
                "subfolder": "unpackaged/pre",
            }
        )
        assert isinstance(u, UnmanagedZipURLDependency)


class TestGitHubTagResolver:
    def test_github_tag_resolver(self, project_config):
        dep = GitHubDynamicDependency(
            github="https://github.com/SFDO-Tooling/ReleasesRepo",
            tag="release/1.0",  # Not the most recent release
        )
        resolver = GitHubTagResolver()

        assert resolver.can_resolve(dep, project_config)
        assert resolver.resolve(dep, project_config) == (
            "tag_sha",
            PackageNamespaceVersionDependency(
                namespace="ccitestdep", version="1.0", package_name="CumulusCI-Test-Dep"
            ),
        )

    def test_github_tag_resolver__unmanaged(self, project_config):
        dep = GitHubDynamicDependency(
            github="https://github.com/SFDO-Tooling/ReleasesRepo",
            tag="release/2.0",
            unmanaged=True,
        )
        resolver = GitHubTagResolver()

        assert resolver.resolve(dep, project_config) == (
            "tag_sha",
            None,
        )

    def test_exception_no_managed_release(self, project_config):
        dep = GitHubDynamicDependency(
            github="https://github.com/SFDO-Tooling/UnmanagedRepo",  # This repo has no namespace
            tag="release/1.0",
            unmanaged=False,
        )
        resolver = GitHubTagResolver()

        with pytest.raises(DependencyResolutionError) as e:
            resolver.resolve(dep, project_config)
        assert "does not identify a managed release" in str(e.value)

    def test_can_resolve_negative(self, project_config):
        dep = GitHubDynamicDependency(
            github="https://github.com/SFDO-Tooling/ReleasesRepo"
        )
        resolver = GitHubTagResolver()

        assert not resolver.can_resolve(dep, project_config)

    def test_exception_no_tag_found(self, project_config):
        dep = GitHubDynamicDependency(
            github="https://github.com/SFDO-Tooling/ReleasesRepo",
            tag="release/3.0",
        )
        resolver = GitHubTagResolver()

        with pytest.raises(DependencyResolutionError) as e:
            resolver.resolve(dep, project_config)
        assert "No release found for tag" in str(e.value)


class TestGitHubReleaseTagResolver:
    def test_github_release_tag_resolver(self, project_config):
        dep = GitHubDynamicDependency(
            github="https://github.com/SFDO-Tooling/ReleasesRepo"
        )
        resolver = GitHubReleaseTagResolver()

        assert resolver.can_resolve(dep, project_config)
        assert resolver.resolve(dep, project_config) == (
            "tag_sha",
            PackageNamespaceVersionDependency(
                namespace="ccitestdep", version="2.0", package_name="CumulusCI-Test-Dep"
            ),
        )

    def test_beta_release_tag(self, project_config):
        dep = GitHubDynamicDependency(
            github="https://github.com/SFDO-Tooling/ReleasesRepo"
        )
        resolver = GitHubBetaReleaseTagResolver()

        assert resolver.can_resolve(dep, project_config)
        assert resolver.resolve(dep, project_config) == (
            "tag_sha",
            PackageNamespaceVersionDependency(
                namespace="ccitestdep",
                version="2.1 Beta 1",
                package_name="CumulusCI-Test-Dep",
            ),
        )


class TestGitHubUnmanagedHeadResolver:
    def test_unmanaged_head_resolver(self, project_config):
        dep = GitHubDynamicDependency(
            github="https://github.com/SFDO-Tooling/ReleasesRepo"
        )
        resolver = GitHubUnmanagedHeadResolver()

        assert resolver.can_resolve(dep, project_config)

        assert resolver.resolve(dep, project_config) == ("commit_sha", None)


class ConcreteGitHubReleaseBranchResolver(GitHubReleaseBranchResolver):
    def resolve(
        self, dep: GitHubDynamicDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[StaticDependency]]:
        return (None, None)


class TestGitHubReleaseBranchResolver:
    def test_is_valid_repo_context(self):
        pc = BaseProjectConfig(UniversalConfig())

        pc.repo_info["branch"] = "feature/232__test"
        pc.project__git["prefix_feature"] = "feature/"

        assert ConcreteGitHubReleaseBranchResolver().is_valid_repo_context(pc)

        pc.repo_info["branch"] = "main"
        assert not ConcreteGitHubReleaseBranchResolver().is_valid_repo_context(pc)

    def test_can_resolve(self):
        pc = BaseProjectConfig(UniversalConfig())

        pc.repo_info["branch"] = "feature/232__test"
        pc.project__git["prefix_feature"] = "feature/"

        gh = ConcreteGitHubReleaseBranchResolver()

        assert gh.can_resolve(
            GitHubDynamicDependency(github="https://github.com/SFDO-Tooling/Test"),
            pc,
        )

        assert not gh.can_resolve(ConcreteDynamicDependency(), pc)

    def test_get_release_id(self):
        pc = BaseProjectConfig(UniversalConfig())
        pc.repo_info["branch"] = "feature/232__test"
        pc.project__git["prefix_feature"] = "feature/"

        assert ConcreteGitHubReleaseBranchResolver().get_release_id(pc) == 232

    def test_get_release_id__not_release_branch(self):
        pc = BaseProjectConfig(UniversalConfig())
        with mock.patch.object(
            BaseProjectConfig, "repo_branch", new_callable=mock.PropertyMock
        ) as repo_branch:
            repo_branch.return_value = None

            with pytest.raises(DependencyResolutionError) as e:
                ConcreteGitHubReleaseBranchResolver().get_release_id(pc)

            assert "Cannot get current branch" in str(e)

    def test_get_release_id__no_git_data(self):
        pc = BaseProjectConfig(UniversalConfig())
        with mock.patch.object(
            BaseProjectConfig, "repo_branch", new_callable=mock.PropertyMock
        ) as repo_branch:
            repo_branch.return_value = "feature/test"
            pc.project__git["prefix_feature"] = "feature/"

            with pytest.raises(DependencyResolutionError) as e:
                ConcreteGitHubReleaseBranchResolver().get_release_id(pc)

            assert "Cannot get current release identifier" in str(e)


class TestGitHubReleaseBranch2GPResolver:
    def test_2gp_release_branch_resolver(self, project_config):
        project_config.repo_branch = "feature/232__test"
        project_config.project__git__prefix_feature = "feature/"

        resolver = GitHubReleaseBranchCommitStatusResolver()
        dep = GitHubDynamicDependency(
            github="https://github.com/SFDO-Tooling/TwoGPRepo"
        )

        assert resolver.can_resolve(dep, project_config)

        assert resolver.resolve(dep, project_config) == (
            "parent_sha",
            PackageVersionIdDependency(
                version_id="04t000000000000", package_name="CumulusCI-2GP-Test"
            ),
        )


class TestGitHubReleaseBranchExactMatch2GPResolver:
    def test_2gp_exact_branch_resolver(self, project_config):
        project_config.repo_branch = "feature/232__test"
        project_config.project__git__prefix_feature = "feature/"

        resolver = GitHubReleaseBranchExactMatchCommitStatusResolver()
        dep = GitHubDynamicDependency(
            github="https://github.com/SFDO-Tooling/TwoGPRepo"
        )

        assert resolver.can_resolve(dep, project_config)

        assert resolver.resolve(dep, project_config) == (
            "feature/232__test_sha",
            PackageVersionIdDependency(
                version_id="04t000000000001", package_name="CumulusCI-2GP-Test"
            ),
        )


class TestResolverAccess:
    def test_get_resolver(self):
        assert isinstance(
            get_resolver(
                DependencyResolutionStrategy.STRATEGY_STATIC_TAG_REFERENCE,
                GitHubDynamicDependency(github="https://github.com/SFDO-Tooling/Test"),
            ),
            GitHubTagResolver,
        )

    def test_get_resolver_stack__indirect(self):
        pc = BaseProjectConfig(UniversalConfig())

        strategy = get_resolver_stack(pc, "production")
        assert DependencyResolutionStrategy.STRATEGY_RELEASE_TAG in strategy
        assert DependencyResolutionStrategy.STRATEGY_BETA_RELEASE_TAG not in strategy

    def test_get_resolver_stack__customized_indirect(self):
        pc = BaseProjectConfig(UniversalConfig())

        pc.project__dependency_resolutions["preproduction"] = "include_beta"
        strategy = get_resolver_stack(pc, "preproduction")
        assert DependencyResolutionStrategy.STRATEGY_BETA_RELEASE_TAG in strategy

    def test_get_resolver_stack__direct(self):
        pc = BaseProjectConfig(UniversalConfig())

        strategy = get_resolver_stack(pc, "commit_status")
        assert (
            DependencyResolutionStrategy.STRATEGY_COMMIT_STATUS_RELEASE_BRANCH
            in strategy
        )

    def test_get_resolver_stack__fail(self):
        pc = BaseProjectConfig(UniversalConfig())

        with pytest.raises(CumulusCIException) as e:
            get_resolver_stack(pc, "bogus")

        assert "not found" in str(e)


class TestStaticDependencyResolution:
    def test_flatten(self, project_config):
        gh = GitHubDynamicDependency(github="https://github.com/SFDO-Tooling/RootRepo")

        assert get_static_dependencies(
            [gh], [DependencyResolutionStrategy.STRATEGY_RELEASE_TAG], project_config
        ) == [
            UnmanagedGitHubRefDependency(
                github="https://github.com/SFDO-Tooling/DependencyRepo",
                subfolder="unpackaged/pre/top",
                unmanaged=True,
                ref="tag_sha",
            ),
            PackageNamespaceVersionDependency(
                namespace="foo", version="1.1", package_name="DependencyRepo"
            ),
            UnmanagedGitHubRefDependency(
                github="https://github.com/SFDO-Tooling/DependencyRepo",
                subfolder="unpackaged/post/top",
                unmanaged=False,
                ref="tag_sha",
                namespace_inject="foo",
            ),
            UnmanagedGitHubRefDependency(
                github="https://github.com/SFDO-Tooling/RootRepo",
                subfolder="unpackaged/pre/first",
                unmanaged=True,
                ref="tag_sha",
            ),
            UnmanagedGitHubRefDependency(
                github="https://github.com/SFDO-Tooling/RootRepo",
                subfolder="unpackaged/pre/second",
                unmanaged=True,
                ref="tag_sha",
            ),
            PackageNamespaceVersionDependency(
                namespace="bar", version="2.0", package_name="RootRepo"
            ),
            UnmanagedGitHubRefDependency(
                github="https://github.com/SFDO-Tooling/RootRepo",
                subfolder="unpackaged/post/first",
                unmanaged=False,
                ref="tag_sha",
                namespace_inject="bar",
            ),
        ]
