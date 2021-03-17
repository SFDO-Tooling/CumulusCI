from github3.exceptions import NotFoundError
from cumulusci.salesforce_api.package_install import (
    DEFAULT_PACKAGE_RETRY_OPTIONS,
    ManagedPackageInstallOptions,
)
from cumulusci.core.exceptions import CumulusCIException, DependencyResolutionError
from typing import Optional, Tuple
from cumulusci.core.config import UniversalConfig
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.dependencies.dependencies import (
    DependencyResolutionStrategy,
    GitHubBetaReleaseTagResolver,
    GitHubDynamicDependency,
    GitHubPackageDataMixin,
    GitHubReleaseBranch2GPResolver,
    GitHubReleaseBranchExactMatch2GPResolver,
    GitHubReleaseBranchMixin,
    GitHubReleaseTagResolver,
    GitHubRepoMixin,
    GitHubTagResolver,
    GitHubUnmanagedHeadResolver,
    ManagedPackageDependency,
    Resolver,
    StaticDependency,
    DynamicDependency,
    UnmanagedDependency,
    get_resolver,
    get_resolver_stack,
    get_static_dependencies,
    parse_dependency,
)
from cumulusci.utils.git import split_repo_url

from unittest import mock
import pytest

from pydantic import ValidationError, parse

from cumulusci.core.tests.test_config import (
    DummyContents,
    DummyRelease,
    DummyRepository,
    DummyGithub,
)


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
            "RootRepo": ROOT_REPO,
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

    @property
    def is_resolved(self):
        return False


class MockResolver(Resolver):
    def __init__(
        self,
        resolve_ref: Optional[str] = None,
        resolve_dep: Optional[ManagedPackageDependency] = None,
    ):
        self.ref = resolve_ref
        self.dep = resolve_dep

    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        return bool(self.dep and self.ref)

    def resolve(
        self, dep: DynamicDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional["ManagedPackageDependency"]]:
        return self.ref, self.dep


class MockBadResolver(Resolver):
    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        return True

    def resolve(
        self, dep: DynamicDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional["ManagedPackageDependency"]]:
        raise DependencyResolutionError("Bad resolver")


class TestDynamicDependency:
    @mock.patch("cumulusci.core.dependencies.dependencies.get_resolver")
    def test_dynamic_dependency(self, get_resolver):
        d = ConcreteDynamicDependency()
        resolvers = [
            MockResolver(),
            MockResolver(
                "aaaaaaaaaaaaaaaa",
                ManagedPackageDependency(namespace="foo", version="1.0"),
            ),
        ]
        get_resolver.side_effect = resolvers

        d.resolve(
            mock.Mock(),
            [
                DependencyResolutionStrategy.STRATEGY_UNMANAGED_HEAD,
                DependencyResolutionStrategy.STRATEGY_2GP_PREVIOUS_RELEASE_BRANCH,
            ],
        )

        assert d.managed_dependency == ManagedPackageDependency(
            namespace="foo", version="1.0"
        )
        assert d.ref == "aaaaaaaaaaaaaaaa"

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


class TestGithubRepoMixin:
    def test_mixin(self):
        gh = GitHubRepoMixin()
        gh.github = "test"
        context = mock.Mock()

        result = gh.get_repo(context)

        assert result == context.get_repo_from_url.return_value

    def test_mixin_failure(self):
        gh = GitHubRepoMixin()
        gh.github = "test"
        context = mock.Mock()
        context.get_repo_from_url.return_value = None

        with pytest.raises(DependencyResolutionError):
            gh.get_repo(context)


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

    def test_flatten(self, project_config):
        gh = GitHubDynamicDependency(github="https://github.com/SFDO-Tooling/RootRepo")
        gh.ref = "aaaaa"
        gh.managed_dependency = ManagedPackageDependency(namespace="bar", version="2.0")

        assert gh.flatten(project_config) == [
            GitHubDynamicDependency(
                github="https://github.com/SFDO-Tooling/DependencyRepo"
            ),
            UnmanagedDependency(
                github="https://github.com/SFDO-Tooling/RootRepo",
                subfolder="unpackaged/pre/first",
                unmanaged=True,
                ref="aaaaa",
            ),
            UnmanagedDependency(
                github="https://github.com/SFDO-Tooling/RootRepo",
                subfolder="unpackaged/pre/second",
                unmanaged=True,
                ref="aaaaa",
            ),
            ManagedPackageDependency(namespace="bar", version="2.0"),
            UnmanagedDependency(
                github="https://github.com/SFDO-Tooling/RootRepo",
                subfolder="unpackaged/post/first",
                unmanaged=False,
                ref="aaaaa",
                namespace_inject="bar",
            ),
        ]

    def test_flatten__unresolved(self):
        context = mock.Mock()
        gh = GitHubDynamicDependency(repo_owner="Test", repo_name="TestRepo")

        with pytest.raises(DependencyResolutionError) as e:
            gh.flatten(context)

        assert "is not resolved" in str(e)


class TestManagedPackageDependency:
    def test_validation(self):
        with pytest.raises(ValidationError):
            ManagedPackageDependency(namespace="test")
        with pytest.raises(ValidationError):
            ManagedPackageDependency(
                namespace="test", version="1.0", version_id="04t000000000000"
            )

    @mock.patch("cumulusci.core.dependencies.dependencies.install_1gp_package_version")
    def test_install__1gp(self, install_1gp_package_version):
        m = ManagedPackageDependency(namespace="test", version="1.0")

        context = mock.Mock()
        org = mock.Mock()

        m.install(context, org)

        install_1gp_package_version.assert_called_once_with(
            context,
            org,
            m.namespace,
            m.version,
            ManagedPackageInstallOptions(),
            retry_options=DEFAULT_PACKAGE_RETRY_OPTIONS,
        )

    @mock.patch("cumulusci.core.dependencies.dependencies.install_package_version")
    def test_install__2gp(self, install_package_version):
        m = ManagedPackageDependency(version_id="04t000000000000")

        context = mock.Mock()
        org = mock.Mock()

        m.install(context, org)

        install_package_version.assert_called_once_with(
            context,
            org,
            m.version_id,
            ManagedPackageInstallOptions(),
            retry_options=DEFAULT_PACKAGE_RETRY_OPTIONS,
        )

    @mock.patch("cumulusci.core.dependencies.dependencies.install_package_version")
    def test_install__custom_options(self, install_package_version):
        m = ManagedPackageDependency(version_id="04t000000000000")

        context = mock.Mock()
        org = mock.Mock()
        opts = ManagedPackageInstallOptions(password="test")

        m.install(context, org, options=opts)

        install_package_version.assert_called_once_with(
            context,
            org,
            m.version_id,
            opts,
            retry_options=DEFAULT_PACKAGE_RETRY_OPTIONS,
        )

    def test_name(self):
        assert (
            str(ManagedPackageDependency(namespace="foo", version="1.0"))
            == "Install foo 1.0"
        )

    def test_package_name(self):
        assert (
            ManagedPackageDependency(
                namespace="foo", version="1.0", package_name="Foo"
            ).package
            == "Foo"
        )

        assert ManagedPackageDependency(namespace="foo", version="1.0").package == "foo"

        assert (
            ManagedPackageDependency(version_id="04t000000000000").package
            == "Unknown Package"
        )


class TestUnmanagedDependency:
    def test_validation(self):
        with pytest.raises(ValidationError):
            UnmanagedDependency()
        with pytest.raises(ValidationError):
            UnmanagedDependency(zip_url="http://foo.com", github="http://github.com")
        with pytest.raises(ValidationError):
            UnmanagedDependency(zip_url="http://foo.com", repo_owner="Test")
        with pytest.raises(ValidationError):
            UnmanagedDependency(github="http://github.com", repo_owner="Test")

        u = UnmanagedDependency(
            github="https://github.com/Test/TestRepo", ref="aaaaaaaa"
        )
        assert u.repo_owner == "Test"
        assert u.repo_name == "TestRepo"

        u = UnmanagedDependency(repo_owner="Test", repo_name="TestRepo", ref="aaaaaaaa")
        assert u.github == "https://github.com/Test/TestRepo"

    @mock.patch("cumulusci.core.dependencies.dependencies.download_extract_zip")
    @mock.patch("cumulusci.core.dependencies.dependencies.MetadataPackageZipBuilder")
    @mock.patch("cumulusci.core.dependencies.dependencies.ApiDeploy")
    def test_install__zip_url(self, api_deploy_mock, zip_builder_mock, download_mock):
        d = UnmanagedDependency(zip_url="http://foo.com", subfolder="bar")

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

    @mock.patch(
        "cumulusci.core.dependencies.dependencies.download_extract_github_from_repo"
    )
    @mock.patch("cumulusci.core.dependencies.dependencies.MetadataPackageZipBuilder")
    @mock.patch("cumulusci.core.dependencies.dependencies.ApiDeploy")
    def test_install__github(self, api_deploy_mock, zip_builder_mock, download_mock):
        d = UnmanagedDependency(
            github="http://github.com/Test/TestRepo", ref="aaaaaaaa"
        )

        context = mock.Mock()
        org = mock.Mock()
        d.install(context, org)

        # All the common logic is tested above in test_install__zip_url()

        download_mock.assert_called_once_with(
            context.get_repo_from_url.return_value, None, ref=d.ref
        )

    def test_get_unmanaged(self):
        org = mock.Mock()
        org.installed_packages = {"foo": "1.0"}
        assert (
            UnmanagedDependency(
                zip_url="http://foo.com", unmanaged=True
            )._get_unmanaged(org)
            is True
        )
        assert (
            UnmanagedDependency(
                zip_url="http://foo.com", namespace_inject="foo"
            )._get_unmanaged(org)
            is False
        )
        assert (
            UnmanagedDependency(
                zip_url="http://foo.com", namespace_inject="bar"
            )._get_unmanaged(org)
            is True
        )

    def test_name(self):
        assert (
            str(UnmanagedDependency(zip_url="http://foo.com", subfolder="bar"))
            == "Deploy http://foo.com /bar"
        )


class TestParseDependency:
    def test_parse_managed_package_dep(self):
        m = parse_dependency({"version": "1.0", "namespace": "foo"})

        assert isinstance(m, ManagedPackageDependency)

    def test_parse_github_dependency(self):
        g = parse_dependency({"github": "https://github.com/Test/TestRepo"})
        assert isinstance(g, GitHubDynamicDependency)

        g = parse_dependency({"repo_owner": "Test", "repo_name": "TestRepo"})
        assert isinstance(g, GitHubDynamicDependency)

    def test_parse_unmanaged_dependency(self):
        u = parse_dependency(
            {"repo_owner": "Test", "repo_name": "TestRepo", "ref": "aaaaaaaa"}
        )
        assert isinstance(u, UnmanagedDependency)

        u = parse_dependency(
            {"github": "https://github.com/Test/TestRepo", "ref": "aaaaaaaa"}
        )
        assert isinstance(u, UnmanagedDependency)

        u = parse_dependency(
            {
                "zip_url": "https://github.com/Test/TestRepo",
                "subfolder": "unpackaged/pre",
            }
        )
        assert isinstance(u, UnmanagedDependency)


class TestGitHubPackageDataMixin:
    def test_get_package_data(self):
        content = b"""
project:
    package:
        namespace: foo"""

        repo = mock.Mock()
        repo.file_contents.return_value.decoded = content

        m = GitHubPackageDataMixin()
        assert m._get_package_data(repo, "aaaaaaaa") == ("Package", "foo")


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
            ManagedPackageDependency(
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
            ManagedPackageDependency(
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
            ManagedPackageDependency(
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


class TestGitHubReleaseBranchMixin:
    def test_is_valid_repo_context(self):
        pc = BaseProjectConfig(UniversalConfig())

        pc.repo_info["branch"] = "feature/232__test"
        pc.project__git["prefix_feature"] = "feature/"

        assert GitHubReleaseBranchMixin().is_valid_repo_context(pc)

        pc.repo_info["branch"] = "main"
        assert not GitHubReleaseBranchMixin().is_valid_repo_context(pc)

    def test_can_resolve(self):
        pc = BaseProjectConfig(UniversalConfig())

        pc.repo_info["branch"] = "feature/232__test"
        pc.project__git["prefix_feature"] = "feature/"

        gh = GitHubReleaseBranchMixin()

        assert gh.can_resolve(
            GitHubDynamicDependency(github="https://github.com/SFDO-Tooling/Test"),
            pc,
        )

        assert not gh.can_resolve(ConcreteDynamicDependency(), pc)

    def test_get_release_id(self):
        pc = BaseProjectConfig(UniversalConfig())
        pc.repo_info["branch"] = "feature/232__test"
        pc.project__git["prefix_feature"] = "feature/"

        assert GitHubReleaseBranchMixin().get_release_id(pc) == 232

    def test_get_release_id__not_release_branch(self):
        pc = BaseProjectConfig(UniversalConfig())
        with mock.patch.object(
            BaseProjectConfig, "repo_branch", new_callable=mock.PropertyMock
        ) as repo_branch:
            repo_branch.return_value = None

            with pytest.raises(DependencyResolutionError) as e:
                GitHubReleaseBranchMixin().get_release_id(pc)

            assert "Cannot get current branch" in str(e)

    def test_get_release_id__no_git_data(self):
        pc = BaseProjectConfig(UniversalConfig())
        with mock.patch.object(
            BaseProjectConfig, "repo_branch", new_callable=mock.PropertyMock
        ) as repo_branch:
            repo_branch.return_value = "feature/test"
            pc.project__git["prefix_feature"] = "feature/"

            with pytest.raises(DependencyResolutionError) as e:
                GitHubReleaseBranchMixin().get_release_id(pc)

            assert "Cannot get current release identifier" in str(e)


class TestGitHubReleaseBranch2GPResolver:
    def test_2gp_release_branch_resolver(self, project_config):
        project_config.repo_branch = "feature/232__test"
        project_config.project__git__prefix_feature = "feature/"

        resolver = GitHubReleaseBranch2GPResolver()
        dep = GitHubDynamicDependency(
            github="https://github.com/SFDO-Tooling/TwoGPRepo"
        )

        assert resolver.can_resolve(dep, project_config)

        assert resolver.resolve(dep, project_config) == (
            "parent_sha",
            ManagedPackageDependency(
                version_id="04t000000000000", package_name="CumulusCI-2GP-Test"
            ),
        )


class TestGitHubReleaseBranchExactMatch2GPResolver:
    def test_2gp_exact_branch_resolver(self, project_config):
        project_config.repo_branch = "feature/232__test"
        project_config.project__git__prefix_feature = "feature/"

        resolver = GitHubReleaseBranchExactMatch2GPResolver()
        dep = GitHubDynamicDependency(
            github="https://github.com/SFDO-Tooling/TwoGPRepo"
        )

        assert resolver.can_resolve(dep, project_config)

        assert resolver.resolve(dep, project_config) == (
            "feature/232__test_sha",
            ManagedPackageDependency(
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

        strategy = get_resolver_stack(pc, "exact_2gp")
        assert DependencyResolutionStrategy.STRATEGY_2GP_RELEASE_BRANCH in strategy

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
            UnmanagedDependency(
                github="https://github.com/SFDO-Tooling/DependencyRepo",
                subfolder="unpackaged/pre/top",
                unmanaged=True,
                ref="tag_sha",
            ),
            ManagedPackageDependency(
                namespace="foo", version="1.1", package_name="DependencyRepo"
            ),
            UnmanagedDependency(
                github="https://github.com/SFDO-Tooling/DependencyRepo",
                subfolder="unpackaged/post/top",
                unmanaged=False,
                ref="tag_sha",
                namespace_inject="foo",
            ),
            UnmanagedDependency(
                github="https://github.com/SFDO-Tooling/RootRepo",
                subfolder="unpackaged/pre/first",
                unmanaged=True,
                ref="tag_sha",
            ),
            UnmanagedDependency(
                github="https://github.com/SFDO-Tooling/RootRepo",
                subfolder="unpackaged/pre/second",
                unmanaged=True,
                ref="tag_sha",
            ),
            ManagedPackageDependency(
                namespace="bar", version="2.0", package_name="RootRepo"
            ),
            UnmanagedDependency(
                github="https://github.com/SFDO-Tooling/RootRepo",
                subfolder="unpackaged/post/first",
                unmanaged=False,
                ref="tag_sha",
                namespace_inject="bar",
            ),
        ]
