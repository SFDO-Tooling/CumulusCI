import io
import os
import pathlib
import zipfile
from base64 import b64encode
from tempfile import TemporaryDirectory
from unittest import mock

import pytest
import responses
import yaml

from cumulusci.core.config import BaseProjectConfig, ServiceConfig, UniversalConfig
from cumulusci.core.dependencies.github_resolvers import VCS_GITHUB
from cumulusci.core.exceptions import DependencyResolutionError, VcsApiError
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.tasks.release_notes.tests.utils import MockUtilBase
from cumulusci.utils import temporary_dir, touch
from cumulusci.utils.yaml.cumulusci_yml import (
    GitHubSourceModel,
    GitHubSourceRelease,
    LocalFolderSourceModel,
)

from ..source import GitHubEnterpriseSource, GitHubSource, LocalFolderSource


class TestGitHubSource(MockUtilBase):
    def setup_method(self):
        self.repo_api_url = "https://api.github.com/repos/TestOwner/TestRepo"
        universal_config = UniversalConfig()
        self.project_config = BaseProjectConfig(
            universal_config, repo_info={"root": os.getcwd()}
        )
        self.project_config.set_keychain(BaseProjectKeychain(self.project_config, None))
        self.project_config.config["sources"]["foo"] = {
            "github": "https://github.com/TestOwner/Foo",
            "release": "latest",
        }
        self.repo_root = TemporaryDirectory()
        self.project_config.keychain.set_service(
            "github",
            "test_alias",
            ServiceConfig(
                {
                    "username": "TestUser",
                    "token": "TestPass",
                    "email": "testuser@testdomain.com",
                }
            ),
        )

    def teardown_method(self):
        self.repo_root.cleanup()

    @responses.activate
    def test_resolve__default(self):
        # The default is to use resolution strategy `production`, which gets the latest release.
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner="TestOwner", name="TestRepo"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/releases/latest",
            json=self._get_expected_release("release/1.0"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/tags/release/1.0",
            json=self._get_expected_tag_ref("release/1.0", "tag_sha"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/tags/tag_sha",
            json=self._get_expected_tag("release/1.0", "commit_sha", "tag_sha"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/contents/cumulusci.yml?ref=commit_sha",
            json={
                "url": "https://api.github.com/repos/TestOwner/TestRepo/contents/cumulusci.yml?ref=commit_sha",
                "download_url": "https://api.github.com/repos/TestOwner/TestRepo/contents/cumulusci.yml?ref=commit_sha",
                "git_url": "https://api.github.com/repos/TestOwner/TestRepo/contents/cumulusci.yml?ref=commit_sha",
                "html_url": "https://api.github.com/repos/TestOwner/TestRepo/contents/cumulusci.yml?ref=commit_sha",
                "_links": {},
                "name": "cumulusci.yml",
                "path": "cumulusci.yml",
                "sha": "commit_sha",
                "size": 100,
                "type": "yaml",
                "encoding": "base64",
                "content": b64encode(
                    yaml.dump(
                        {
                            "project": {
                                "package": {
                                    "name_managed": "Test Product",
                                    "namespace": "ns",
                                }
                            }
                        }
                    ).encode("utf-8")
                ).decode("utf-8"),
            },
        )

        source = GitHubSource(
            self.project_config,
            GitHubSourceModel(github="https://github.com/TestOwner/TestRepo.git"),
        )
        assert source.vcs == VCS_GITHUB
        assert repr(source) == "<GitHubSource GitHub: TestOwner/TestRepo @ commit_sha>"

    @responses.activate
    def test_resolve__commit(self):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner="TestOwner", name="TestRepo"),
        )

        source = GitHubSource(
            self.project_config,
            GitHubSourceModel(
                github="https://github.com/TestOwner/TestRepo.git", commit="abcdef"
            ),
        )
        assert repr(source) == "<GitHubSource GitHub: TestOwner/TestRepo @ abcdef>"

    @responses.activate
    def test_resolve__ref(self):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner="TestOwner", name="TestRepo"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/main",
            json=self._get_expected_ref("main", "abcdef"),
        )

        source = GitHubSource(
            self.project_config,
            GitHubSourceModel(
                github="https://github.com/TestOwner/TestRepo.git", ref="main"
            ),
        )
        assert (
            repr(source) == "<GitHubSource GitHub: TestOwner/TestRepo @ main (abcdef)>"
        )

    @responses.activate
    def test_resolve__branch(self):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner="TestOwner", name="TestRepo"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/heads/main",
            json=self._get_expected_ref("main", "abcdef"),
        )

        source = GitHubSource(
            self.project_config,
            GitHubSourceModel(
                github="https://github.com/TestOwner/TestRepo.git", branch="main"
            ),
        )
        assert (
            repr(source) == "<GitHubSource GitHub: TestOwner/TestRepo @ main (abcdef)>"
        )

    @responses.activate
    def test_resolve__tag(self):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner="TestOwner", name="TestRepo"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/tags/release/1.0",
            json=self._get_expected_tag_ref("release/1.0", "abcdef"),
        )

        source = GitHubSource(
            self.project_config,
            GitHubSourceModel(
                github="https://github.com/TestOwner/TestRepo.git", tag="release/1.0"
            ),
        )
        assert (
            repr(source)
            == "<GitHubSource GitHub: TestOwner/TestRepo @ tags/release/1.0 (abcdef)>"
        )

    @responses.activate
    def test_resolve__latest_release(self):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner="TestOwner", name="TestRepo"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/releases/latest",
            json=self._get_expected_release("release/1.0"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/tags/release/1.0",
            json=self._get_expected_tag_ref("release/1.0", "tag_sha"),
        )

        source = GitHubSource(
            self.project_config,
            GitHubSourceModel(
                github="https://github.com/TestOwner/TestRepo.git", release="latest"
            ),
        )
        assert (
            repr(source)
            == "<GitHubSource GitHub: TestOwner/TestRepo @ tags/release/1.0 (tag_sha)>"
        )

    @responses.activate
    def test_resolve__latest_beta(self):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner="TestOwner", name="TestRepo"),
        )
        responses.add(
            "POST",
            "https://api.github.com/graphql",
            json=self._get_expected_prerelease_tag_gql("beta/1.0-Beta_1"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/releases/tags/beta/1.0-Beta_1",
            json=self._get_expected_release("beta/1.0-Beta_1"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/tags/beta/1.0-Beta_1",
            json=self._get_expected_tag_ref("beta/1.0-Beta_1", "tag_sha"),
        )

        source = GitHubSource(
            self.project_config,
            GitHubSourceModel(
                github="https://github.com/TestOwner/TestRepo.git",
                release="latest_beta",
            ),
        )
        assert (
            repr(source)
            == "<GitHubSource GitHub: TestOwner/TestRepo @ tags/beta/1.0-Beta_1 (tag_sha)>"
        )

    @responses.activate
    def test_resolve__previous_release(self):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner="TestOwner", name="TestRepo"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/releases",
            json=[
                self._get_expected_release("release/2.0"),
                self._get_expected_release("beta/1.0-Beta_1", prerelease=True),
                self._get_expected_release("release/1.0"),
            ],
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/tags/release/1.0",
            json=self._get_expected_tag_ref("release/1.0", "tag_sha"),
        )

        source = GitHubSource(
            self.project_config,
            GitHubSourceModel(
                github="https://github.com/TestOwner/TestRepo.git", release="previous"
            ),
        )
        assert (
            repr(source)
            == "<GitHubSource GitHub: TestOwner/TestRepo @ tags/release/1.0 (tag_sha)>"
        )

    @responses.activate
    def test_resolve__release_not_found(self):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner="TestOwner", name="TestRepo"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/releases/latest",
            status=404,
        )

        with pytest.raises(DependencyResolutionError):
            GitHubSource(
                self.project_config,
                GitHubSourceModel(
                    github="https://github.com/TestOwner/TestRepo.git", release="latest"
                ),
            )

    @responses.activate
    def test_fetch(self):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner="TestOwner", name="TestRepo"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/releases/latest",
            json=self._get_expected_release("release/1.0"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/tags/release/1.0",
            json=self._get_expected_tag_ref("release/1.0", "tag_sha"),
        )
        f = io.BytesIO()
        zf = zipfile.ZipFile(f, "w")
        zfi = zipfile.ZipInfo("toplevel/")
        zf.writestr(zfi, "")
        zf.writestr(
            "toplevel/cumulusci.yml",
            yaml.dump(
                {
                    "project": {
                        "package": {"name_managed": "Test Product", "namespace": "ns"}
                    }
                }
            ),
        )
        zf.close()
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/zipball/tag_sha",
            body=f.getvalue(),
            content_type="application/zip",
        )

        source = GitHubSource(
            self.project_config,
            GitHubSourceModel(
                github="https://github.com/TestOwner/TestRepo.git",
                release=GitHubSourceRelease.LATEST,
            ),
        )
        project_config = source.fetch()
        assert isinstance(project_config, BaseProjectConfig)
        assert pathlib.Path(project_config.repo_root).samefile(
            os.path.join(
                self.project_config.cache_dir, "projects", "TestRepo", "tag_sha"
            )
        )

    @responses.activate
    def test_fetch__nested_sources(self):
        def mock_repo(name: str, cci_yaml: dict):
            responses.add(
                method=responses.GET,
                url=f"https://api.github.com/repos/TestOwner/{name}",
                json=self._get_expected_repo(owner="TestOwner", name=name),
            )
            responses.add(
                "GET",
                f"https://api.github.com/repos/TestOwner/{name}/releases/latest",
                json=self._get_expected_release("release/1.0"),
            )
            responses.add(
                "GET",
                f"https://api.github.com/repos/TestOwner/{name}/git/ref/tags/release/1.0",
                json=self._get_expected_tag_ref("release/1.0", "tag_sha"),
            )
            f = io.BytesIO()
            zf = zipfile.ZipFile(f, "w")
            zfi = zipfile.ZipInfo("toplevel/")
            zf.writestr(zfi, "")
            zf.writestr(
                "toplevel/cumulusci.yml",
                yaml.dump(cci_yaml),
            )
            zf.close()
            responses.add(
                "GET",
                f"https://api.github.com/repos/TestOwner/{name}/zipball/tag_sha",
                body=f.getvalue(),
                content_type="application/zip",
            )

        mock_repo(
            "Foo",
            {
                "project": {"package": {"name": "Test Foo", "namespace": "foo"}},
                "sources": {
                    "bar": {
                        "github": "https://github.com/TestOwner/Bar",
                        "release": "latest",
                    }
                },
            },
        )
        mock_repo(
            "Bar", {"project": {"package": {"name": "Test Bar", "namespace": "bar"}}}
        )

        foo_config = self.project_config.get_namespace("foo")
        assert isinstance(foo_config, BaseProjectConfig)
        bar_config = foo_config.get_namespace("bar")
        assert isinstance(bar_config, BaseProjectConfig)

        assert (
            pathlib.Path(self.project_config.cache_dir) / "projects" / "Foo" / "tag_sha"
        ).exists()
        assert (
            pathlib.Path(self.project_config.cache_dir) / "projects" / "Bar" / "tag_sha"
        ).exists()
        assert not (
            pathlib.Path(self.project_config.cache_dir)
            / "projects"
            / "Foo"
            / "tag_sha"
            / ".cci"
        ).exists()

    @responses.activate
    @mock.patch("cumulusci.vcs.vcs_source.download_extract_vcs_from_repo")
    def test_fetch__cleans_up_after_failed_extract(
        self, download_extract_vcs_from_repo
    ):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner="TestOwner", name="TestRepo"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/releases/latest",
            json=self._get_expected_release("release/1.0"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/tags/release/1.0",
            json=self._get_expected_tag_ref("release/1.0", "tag_sha"),
        )
        # Set up a fake IOError while extracting the zipball
        download_extract_vcs_from_repo.return_value = mock.Mock(
            extractall=mock.Mock(side_effect=IOError)
        )

        source = GitHubSource(
            self.project_config,
            GitHubSourceModel(
                github="https://github.com/TestOwner/TestRepo.git",
                release=GitHubSourceRelease.LATEST,
            ),
        )
        with temporary_dir():
            with pytest.raises(IOError):
                source.fetch()
            assert not pathlib.Path(".cci", "projects", "TestRepo", "tag_sha").exists()

    @responses.activate
    def test_hash(self):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner="TestOwner", name="TestRepo"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/releases/latest",
            json=self._get_expected_release("release/1.0"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/tags/release/1.0",
            json=self._get_expected_tag_ref("release/1.0", "tag_sha"),
        )

        source = GitHubSource(
            self.project_config,
            GitHubSourceModel(
                github="https://github.com/TestOwner/TestRepo.git", release="latest"
            ),
        )
        assert hash(source) == hash(
            ("https://github.com/TestOwner/TestRepo", "tag_sha")
        )

    @responses.activate
    def test_frozenspec(self):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner="TestOwner", name="TestRepo"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/releases/latest",
            json=self._get_expected_release("release/1.0"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/tags/release/1.0",
            json=self._get_expected_tag_ref("release/1.0", "tag_sha"),
        )

        source = GitHubSource(
            self.project_config,
            GitHubSourceModel(
                github="https://github.com/TestOwner/TestRepo.git", release="latest"
            ),
        )
        assert source.frozenspec == {
            "vcs": "github",
            "url": "https://github.com/TestOwner/TestRepo",
            "commit": "tag_sha",
            "description": "tags/release/1.0",
        }

    @responses.activate
    def test_githubsource_init__404(self):
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo",
            status=404,
        )

        with pytest.raises(
            DependencyResolutionError, match="unable to find the repository"
        ):
            GitHubSource(
                self.project_config,
                GitHubSourceModel(
                    github="https://github.com/TestOwner/TestRepo.git", release="latest"
                ),
            )

    @responses.activate
    def test_githubsource_init__403(self):
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo",
            status=403,
            headers={"X-Github-Sso": "partial-results; organizations=0810298,20348880"},
        )

        with pytest.raises(VcsApiError):
            GitHubSource(
                self.project_config,
                GitHubSourceModel(
                    github="https://github.com/TestOwner/TestRepo.git", release="latest"
                ),
            )

    @responses.activate
    def test_resolve_github_enterprise__default(self):
        # The default is to use resolution strategy `production`, which gets the latest release.
        responses.add(
            method=responses.GET,
            url="https://git.enterprise.domain.com/api/v3/repos/TestOwner/TestRepo",
            json=self._get_expected_repo(owner="TestOwner", name="TestRepo"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/releases/latest",
            json=self._get_expected_release("release/1.0"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/tags/release/1.0",
            json=self._get_expected_tag_ref("release/1.0", "tag_sha"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/tags/tag_sha",
            json=self._get_expected_tag("release/1.0", "commit_sha", "tag_sha"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/contents/cumulusci.yml?ref=commit_sha",
            json={
                "url": "https://api.github.com/repos/TestOwner/TestRepo/contents/cumulusci.yml?ref=commit_sha",
                "download_url": "https://api.github.com/repos/TestOwner/TestRepo/contents/cumulusci.yml?ref=commit_sha",
                "git_url": "https://api.github.com/repos/TestOwner/TestRepo/contents/cumulusci.yml?ref=commit_sha",
                "html_url": "https://api.github.com/repos/TestOwner/TestRepo/contents/cumulusci.yml?ref=commit_sha",
                "_links": {},
                "name": "cumulusci.yml",
                "path": "cumulusci.yml",
                "sha": "commit_sha",
                "size": 100,
                "type": "yaml",
                "encoding": "base64",
                "content": b64encode(
                    yaml.dump(
                        {
                            "project": {
                                "package": {
                                    "name_managed": "Test Product",
                                    "namespace": "ns",
                                }
                            }
                        }
                    ).encode("utf-8")
                ).decode("utf-8"),
            },
        )

        self.project_config.keychain.set_service(
            "github_enterprise",
            "ent",
            ServiceConfig(
                {
                    "username": "testusername",
                    "email": "test@domain.com",
                    "token": "ATOKEN",
                    "server_domain": "git.enterprise.domain.com",
                }
            ),
        )

        source = GitHubEnterpriseSource(
            self.project_config,
            GitHubSourceModel(
                github="https://git.enterprise.domain.com/TestOwner/TestRepo.git"
            ),
        )
        assert repr(source) == "<GitHubSource GitHub: TestOwner/TestRepo @ commit_sha>"


class TestLocalFolderSource:
    def test_fetch(self):
        project_config = BaseProjectConfig(
            UniversalConfig(),
            repo_info={"root": os.getcwd()},
        )
        with temporary_dir() as d:
            touch("cumulusci.yml")
            source = LocalFolderSource(project_config, LocalFolderSourceModel(path=d))
            project_config = source.fetch()
            assert project_config.repo_root == os.path.realpath(d)

    def test_hash(self):
        project_config = BaseProjectConfig(UniversalConfig())
        with temporary_dir() as d:
            source = LocalFolderSource(project_config, LocalFolderSourceModel(path=d))
            assert hash(source) == hash((source.path,))

    def test_repr(self):
        project_config = BaseProjectConfig(UniversalConfig())
        with temporary_dir() as d:
            source = LocalFolderSource(project_config, LocalFolderSourceModel(path=d))
            assert repr(source) == f"<LocalFolderSource Local folder: {d}>"

    def test_frozenspec(self):
        project_config = BaseProjectConfig(UniversalConfig())
        with temporary_dir() as d:
            source = LocalFolderSource(project_config, LocalFolderSourceModel(path=d))
            with pytest.raises(NotImplementedError):
                source.frozenspec
