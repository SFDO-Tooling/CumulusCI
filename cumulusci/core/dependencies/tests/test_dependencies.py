from cumulusci.core.config import project_config
from cumulusci.salesforce_api.package_install import (
    DEFAULT_PACKAGE_RETRY_OPTIONS,
    ManagedPackageInstallOptions,
)
from cumulusci.core.exceptions import DependencyResolutionError
from typing import Optional, Tuple
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.dependencies.dependencies import (
    DependencyResolutionStrategy,
    GitHubDynamicDependency,
    GitHubPackageDataMixin,
    GitHubRepoMixin,
    ManagedPackageDependency,
    Resolver,
    StaticDependency,
    DynamicDependency,
    UnmanagedDependency,
    parse_dependency,
)

from unittest import mock
import pytest

from pydantic import ValidationError, parse


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

        assert result == context.get_github_repo.return_value

    def test_mixin_failure(self):
        gh = GitHubRepoMixin()
        gh.github = "test"
        context = mock.Mock()
        context.get_github_repo.return_value = None

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

    def test_flatten_unpackaged(self):
        pass

    def test_flatten(self):
        pass


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
            m.package_version_id,
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
            m.package_version_id,
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
            context.get_github_repo.return_value, None, ref=d.ref
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
    pass


class TestGitHubReleaseTagResolver:
    def test_release_tag(self):
        pass

    def test_beta_release_tag(self):
        pass


class TestGitHubUnmanagedHeadResolver:
    pass


class TestGitHubReleaseBranchMixin:
    pass


class TestGitHubReleaseBranch2GPResolver:
    pass


class TestGitHubReleaseBranchExactMatch2GPResolver:
    pass


class TestResolverAccess:
    pass


class TestStaticDependencyResolution:
    pass