from unittest import mock
import io
import os
import pathlib
import unittest
import yaml
import zipfile

import pytest
import responses

from ..source import GitHubSource
from ..source import LocalFolderSource
from cumulusci.core.config import UniversalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import ServiceConfig
from cumulusci.core.exceptions import DependencyResolutionError
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.tasks.release_notes.tests.utils import MockUtil
from cumulusci.utils import temporary_dir
from cumulusci.utils import touch


class TestGitHubSource(unittest.TestCase, MockUtil):
    def setUp(self):
        self.repo_api_url = "https://api.github.com/repos/TestOwner/TestRepo"
        universal_config = UniversalConfig()
        self.project_config = BaseProjectConfig(universal_config)
        self.project_config.set_keychain(BaseProjectKeychain(self.project_config, None))
        self.project_config.keychain.set_service(
            "github",
            ServiceConfig(
                {
                    "username": "TestUser",
                    "password": "TestPass",
                    "email": "testuser@testdomain.com",
                }
            ),
        )

    @responses.activate
    def test_resolve__default(self):
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
            "https://api.github.com/repos/TestOwner/TestRepo/git/refs/tags/release/1.0",
            json=self._get_expected_tag_ref("release/1.0", "tag_sha"),
        )

        source = GitHubSource(
            self.project_config, {"github": "https://github.com/TestOwner/TestRepo.git"}
        )
        assert (
            repr(source)
            == "<GitHubSource GitHub: TestOwner/TestRepo @ tags/release/1.0 (tag_sha)>"
        )

    @responses.activate
    def test_resolve__default_no_release(self):
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
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/refs/heads/main",
            json=self._get_expected_ref("heads/main", "abcdef"),
        )

        source = GitHubSource(
            self.project_config, {"github": "https://github.com/TestOwner/TestRepo.git"}
        )
        assert (
            repr(source) == "<GitHubSource GitHub: TestOwner/TestRepo @ main (abcdef)>"
        )

    @responses.activate
    def test_resolve__commit(self):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner="TestOwner", name="TestRepo"),
        )

        source = GitHubSource(
            self.project_config,
            {"github": "https://github.com/TestOwner/TestRepo.git", "commit": "abcdef"},
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
            "https://api.github.com/repos/TestOwner/TestRepo/git/refs/main",
            json=self._get_expected_ref("main", "abcdef"),
        )

        source = GitHubSource(
            self.project_config,
            {"github": "https://github.com/TestOwner/TestRepo.git", "ref": "main"},
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
            "https://api.github.com/repos/TestOwner/TestRepo/git/refs/heads/main",
            json=self._get_expected_ref("main", "abcdef"),
        )

        source = GitHubSource(
            self.project_config,
            {"github": "https://github.com/TestOwner/TestRepo.git", "branch": "main"},
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
            "https://api.github.com/repos/TestOwner/TestRepo/git/refs/tags/release/1.0",
            json=self._get_expected_tag_ref("release/1.0", "abcdef"),
        )

        source = GitHubSource(
            self.project_config,
            {
                "github": "https://github.com/TestOwner/TestRepo.git",
                "tag": "release/1.0",
            },
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
            "https://api.github.com/repos/TestOwner/TestRepo/git/refs/tags/release/1.0",
            json=self._get_expected_tag_ref("release/1.0", "tag_sha"),
        )

        source = GitHubSource(
            self.project_config,
            {
                "github": "https://github.com/TestOwner/TestRepo.git",
                "release": "latest",
            },
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
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/releases",
            json=[self._get_expected_release("beta/1.0-Beta_1")],
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/refs/tags/beta/1.0-Beta_1",
            json=self._get_expected_tag_ref("beta/1.0-Beta_1", "tag_sha"),
        )

        source = GitHubSource(
            self.project_config,
            {
                "github": "https://github.com/TestOwner/TestRepo.git",
                "release": "latest_beta",
            },
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
            "https://api.github.com/repos/TestOwner/TestRepo/git/refs/tags/release/1.0",
            json=self._get_expected_tag_ref("release/1.0", "tag_sha"),
        )

        source = GitHubSource(
            self.project_config,
            {
                "github": "https://github.com/TestOwner/TestRepo.git",
                "release": "previous",
            },
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
                {
                    "github": "https://github.com/TestOwner/TestRepo.git",
                    "release": "latest",
                },
            )

    @responses.activate
    def test_resolve__bogus_release(self):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner="TestOwner", name="TestRepo"),
        )

        with pytest.raises(DependencyResolutionError):
            GitHubSource(
                self.project_config,
                {
                    "github": "https://github.com/TestOwner/TestRepo.git",
                    "release": "bogus",
                },
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
            "https://api.github.com/repos/TestOwner/TestRepo/git/refs/tags/release/1.0",
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
            self.project_config, {"github": "https://github.com/TestOwner/TestRepo.git"}
        )
        with temporary_dir() as d:
            project_config = source.fetch()
            assert isinstance(project_config, BaseProjectConfig)
            assert project_config.repo_root == os.path.join(
                os.path.realpath(d), ".cci", "projects", "TestRepo", "tag_sha"
            )

    @responses.activate
    @mock.patch("cumulusci.core.source.github.download_extract_github")
    def test_fetch__cleans_up_after_failed_extract(self, download_extract_github):
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
            "https://api.github.com/repos/TestOwner/TestRepo/git/refs/tags/release/1.0",
            json=self._get_expected_tag_ref("release/1.0", "tag_sha"),
        )
        # Set up a fake IOError while extracting the zipball
        download_extract_github.return_value = mock.Mock(
            extractall=mock.Mock(side_effect=IOError)
        )

        source = GitHubSource(
            self.project_config, {"github": "https://github.com/TestOwner/TestRepo.git"}
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
            "https://api.github.com/repos/TestOwner/TestRepo/git/refs/tags/release/1.0",
            json=self._get_expected_tag_ref("release/1.0", "tag_sha"),
        )

        source = GitHubSource(
            self.project_config, {"github": "https://github.com/TestOwner/TestRepo.git"}
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
            "https://api.github.com/repos/TestOwner/TestRepo/git/refs/tags/release/1.0",
            json=self._get_expected_tag_ref("release/1.0", "tag_sha"),
        )

        source = GitHubSource(
            self.project_config, {"github": "https://github.com/TestOwner/TestRepo.git"}
        )
        assert source.frozenspec == {
            "github": "https://github.com/TestOwner/TestRepo",
            "commit": "tag_sha",
            "description": "tags/release/1.0",
        }


class TestLocalFolderSource:
    def test_fetch(self):
        project_config = BaseProjectConfig(UniversalConfig())
        with temporary_dir() as d:
            touch("cumulusci.yml")
            source = LocalFolderSource(project_config, {"path": d})
            project_config = source.fetch()
            assert project_config.repo_root == os.path.realpath(d)

    def test_hash(self):
        project_config = BaseProjectConfig(UniversalConfig())
        with temporary_dir() as d:
            source = LocalFolderSource(project_config, {"path": d})
            assert hash(source) == hash((source.path,))

    def test_repr(self):
        project_config = BaseProjectConfig(UniversalConfig())
        with temporary_dir() as d:
            source = LocalFolderSource(project_config, {"path": d})
            assert repr(source) == f"<LocalFolderSource Local folder: {d}>"

    def test_frozenspec(self):
        project_config = BaseProjectConfig(UniversalConfig())
        with temporary_dir() as d:
            source = LocalFolderSource(project_config, {"path": d})
            with pytest.raises(NotImplementedError):
                source.frozenspec
