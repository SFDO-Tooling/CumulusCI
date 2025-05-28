import io
import os
from typing import List, Optional, Tuple
from unittest import mock
from zipfile import ZipFile

import pytest
from pydantic import ValidationError, root_validator

from cumulusci.core.config.org_config import OrgConfig, VersionInfo
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.dependencies.base import DynamicDependency, StaticDependency
from cumulusci.core.dependencies.dependencies import (
    PackageNamespaceVersionDependency,
    PackageVersionIdDependency,
    UnmanagedZipURLDependency,
    parse_dependency,
)
from cumulusci.core.dependencies.github import (
    GitHubDynamicDependency,
    GitHubDynamicSubfolderDependency,
    UnmanagedGitHubRefDependency,
)
from cumulusci.core.dependencies.resolvers import (
    AbstractResolver,
    DependencyResolutionStrategy,
)
from cumulusci.core.exceptions import DependencyResolutionError
from cumulusci.salesforce_api.package_install import (
    DEFAULT_PACKAGE_RETRY_OPTIONS,
    PackageInstallOptions,
)
from cumulusci.utils.version_strings import StrictVersion
from cumulusci.utils.ziputils import zip_subfolder


def _sync_vcs_and_url(values):
    # If only vcs is provided, set url to vcs
    if values.get("vcs") and not values.get("url"):
        values["url"] = values["vcs"]
    # If only url is provided, set vcs to url
    elif values.get("url") and not values.get("vcs"):
        values["vcs"] = values["url"]
    return values


class ConcreteDynamicDependency(DynamicDependency):
    ref: Optional[str]
    resolved: Optional[bool] = False
    vcs: str = "github"

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

    @root_validator(pre=True)
    def sync_vcs_and_url(cls, values):
        """Defined vcs should be assigned to url"""
        return _sync_vcs_and_url(values)


class MockResolver(AbstractResolver):
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


class MockBadResolver(AbstractResolver):
    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        return True

    def resolve(
        self, dep: DynamicDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[StaticDependency]]:
        raise DependencyResolutionError("Bad resolver")


class TestDynamicDependency:
    @mock.patch("cumulusci.core.dependencies.resolvers.get_resolver")
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
                DependencyResolutionStrategy.UNMANAGED_HEAD,
                DependencyResolutionStrategy.COMMIT_STATUS_PREVIOUS_RELEASE_BRANCH,
            ],
        )

        assert d.package_dependency == PackageNamespaceVersionDependency(
            namespace="foo", version="1.0"
        )
        assert d.ref == "aaaaaaaaaaaaaaaa"

    @mock.patch("cumulusci.core.dependencies.resolvers.get_resolver")
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
                DependencyResolutionStrategy.UNMANAGED_HEAD,
                DependencyResolutionStrategy.COMMIT_STATUS_PREVIOUS_RELEASE_BRANCH,
            ],
        )

        assert d.is_resolved
        resolvers[0].resolve.assert_called_once()
        d.resolve(
            mock.Mock(),
            [
                DependencyResolutionStrategy.UNMANAGED_HEAD,
                DependencyResolutionStrategy.COMMIT_STATUS_PREVIOUS_RELEASE_BRANCH,
            ],
        )
        assert d.is_resolved
        resolvers[0].resolve.assert_called_once()

    @mock.patch("cumulusci.core.dependencies.resolvers.get_resolver")
    def test_dynamic_dependency_resolution_fails(self, get_resolver):
        d = ConcreteDynamicDependency()
        resolvers = [MockBadResolver()]
        get_resolver.side_effect = resolvers

        with pytest.raises(DependencyResolutionError):
            d.resolve(mock.Mock(), [DependencyResolutionStrategy.UNMANAGED_HEAD])

    @mock.patch("cumulusci.core.dependencies.resolvers.get_resolver")
    def test_dynamic_dependency_resolution_no_results(self, get_resolver):
        d = ConcreteDynamicDependency()
        resolvers = [MockResolver("", None)]
        get_resolver.side_effect = resolvers

        with pytest.raises(DependencyResolutionError):
            d.resolve(mock.Mock(), [DependencyResolutionStrategy.UNMANAGED_HEAD])


class TestGitHubDynamicSubfolderDependency:
    def test_flatten(self):
        gh = GitHubDynamicSubfolderDependency(
            github="https://github.com/Test/TestRepo", subfolder="foo"
        )

        gh.ref = "aaaa"

        assert gh.is_unmanaged
        assert gh.flatten(mock.Mock()) == [
            UnmanagedGitHubRefDependency(
                github="https://github.com/Test/TestRepo",
                subfolder="foo",
                ref="aaaa",
                namespace_inject=None,
                namespace_strip=None,
            )
        ]

    def test_flatten__unresolved(self):
        context = mock.Mock()
        gh = GitHubDynamicSubfolderDependency(
            repo_owner="Test", repo_name="TestRepo", subfolder="foo"
        )

        with pytest.raises(DependencyResolutionError) as e:
            gh.flatten(context)

        assert "is not resolved" in str(e)

    def test_name(self):
        gh = GitHubDynamicSubfolderDependency(
            repo_owner="Test", repo_name="TestRepo", subfolder="foo"
        )
        assert gh.github in gh.name and gh.subfolder in gh.name

    def test_description(self):
        gh = GitHubDynamicSubfolderDependency(
            repo_owner="Test", repo_name="TestRepo", subfolder="foo"
        )
        gh.ref = "aaaa"
        assert (
            gh.github in gh.description
            and gh.subfolder in gh.description
            and gh.ref in gh.description
        )


class TestGitHubDynamicDependency:
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

    @mock.patch("cumulusci.core.dependencies.github.get_github_repo")
    def test_flatten(self, repo, project_config):
        repo.side_effect = project_config.get_github_repo_side_effect

        gh = GitHubDynamicDependency(github="https://github.com/SFDO-Tooling/RootRepo")
        gh.ref = "aaaaa"
        gh.package_dependency = PackageNamespaceVersionDependency(
            namespace="bar", version="2.0"
        )

        assert gh.flatten(project_config) == [
            GitHubDynamicDependency(
                github="https://github.com/SFDO-Tooling/DependencyRepo",
                password_env_name="DEP_PW",
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

    @mock.patch("cumulusci.core.dependencies.github.get_github_repo")
    def test_flatten__skip(self, repo, project_config):
        repo.side_effect = project_config.get_github_repo_side_effect
        gh = GitHubDynamicDependency(
            github="https://github.com/SFDO-Tooling/RootRepo",
            skip="unpackaged/pre/first",
        )
        gh.ref = "aaaaa"
        gh.package_dependency = PackageNamespaceVersionDependency(
            namespace="bar", version="2.0"
        )

        assert gh.flatten(project_config) == [
            GitHubDynamicDependency(
                github="https://github.com/SFDO-Tooling/DependencyRepo",
                password_env_name="DEP_PW",
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

    @mock.patch("cumulusci.core.dependencies.github.get_github_repo")
    def test_flatten__not_found(self, repo, project_config):
        repo.side_effect = project_config.get_github_repo_side_effect
        gh = GitHubDynamicDependency(
            github="https://github.com/SFDO-Tooling/NoUnmanagedPreRepo",
        )
        gh.ref = "aaaaa"
        gh.package_dependency = PackageNamespaceVersionDependency(
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

    @mock.patch("cumulusci.core.dependencies.github.get_github_repo")
    def test_flatten__bad_transitive_dep(self, repo, project_config):
        repo.side_effect = project_config.get_github_repo_side_effect
        gh = GitHubDynamicDependency(repo_owner="Test", repo_name="RootRepoBadDep")
        gh.ref = "aaaa"

        with pytest.raises(DependencyResolutionError) as e:
            gh.flatten(project_config)

        assert "transitive dependency could not be parsed" in str(e)

    @mock.patch("cumulusci.core.dependencies.github.get_github_repo")
    def test_flatten__unmanaged_src(self, repo, project_config):
        repo.side_effect = project_config.get_github_repo_side_effect
        gh = GitHubDynamicDependency(
            github="https://github.com/SFDO-Tooling/RootRepo",
            unmanaged=True,
        )
        gh.ref = "aaaaa"

        assert gh.flatten(project_config) == [
            GitHubDynamicDependency(
                github="https://github.com/SFDO-Tooling/DependencyRepo",
                password_env_name="DEP_PW",
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

    @mock.patch("cumulusci.core.dependencies.github.get_github_repo")
    def test_flatten__no_release(self, repo, project_config):
        repo.side_effect = project_config.get_github_repo_side_effect
        gh = GitHubDynamicDependency(
            github="https://github.com/SFDO-Tooling/RootRepo",
            unmanaged=False,
        )
        gh.ref = "aaaaa"

        with pytest.raises(DependencyResolutionError) as e:
            gh.flatten(project_config)

        assert "Could not find latest release" in str(e)

    def test_name(self):
        gh = GitHubDynamicDependency(github="https://github.com/SFDO-Tooling/RootRepo")
        assert gh.github in gh.name


class TestPackageNamespaceVersionDependency:
    @mock.patch(
        "cumulusci.core.dependencies.dependencies.install_package_by_namespace_version"
    )
    def test_install(self, install_package_by_namespace_version):
        m = PackageNamespaceVersionDependency(namespace="test", version="1.0")

        context = mock.Mock()
        org = OrgConfig({}, "dev")
        org._installed_packages = {}

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
    def test_install__already_installed(self, install_package_by_namespace_version):
        m = PackageNamespaceVersionDependency(namespace="test", version="1.0")

        context = mock.Mock()
        org = OrgConfig({}, "dev")
        org._installed_packages = {
            "test": [VersionInfo(id="04t000000000000", number=StrictVersion("1.0"))]
        }

        m.install(context, org)

        install_package_by_namespace_version.assert_not_called()

    @mock.patch(
        "cumulusci.core.dependencies.dependencies.install_package_by_namespace_version"
    )
    def test_install__newer_beta(self, install_package_by_namespace_version):
        m = PackageNamespaceVersionDependency(namespace="test", version="1.1 (Beta 4)")

        context = mock.Mock()
        org = OrgConfig({}, "dev")
        org._installed_packages = {
            "test": [VersionInfo(id="04t000000000000", number=StrictVersion("1.0"))]
        }

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
        org = OrgConfig({}, "dev")
        org._installed_packages = {}
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

    @mock.patch(
        "cumulusci.core.dependencies.dependencies.install_package_by_namespace_version"
    )
    def test_install__key_from_env(self, install_package_by_namespace_version):
        m = PackageNamespaceVersionDependency(
            namespace="foo", version="1.0", password_env_name="PW"
        )

        context = mock.Mock()
        org = OrgConfig({}, "dev")
        org._installed_packages = {}

        with mock.patch.dict(os.environ, PW="testpw"):
            m.install(context, org)

        opts = install_package_by_namespace_version.call_args[0][4]
        assert opts.password == "testpw"

    def test_name(self):
        assert (
            PackageNamespaceVersionDependency(namespace="foo", version="1.0").name
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
        org = OrgConfig({}, "dev")
        org._installed_packages = {}

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
    def test_install__already_installed(self, install_package_by_version_id):
        m = PackageVersionIdDependency(version_id="04t000000000000")

        context = mock.Mock()
        org = OrgConfig({}, "dev")
        org._installed_packages = {
            "04t000000000000": [VersionInfo(number="1.0", id="04t000000000000")]
        }

        m.install(context, org)

        install_package_by_version_id.assert_not_called()

    @mock.patch(
        "cumulusci.core.dependencies.dependencies.install_package_by_version_id"
    )
    def test_install__custom_options(self, install_package_by_version_id):
        m = PackageVersionIdDependency(version_id="04t000000000000")

        context = mock.Mock()
        org = OrgConfig({}, "dev")
        org._installed_packages = {}
        opts = PackageInstallOptions(password="test")

        m.install(context, org, options=opts)

        install_package_by_version_id.assert_called_once_with(
            context,
            org,
            m.version_id,
            opts,
            retry_options=DEFAULT_PACKAGE_RETRY_OPTIONS,
        )

    @mock.patch(
        "cumulusci.core.dependencies.dependencies.install_package_by_version_id"
    )
    def test_install__key_from_env(self, install_package_by_version_id):
        m = PackageVersionIdDependency(
            version_id="04t000000000000", password_env_name="PW"
        )

        context = mock.Mock()
        org = OrgConfig({}, "dev")
        org._installed_packages = {}

        with mock.patch.dict(os.environ, PW="testpw"):
            m.install(context, org)

        opts = install_package_by_version_id.call_args[0][3]
        assert opts.password == "testpw"

    def test_name(self):
        assert (
            PackageVersionIdDependency(
                package_name="foo", version_id="04t000000000000"
            ).name
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
            UnmanagedGitHubRefDependency(github="http://github.com")

        u = UnmanagedGitHubRefDependency(
            github="https://github.com/Test/TestRepo",
            ref="aaaaaaaa",
            namespace_token="obsolete but accepted",
            filename_token="obsolete but accepted",
        )

        u = UnmanagedGitHubRefDependency(
            repo_owner="Test", repo_name="TestRepo", ref="aaaaaaaa"
        )
        assert u.github == "https://github.com/Test/TestRepo"

    @mock.patch("cumulusci.core.dependencies.github.get_github_repo")
    @mock.patch("cumulusci.core.dependencies.base.download_extract_vcs_from_repo")
    @mock.patch("cumulusci.core.dependencies.base.MetadataPackageZipBuilder")
    @mock.patch("cumulusci.core.dependencies.base.ApiDeploy")
    def test_install(
        self, api_deploy_mock, zip_builder_mock, download_mock, repo_mock, init_git_repo
    ):
        repo_mock.return_value = init_git_repo
        d = UnmanagedGitHubRefDependency(
            github="http://github.com/Test/TestRepo", ref="aaaaaaaa"
        )

        with ZipFile(io.BytesIO(), "w") as zf:
            zf.writestr("package.xml", "test")
            download_mock.return_value = zf

            context = mock.Mock()
            org = mock.Mock()
            d.install(context, org)

            download_mock.assert_called_once_with(init_git_repo, ref=d.ref)
            zip_builder_mock.from_zipfile.assert_called_once_with(
                download_mock.return_value,
                path=None,
                options={
                    "unmanaged": True,
                    "namespace_inject": None,
                    "namespace_strip": None,
                },
                context=mock.ANY,
            )
            api_deploy_mock.assert_called_once_with(
                mock.ANY,  # The context object is checked below
                zip_builder_mock.from_zipfile.return_value.as_base64.return_value,
            )
            mock_task = api_deploy_mock.call_args_list[0][0][0]
            assert mock_task.org_config == org
            assert mock_task.project_config == context

            api_deploy_mock.return_value.assert_called_once()
            zf.close()

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
                github="http://github.com/Test/TestRepo", ref="aaaa"
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
            UnmanagedGitHubRefDependency(
                github="http://github.com/Test/TestRepo",
                subfolder="unpackaged/pre/first",
                ref="aaaa",
            ).name
            == "Deploy http://github.com/Test/TestRepo/unpackaged/pre/first"
        )

        assert (
            UnmanagedGitHubRefDependency(
                github="http://github.com/Test/TestRepo",
                ref="aaaa",
            ).name
            == "Deploy http://github.com/Test/TestRepo"
        )


class TestUnmanagedZipURLDependency:
    @mock.patch("cumulusci.core.dependencies.dependencies.download_extract_zip")
    @mock.patch("cumulusci.core.dependencies.base.MetadataPackageZipBuilder")
    @mock.patch("cumulusci.core.dependencies.base.ApiDeploy")
    def test_install(self, api_deploy_mock, zip_builder_mock, download_mock):
        d = UnmanagedZipURLDependency(zip_url="http://foo.com")

        with ZipFile(io.BytesIO(), "w") as zf:
            zf.writestr("src/package.xml", "test")
            download_mock.return_value = zf

            context = mock.Mock()
            org = mock.Mock()
            d.install(context, org)

            download_mock.assert_called_once_with(d.zip_url)

            zip_builder_mock.from_zipfile.assert_called_once_with(
                mock.ANY,
                options={
                    "unmanaged": True,
                    "namespace_inject": None,
                    "namespace_strip": None,
                },
                path=None,
                context=mock.ANY,
            )
            api_deploy_mock.assert_called_once_with(
                mock.ANY,  # The context object is checked below
                zip_builder_mock.from_zipfile.return_value.as_base64.return_value,
            )
            mock_task = api_deploy_mock.call_args_list[0][0][0]
            assert mock_task.org_config == org
            assert mock_task.project_config == context

            api_deploy_mock.return_value.assert_called_once()
            zf.close()

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
            UnmanagedZipURLDependency(zip_url="http://foo.com", subfolder="bar").name
            == "Deploy http://foo.com /bar"
        )

    @mock.patch("cumulusci.core.dependencies.base.MetadataPackageZipBuilder")
    @mock.patch("cumulusci.core.dependencies.dependencies.download_extract_zip")
    @mock.patch("cumulusci.core.dependencies.base.zip_subfolder")
    def test_get_metadata_package_zip_builder__mdapi_root(
        self, subfolder_mock, download_zip_mock, zipbuilder_mock
    ):
        with ZipFile(io.BytesIO(), "w") as zf:
            zf.writestr("src/package.xml", "test")

            dep = UnmanagedZipURLDependency(zip_url="http://foo.com")
            download_zip_mock.return_value = zf
            subfolder_mock.return_value = zip_subfolder(zf, "src")

            context = mock.Mock()
            org = mock.Mock()

            assert (
                dep.get_metadata_package_zip_builder(context, org)
                == zipbuilder_mock.from_zipfile.return_value
            )
            subfolder_mock.assert_called_once_with(zf, "src")
            zipbuilder_mock.from_zipfile.assert_called_once_with(
                subfolder_mock.return_value,
                path=None,
                options={
                    "unmanaged": True,
                    "namespace_inject": None,
                    "namespace_strip": None,
                },
                context=mock.ANY,
            )
            zf.close()

    @mock.patch("cumulusci.core.dependencies.base.MetadataPackageZipBuilder")
    @mock.patch("cumulusci.core.dependencies.dependencies.download_extract_zip")
    @mock.patch("cumulusci.core.dependencies.base.zip_subfolder")
    def test_get_metadata_package_zip_builder__mdapi_subfolder(
        self, subfolder_mock, download_zip_mock, zipbuilder_mock
    ):
        with ZipFile(io.BytesIO(), "w") as zf:

            zf.writestr("unpackaged/pre/first/package.xml", "test")

            dep = UnmanagedZipURLDependency(
                zip_url="http://foo.com", subfolder="unpackaged/pre/first"
            )
            download_zip_mock.return_value = zf
            subfolder_mock.return_value = zip_subfolder(zf, "unpackaged/pre/first")
            context = mock.Mock()
            org = mock.Mock()

            assert (
                dep.get_metadata_package_zip_builder(context, org)
                == zipbuilder_mock.from_zipfile.return_value
            )
            subfolder_mock.assert_called_once_with(zf, "unpackaged/pre/first")
            zipbuilder_mock.from_zipfile.assert_called_once_with(
                subfolder_mock.return_value,
                path=None,
                options={
                    "unmanaged": True,
                    "namespace_inject": None,
                    "namespace_strip": None,
                },
                context=mock.ANY,
            )
            zf.close()

    @mock.patch("cumulusci.core.dependencies.base.MetadataPackageZipBuilder")
    @mock.patch("cumulusci.core.dependencies.dependencies.download_extract_zip")
    @mock.patch("cumulusci.core.dependencies.base.zip_subfolder")
    @mock.patch("cumulusci.core.sfdx.sfdx")
    def test_get_metadata_package_zip_builder__sfdx(
        self, sfdx_mock, subfolder_mock, download_zip_mock, zipbuilder_mock
    ):
        zf = ZipFile(io.BytesIO(), "w")

        zf.writestr("force-app/main/default/classes/", "test")

        dep = UnmanagedZipURLDependency(zip_url="http://foo.com", subfolder="force-app")
        download_zip_mock.return_value = zf

        context = mock.Mock()
        org = mock.Mock()

        assert (
            dep.get_metadata_package_zip_builder(context, org)
            == zipbuilder_mock.from_zipfile.return_value
        )
        subfolder_mock.assert_not_called()
        zipbuilder_mock.from_zipfile.assert_called_once_with(
            None,
            path=mock.ANY,
            options={
                "unmanaged": True,
                "namespace_inject": None,
                "namespace_strip": None,
            },
            context=mock.ANY,
        )
        sfdx_mock.assert_called_once_with(
            "project convert source",
            args=["-d", mock.ANY, "-r", "force-app"],
            capture_output=True,
            check_return=True,
        )
        zf.close()


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

        u = parse_dependency(
            {
                "github": "https://github.com/Test/TestRepo",
                "ref": "aaaaaaaa",
                "namespace_inject": "ns",
                "collision_check": "false",
            }
        )
        assert isinstance(u, UnmanagedGitHubRefDependency)
