# -*- coding: utf-8 -*-
from distutils.version import StrictVersion
import json
import os
import pathlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from unittest import mock
import responses
import yaml

from github3.exceptions import NotFoundError
from cumulusci.core.config import BaseConfig
from cumulusci.core.config import UniversalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import BaseTaskFlowConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config.OrgConfig import VersionInfo
from cumulusci.core.exceptions import ConfigError
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.exceptions import DependencyResolutionError
from cumulusci.core.exceptions import GithubException
from cumulusci.core.exceptions import KeychainNotFound
from cumulusci.core.exceptions import FlowNotFoundError
from cumulusci.core.exceptions import NamespaceNotFoundError
from cumulusci.core.exceptions import SalesforceCredentialsException
from cumulusci.core.exceptions import TaskNotFoundError
from cumulusci.core.source import LocalFolderSource
from cumulusci.utils import temporary_dir
from cumulusci.utils import touch
from cumulusci.tests.util import DummyKeychain


class TestBaseConfig(unittest.TestCase):
    def test_getattr_toplevel_key(self):
        config = BaseConfig()
        config.config = {"foo": "bar"}
        self.assertEqual(config.foo, "bar")

    def test_getattr_toplevel_key_missing(self):
        config = BaseConfig()
        config.config = {}
        self.assertEqual(config.foo, None)

    def test_getattr_child_key(self):
        config = BaseConfig()
        config.config = {"foo": {"bar": "baz"}}
        self.assertEqual(config.foo__bar, "baz")

    def test_getattr_child_parent_key_missing(self):
        config = BaseConfig()
        config.config = {}
        self.assertEqual(config.foo__bar, None)

    def test_getattr_child_key_missing(self):
        config = BaseConfig()
        config.config = {"foo": {}}
        self.assertEqual(config.foo__bar, None)

    def test_getattr_default_toplevel(self):
        config = BaseConfig()
        config.config = {"foo": "bar"}
        config.defaults = {"foo": "default"}
        self.assertEqual(config.foo, "bar")

    def test_getattr_default_toplevel_missing_default(self):
        config = BaseConfig()
        config.config = {"foo": "bar"}
        config.defaults = {}
        self.assertEqual(config.foo, "bar")

    def test_getattr_default_toplevel_missing_config(self):
        config = BaseConfig()
        config.config = {}
        config.defaults = {"foo": "default"}
        self.assertEqual(config.foo, "default")

    def test_getattr_default_child(self):
        config = BaseConfig()
        config.config = {"foo": {"bar": "baz"}}
        config.defaults = {"foo__bar": "default"}
        self.assertEqual(config.foo__bar, "baz")

    def test_getattr_default_child_missing_default(self):
        config = BaseConfig()
        config.config = {"foo": {"bar": "baz"}}
        config.defaults = {}
        self.assertEqual(config.foo__bar, "baz")

    def test_getattr_default_child_missing_config(self):
        config = BaseConfig()
        config.config = {}
        config.defaults = {"foo__bar": "default"}
        self.assertEqual(config.foo__bar, "default")


class DummyContents(object):
    def __init__(self, content):
        self.decoded = content


class DummyResponse(object):
    def __init__(self, content, status_code):
        self.content = content
        self.status_code = status_code


class DummyRepository(object):
    default_branch = "main"
    _api = "http://"

    def __init__(self, owner, name, contents, releases=None):
        self.owner = owner
        self.name = name
        self.html_url = f"https://github.com/{owner}/{name}"
        self._contents = contents
        self._releases = releases or []

    def file_contents(self, path, **kw):
        try:
            return self._contents[path]
        except KeyError:
            raise AssertionError(f"Accessed unexpected file: {path}")

    def directory_contents(self, path, **kw):
        try:
            return self._contents[path]
        except KeyError:
            raise NotFoundError(
                DummyResponse(f"Accessed unexpected directory: {path}", 404)
            )

    def _build_url(self, *args, **kw):
        return self._api

    def releases(self):
        return iter(self._releases)

    def latest_release(self):
        for release in self._releases:
            if release.tag_name.startswith("release/"):
                return release
        raise NotFoundError(DummyResponse("", 404))

    def release_from_tag(self, tag_name):
        for release in self._releases:
            if release.tag_name == tag_name:
                return release
        raise NotFoundError(DummyResponse("", 404))

    def branch(self, name):
        branch = mock.Mock()
        branch.commit.sha = "commit_sha"
        return branch

    def tag(self, sha):
        tag = mock.Mock()
        tag.object.sha = "tag_sha"
        return tag

    def ref(self, s):
        ref = mock.Mock()
        ref.object.sha = "ref_sha"
        return ref


class DummyRelease(object):
    def __init__(self, tag_name, name=None):
        self.tag_name = tag_name
        self.name = name


class DummyGithub(object):
    def __init__(self, repositories):
        self.repositories = repositories

    def repository(self, owner, name):
        try:
            return self.repositories[name]
        except KeyError:
            raise AssertionError(f"Unexpected repository: {name}")


class TestBaseProjectConfig(unittest.TestCase):
    maxDiff = None

    def _make_github(self):
        CUMULUSCI_TEST_REPO = DummyRepository(
            "SFDO-Tooling",
            "CumulusCI-Test",
            {
                "cumulusci.yml": DummyContents(
                    b"""
        project:
            name: CumulusCI-Test
            package:
                name: CumulusCI-Test
                namespace: ccitest
            git:
                repo_url: https://github.com/SFDO-Tooling/CumulusCI-Test
            dependencies:
                - github: https://github.com/SFDO-Tooling/CumulusCI-Test-Dep
        """
                ),
                "unpackaged/pre": {"pre": {}, "skip": {}},
                "src": {"src": ""},
                "unpackaged/post": {"post": {}, "skip": {}},
            },
        )

        CUMULUSCI_TEST_DEP_REPO = DummyRepository(
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
            [DummyRelease("release/2.0", "2.0")],
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

        return DummyGithub(
            {
                "CumulusCI": CUMULUSCI_REPO,
                "CumulusCI-Test": CUMULUSCI_TEST_REPO,
                "CumulusCI-Test-Dep": CUMULUSCI_TEST_DEP_REPO,
            }
        )

    def test_config_global(self):
        universal_config = UniversalConfig()
        universal_config.config_global = {}
        config = BaseProjectConfig(universal_config)
        self.assertIs(universal_config.config_global, config.config_global)

    def test_config_universal(self):
        universal_config = UniversalConfig()
        config = BaseProjectConfig(universal_config)
        self.assertIs(universal_config.config_universal, config.config_universal)

    def test_repo_info(self):
        env = {
            "CUMULUSCI_AUTO_DETECT": "1",
            "HEROKU_TEST_RUN_ID": "TEST1",
            "HEROKU_TEST_RUN_BRANCH": "main",
            "HEROKU_TEST_RUN_COMMIT_VERSION": "HEAD",
            "CUMULUSCI_REPO_BRANCH": "feature/test",
            "CUMULUSCI_REPO_COMMIT": "HEAD~1",
            "CUMULUSCI_REPO_ROOT": ".",
            "CUMULUSCI_REPO_URL": "https://github.com/SFDO-Tooling/CumulusCI-Test.git",
        }
        with mock.patch.dict(os.environ, env):
            config = BaseProjectConfig(UniversalConfig())
            result = config.repo_info
        self.assertEqual(
            {
                "ci": "heroku",
                "name": "CumulusCI-Test",
                "owner": "SFDO-Tooling",
                "branch": "feature/test",
                "commit": "HEAD~1",
                "root": ".",
                "url": "https://github.com/SFDO-Tooling/CumulusCI-Test.git",
            },
            result,
        )

    def test_repo_info_missing_env(self):
        env = {
            "CUMULUSCI_AUTO_DETECT": "1",
            "HEROKU_TEST_RUN_ID": "TEST1",
            "HEROKU_TEST_RUN_BRANCH": "main",
            "HEROKU_TEST_RUN_COMMIT_VERSION": "HEAD",
            "CUMULUSCI_REPO_BRANCH": "feature/test",
            "CUMULUSCI_REPO_COMMIT": "HEAD~1",
            "CUMULUSCI_REPO_ROOT": ".",
        }
        with mock.patch.dict(os.environ, env):
            with self.assertRaises(ConfigError):
                config = BaseProjectConfig(UniversalConfig())
                config.repo_info

    def test_repo_root_from_env(self):
        config = BaseProjectConfig(UniversalConfig())
        config._repo_info = {"root": "."}
        self.assertEqual(".", config.repo_root)

    def test_repo_name_from_repo_info(self):
        config = BaseProjectConfig(UniversalConfig())
        config._repo_info = {"name": "CumulusCI"}
        self.assertEqual("CumulusCI", config.repo_name)

    def test_repo_name_no_repo_root(self):
        config = BaseProjectConfig(UniversalConfig())
        with temporary_dir():
            self.assertIsNone(config.repo_name)

    def test_repo_name_from_git(self):
        config = BaseProjectConfig(UniversalConfig())
        self.assertEqual("CumulusCI", config.repo_name)

    def test_repo_url_from_repo_info(self):
        config = BaseProjectConfig(UniversalConfig())
        config._repo_info = {"url": "https://github.com/SFDO-Tooling/CumulusCI"}
        self.assertEqual("https://github.com/SFDO-Tooling/CumulusCI", config.repo_url)

    def test_repo_url_no_repo_root(self):
        config = BaseProjectConfig(UniversalConfig())
        with temporary_dir():
            self.assertIsNone(config.repo_url)

    @mock.patch("cumulusci.core.config.project_config.git_path")
    def test_repo_url_from_git(self, git_path):
        git_config_file = "git_config"
        git_path.return_value = git_config_file
        repo_url = "https://github.com/foo/bar.git"
        with open(git_config_file, "w") as f:
            f.writelines(['[remote "origin"]\n' f"\turl = {repo_url}"])

        config = BaseProjectConfig(UniversalConfig())
        assert repo_url == config.repo_url

        os.remove(git_config_file)

    def test_repo_owner_from_repo_info(self):
        config = BaseProjectConfig(UniversalConfig())
        config._repo_info = {"owner": "SFDO-Tooling"}
        self.assertEqual("SFDO-Tooling", config.repo_owner)

    def test_repo_owner_no_repo_root(self):
        config = BaseProjectConfig(UniversalConfig())
        with temporary_dir():
            self.assertIsNone(config.repo_owner)

    def test_repo_branch_from_repo_info(self):
        config = BaseProjectConfig(UniversalConfig())
        config._repo_info = {"branch": "main"}
        self.assertEqual("main", config.repo_branch)

    def test_repo_branch_no_repo_root(self):
        config = BaseProjectConfig(UniversalConfig())
        with temporary_dir():
            self.assertIsNone(config.repo_branch)

    def test_repo_commit_from_repo_info(self):
        config = BaseProjectConfig(UniversalConfig())
        config._repo_info = {"commit": "abcdef"}
        self.assertEqual("abcdef", config.repo_commit)

    def test_repo_commit_no_repo_root(self):
        config = BaseProjectConfig(UniversalConfig())
        with temporary_dir():
            self.assertIsNone(config.repo_commit)

    def test_repo_commit_no_repo_branch(self):
        config = BaseProjectConfig(UniversalConfig())
        with temporary_dir() as d:
            os.mkdir(os.path.join(d, ".git"))
            with open(os.path.join(d, ".git", "HEAD"), "w") as f:
                f.write("abcdef")

            self.assertIsNone(config.repo_commit)

    def test_repo_commit_packed_refs(self):
        config = BaseProjectConfig(UniversalConfig())
        with temporary_dir() as d:
            os.system("git init")
            with open(os.path.join(d, ".git", "HEAD"), "w") as f:
                f.write("ref: refs/heads/main\n")
            with open(os.path.join(d, ".git", "packed-refs"), "w") as f:
                f.write("# pack-refs with: peeled fully-peeled sorted\n")
                f.write("#\n")
                f.write(
                    "8ce67f4519190cd1ec9785105168e21b9599bc27 refs/remotes/origin/main\n"
                )

            self.assertIsNotNone(config.repo_commit)

    def test_get_latest_tag(self):
        config = BaseProjectConfig(
            UniversalConfig(),
            {
                "project": {
                    "git": {"prefix_beta": "beta/", "prefix_release": "release/"}
                }
            },
        )
        config.get_github_api = mock.Mock(return_value=self._make_github())
        result = config.get_latest_tag()
        self.assertEqual("release/1.1", result)

    def test_get_latest_tag_matching_prefix(self):
        config = BaseProjectConfig(
            UniversalConfig(),
            {"project": {"git": {"prefix_beta": "beta/", "prefix_release": "rel/"}}},
        )
        github = self._make_github()
        github.repositories["CumulusCI"]._releases.append(
            DummyRelease("rel/0.9", "0.9")
        )
        config.get_github_api = mock.Mock(return_value=github)
        result = config.get_latest_tag()
        self.assertEqual("rel/0.9", result)

    def test_get_latest_tag_beta(self):
        config = BaseProjectConfig(
            UniversalConfig(),
            {
                "project": {
                    "git": {"prefix_beta": "beta/", "prefix_release": "release/"}
                }
            },
        )
        config.get_github_api = mock.Mock(return_value=self._make_github())
        result = config.get_latest_tag(beta=True)
        self.assertEqual("beta/1.0-Beta_2", result)

    def test_get_latest_tag__beta_not_found(self):
        config = BaseProjectConfig(UniversalConfig())
        github = self._make_github()
        github.repositories["CumulusCI"]._releases = []
        config.get_github_api = mock.Mock(return_value=github)
        with pytest.raises(GithubException):
            config.get_latest_tag(beta=True)

    def test_get_latest_tag__repo_not_found(self):
        config = BaseProjectConfig(UniversalConfig())
        github = self._make_github()
        github.repositories["CumulusCI"] = None
        config.get_github_api = mock.Mock(return_value=github)
        with pytest.raises(GithubException):
            config.get_latest_tag()

    def test_get_latest_tag__release_not_found(self):
        config = BaseProjectConfig(UniversalConfig())
        github = self._make_github()
        github.repositories["CumulusCI"]._releases = []
        config.get_github_api = mock.Mock(return_value=github)
        with pytest.raises(GithubException):
            config.get_latest_tag()

    def test_get_latest_version(self):
        config = BaseProjectConfig(
            UniversalConfig(),
            {
                "project": {
                    "git": {"prefix_beta": "beta/", "prefix_release": "release/"}
                }
            },
        )
        config.get_github_api = mock.Mock(return_value=self._make_github())
        result = config.get_latest_version()
        self.assertEqual("1.1", result)

    def test_get_latest_version_beta(self):
        config = BaseProjectConfig(
            UniversalConfig(),
            {
                "project": {
                    "git": {"prefix_beta": "beta/", "prefix_release": "release/"}
                }
            },
        )
        config.get_github_api = mock.Mock(return_value=self._make_github())
        result = config.get_latest_version(beta=True)
        self.assertEqual("1.0 (Beta 2)", result)

    def test_get_previous_version(self):
        config = BaseProjectConfig(
            UniversalConfig(),
            {
                "project": {
                    "git": {"prefix_beta": "beta/", "prefix_release": "release/"}
                }
            },
        )
        config.get_github_api = mock.Mock(return_value=self._make_github())
        result = config.get_previous_version()
        self.assertEqual("1.0", result)

    def test_config_project_path_no_repo_root(self):
        config = BaseProjectConfig(UniversalConfig())
        with temporary_dir():
            self.assertIsNone(config.config_project_path)

    def test_get_tag_for_version(self):
        config = BaseProjectConfig(
            UniversalConfig(), {"project": {"git": {"prefix_release": "release/"}}}
        )
        self.assertEqual("release/1.0", config.get_tag_for_version("1.0"))

    def test_get_tag_for_version_beta(self):
        config = BaseProjectConfig(
            UniversalConfig(), {"project": {"git": {"prefix_beta": "beta/"}}}
        )
        self.assertEqual("beta/1.0-Beta_1", config.get_tag_for_version("1.0 (Beta 1)"))

    def test_get_version_for_tag(self):
        config = BaseProjectConfig(
            UniversalConfig(),
            {
                "project": {
                    "git": {"prefix_beta": "beta/", "prefix_release": "release/"}
                }
            },
        )
        self.assertEqual("1.0", config.get_version_for_tag("release/1.0"))

    def test_get_version_for_tag_invalid_beta(self):
        config = BaseProjectConfig(
            UniversalConfig(),
            {
                "project": {
                    "git": {"prefix_beta": "beta/", "prefix_release": "release/"}
                }
            },
        )
        self.assertEqual(None, config.get_version_for_tag("beta/invalid-format"))

    def test_check_keychain(self):
        config = BaseProjectConfig(UniversalConfig())
        with self.assertRaises(KeychainNotFound):
            config._check_keychain()

    def test_get_static_dependencies(self):
        dep = {"namespace": "npsp", "version": "3"}
        config = BaseProjectConfig(
            UniversalConfig(), {"project": {"dependencies": [dep]}}
        )
        self.assertEqual([dep], config.get_static_dependencies())

    def test_get_static_dependencies_no_dependencies(self):
        config = BaseProjectConfig(UniversalConfig())
        self.assertEqual([], config.get_static_dependencies())

    def test_get_static_dependencies__skipped_dependencies(self):
        config = BaseProjectConfig(UniversalConfig())
        deps = [
            {"namespace": "npsp", "version": "3"},
            {"namespace": "foo", "version": "1"},
        ]
        config = BaseProjectConfig(
            UniversalConfig(), {"project": {"dependencies": deps}}
        )
        self.assertEqual(
            deps[1:],
            config.get_static_dependencies(ignore_deps=[{"namespace": "npsp"}]),
        )

    def test_should_ignore_dependency(self):
        ignore_deps = [{"namespace": "npsp"}, {"github": "https://test/"}]
        config = BaseProjectConfig(UniversalConfig(), {})

        assert config._should_ignore_dependency(
            {"namespace": "npsp", "version": "3"}, ignore_deps
        )
        assert not config._should_ignore_dependency(
            {"namespace": "foo", "version": "1"}, ignore_deps
        )
        assert config._should_ignore_dependency(
            {"github": "https://test/"}, ignore_deps
        )
        assert not config._should_ignore_dependency(
            {"github": "https://example/"}, ignore_deps
        )
        assert not config._should_ignore_dependency({}, ignore_deps)

    def test_pretty_dependencies(self):
        dep = {
            "namespace": "npsp",
            "version": "3",
            "boolean": False,
            "dependencies": [{"repo_name": "TestRepo", "dependencies": []}],
        }
        config = BaseProjectConfig(UniversalConfig())
        result = "\n".join(config.pretty_dependencies([dep]))
        self.assertEqual(
            """  - dependencies: \n    \n      - repo_name: TestRepo\n    namespace: npsp\n    version: 3""",
            result,
        )

    def test_process_github_dependency(self):
        universal_config = UniversalConfig()
        config = BaseProjectConfig(universal_config)
        config.get_github_api = mock.Mock(return_value=self._make_github())
        config.keychain = DummyKeychain()

        result = config.process_github_dependency(
            {
                "github": "https://github.com/SFDO-Tooling/CumulusCI-Test.git",
                "unmanaged": True,
                "skip": ["unpackaged/pre/skip", "unpackaged/post/skip"],
            }
        )
        self.assertEqual(
            result,
            [
                {
                    "name": "Deploy unpackaged/pre/pre",
                    "repo_owner": "SFDO-Tooling",
                    "repo_name": "CumulusCI-Test",
                    "ref": "commit_sha",
                    "subfolder": "unpackaged/pre/pre",
                    "unmanaged": True,
                    "namespace_inject": None,
                    "namespace_strip": None,
                },
                {
                    "name": "Install CumulusCI-Test-Dep 2.0",
                    "version": "2.0",
                    "namespace": "ccitestdep",
                },
                {
                    "name": "Deploy CumulusCI-Test",
                    "repo_owner": "SFDO-Tooling",
                    "repo_name": "CumulusCI-Test",
                    "ref": "commit_sha",
                    "subfolder": "src",
                    "unmanaged": True,
                    "namespace_inject": None,
                    "namespace_strip": None,
                },
                {
                    "name": "Deploy unpackaged/post/post",
                    "repo_owner": "SFDO-Tooling",
                    "repo_name": "CumulusCI-Test",
                    "ref": "commit_sha",
                    "subfolder": "unpackaged/post/post",
                    "unmanaged": True,
                    "namespace_inject": "ccitest",
                    "namespace_strip": None,
                },
            ],
        )

    def test_process_github_dependency_no_unpackaged(self):
        universal_config = UniversalConfig()
        config = BaseProjectConfig(universal_config)
        github = self._make_github()
        del github.repositories["CumulusCI-Test"]._contents["unpackaged/pre"]
        del github.repositories["CumulusCI-Test"]._contents["unpackaged/post"]
        config.get_github_api = mock.Mock(return_value=github)
        config.keychain = DummyKeychain()
        result = config.process_github_dependency(
            {
                "github": "https://github.com/SFDO-Tooling/CumulusCI-Test.git",
                "unmanaged": True,
            }
        )
        self.assertEqual(
            result,
            [
                {
                    "name": "Install CumulusCI-Test-Dep 2.0",
                    "version": "2.0",
                    "namespace": "ccitestdep",
                },
                {
                    "name": "Deploy CumulusCI-Test",
                    "repo_owner": "SFDO-Tooling",
                    "repo_name": "CumulusCI-Test",
                    "ref": "commit_sha",
                    "subfolder": "src",
                    "unmanaged": True,
                    "namespace_inject": None,
                    "namespace_strip": None,
                },
            ],
        )

    def test_process_github_dependency_with_tag(self):
        universal_config = UniversalConfig()
        config = BaseProjectConfig(universal_config)
        github = self._make_github()
        github.repositories["CumulusCI-Test"]._releases = [
            DummyRelease("release/1.0", "1.0")
        ]
        config.get_github_api = mock.Mock(return_value=github)
        config.keychain = DummyKeychain()

        result = config.process_github_dependency(
            {
                "github": "https://github.com/SFDO-Tooling/CumulusCI-Test.git",
                "tag": "release/1.0",
            }
        )
        self.assertIn(
            {
                "name": "Install CumulusCI-Test 1.0",
                "namespace": "ccitest",
                "version": "1.0",
                "dependencies": [
                    {
                        "name": "Install CumulusCI-Test-Dep 2.0",
                        "namespace": "ccitestdep",
                        "version": "2.0",
                    }
                ],
            },
            result,
        )

    def test_process_github_dependency_latest(self):
        universal_config = UniversalConfig()
        config = BaseProjectConfig(universal_config)
        config.keychain = DummyKeychain()
        github = self._make_github()
        github.repositories["CumulusCI-Test-Dep"]._releases = [
            DummyRelease("beta/1.1-Beta_1", "1.1 (Beta 1)"),
            DummyRelease("release/1.0", "1.0"),
        ]
        config.get_github_api = mock.Mock(return_value=github)

        result = config.process_github_dependency(
            {
                "github": "https://github.com/SFDO-Tooling/CumulusCI-Test.git",
                "unmanaged": True,
                "skip": ["unpackaged/pre/skip", "unpackaged/post/skip"],
            },
            "",
            include_beta=True,
        )
        self.assertEqual(
            result,
            [
                {
                    "name": "Deploy unpackaged/pre/pre",
                    "repo_owner": "SFDO-Tooling",
                    "repo_name": "CumulusCI-Test",
                    "ref": "commit_sha",
                    "subfolder": "unpackaged/pre/pre",
                    "unmanaged": True,
                    "namespace_inject": None,
                    "namespace_strip": None,
                },
                {
                    "name": "Install CumulusCI-Test-Dep 1.1 (Beta 1)",
                    "version": "1.1 (Beta 1)",
                    "namespace": "ccitestdep",
                },
                {
                    "name": "Deploy CumulusCI-Test",
                    "repo_owner": "SFDO-Tooling",
                    "repo_name": "CumulusCI-Test",
                    "ref": "commit_sha",
                    "subfolder": "src",
                    "unmanaged": True,
                    "namespace_inject": None,
                    "namespace_strip": None,
                },
                {
                    "name": "Deploy unpackaged/post/post",
                    "repo_owner": "SFDO-Tooling",
                    "repo_name": "CumulusCI-Test",
                    "ref": "commit_sha",
                    "subfolder": "unpackaged/post/post",
                    "unmanaged": True,
                    "namespace_inject": "ccitest",
                    "namespace_strip": None,
                },
            ],
        )

    def test_process_github_dependency_ref(self):
        universal_config = UniversalConfig()
        config = BaseProjectConfig(universal_config)
        config.keychain = DummyKeychain()
        config.get_github_api = mock.Mock(return_value=self._make_github())

        result = config.process_github_dependency(
            {
                "github": "https://github.com/SFDO-Tooling/CumulusCI-Test.git",
                "unmanaged": True,
                "ref": "other_commit_sha",
                "skip": ["unpackaged/pre/skip", "unpackaged/post/skip"],
            },
            "",
        )
        self.assertEqual(
            result,
            [
                {
                    "name": "Deploy unpackaged/pre/pre",
                    "repo_owner": "SFDO-Tooling",
                    "repo_name": "CumulusCI-Test",
                    "ref": "other_commit_sha",
                    "subfolder": "unpackaged/pre/pre",
                    "unmanaged": True,
                    "namespace_inject": None,
                    "namespace_strip": None,
                },
                {
                    "name": "Install CumulusCI-Test-Dep 2.0",
                    "version": "2.0",
                    "namespace": "ccitestdep",
                },
                {
                    "name": "Deploy CumulusCI-Test",
                    "repo_owner": "SFDO-Tooling",
                    "repo_name": "CumulusCI-Test",
                    "ref": "other_commit_sha",
                    "subfolder": "src",
                    "unmanaged": True,
                    "namespace_inject": None,
                    "namespace_strip": None,
                },
                {
                    "name": "Deploy unpackaged/post/post",
                    "repo_owner": "SFDO-Tooling",
                    "repo_name": "CumulusCI-Test",
                    "ref": "other_commit_sha",
                    "subfolder": "unpackaged/post/post",
                    "unmanaged": True,
                    "namespace_inject": "ccitest",
                    "namespace_strip": None,
                },
            ],
        )

    def test_process_github_dependency__with_skipped_deps(self):
        universal_config = UniversalConfig()
        config = BaseProjectConfig(universal_config)
        config.get_github_api = mock.Mock(return_value=self._make_github())
        config.keychain = DummyKeychain()

        result = config.process_github_dependency(
            {
                "github": "https://github.com/SFDO-Tooling/CumulusCI-Test.git",
                "unmanaged": True,
                "skip": ["unpackaged/pre/skip", "unpackaged/post/skip"],
            },
            ignore_deps=[
                {"github": "https://github.com/SFDO-Tooling/CumulusCI-Test-Dep"}
            ],
        )
        self.assertEqual(
            result,
            [
                {
                    "name": "Deploy unpackaged/pre/pre",
                    "repo_owner": "SFDO-Tooling",
                    "repo_name": "CumulusCI-Test",
                    "ref": "commit_sha",
                    "subfolder": "unpackaged/pre/pre",
                    "unmanaged": True,
                    "namespace_inject": None,
                    "namespace_strip": None,
                },
                {
                    "name": "Deploy CumulusCI-Test",
                    "repo_owner": "SFDO-Tooling",
                    "repo_name": "CumulusCI-Test",
                    "ref": "commit_sha",
                    "subfolder": "src",
                    "unmanaged": True,
                    "namespace_inject": None,
                    "namespace_strip": None,
                },
                {
                    "name": "Deploy unpackaged/post/post",
                    "repo_owner": "SFDO-Tooling",
                    "repo_name": "CumulusCI-Test",
                    "ref": "commit_sha",
                    "subfolder": "unpackaged/post/post",
                    "unmanaged": True,
                    "namespace_inject": "ccitest",
                    "namespace_strip": None,
                },
            ],
        )

    def test_process_github_dependency__cannot_find_repo(self):
        universal_config = UniversalConfig()
        config = BaseProjectConfig(universal_config)
        config.keychain = DummyKeychain()
        github = self._make_github()
        github.repositories["CumulusCI-Test-Dep"] = None
        config.get_github_api = mock.Mock(return_value=github)

        with self.assertRaises(DependencyResolutionError):
            config.process_github_dependency(
                {"github": "https://github.com/SFDO-Tooling/CumulusCI-Test-Dep.git"}
            )

    def test_process_github_dependency_cannot_find_latest(self):
        universal_config = UniversalConfig()
        config = BaseProjectConfig(universal_config)
        config.keychain = DummyKeychain()
        github = self._make_github()
        github.repositories["CumulusCI-Test-Dep"]._releases = []
        config.get_github_api = mock.Mock(return_value=github)

        with self.assertRaises(DependencyResolutionError):
            config.process_github_dependency(
                {"github": "https://github.com/SFDO-Tooling/CumulusCI-Test-Dep.git"}
            )

    def test_process_github_dependency_tag_not_found(self):
        universal_config = UniversalConfig()
        config = BaseProjectConfig(universal_config)
        config.keychain = DummyKeychain()
        config.get_github_api = mock.Mock(return_value=self._make_github())

        with self.assertRaises(DependencyResolutionError):
            config.process_github_dependency(
                {
                    "github": "https://github.com/SFDO-Tooling/CumulusCI-Test-Dep.git",
                    "tag": "bogus",
                }
            )

    def test_get_task__included_source(self):
        universal_config = UniversalConfig()
        with temporary_dir() as d:
            touch("cumulusci.yml")
            project_config = BaseProjectConfig(
                universal_config, {"sources": {"test": {"path": d}}}
            )
            task_config = project_config.get_task("test:log")
        assert task_config.project_config is not project_config
        assert isinstance(task_config.project_config.source, LocalFolderSource)

    def test_get_flow__included_source(self):
        universal_config = UniversalConfig()
        with temporary_dir() as d:
            touch("cumulusci.yml")
            project_config = BaseProjectConfig(
                universal_config, {"sources": {"test": {"path": d}}}
            )
            flow_config = project_config.get_flow("test:dev_org")
        assert flow_config.project_config is not project_config
        assert isinstance(flow_config.project_config.source, LocalFolderSource)

    def test_get_namespace__not_found(self):
        universal_config = UniversalConfig()
        project_config = BaseProjectConfig(universal_config)
        with self.assertRaises(NamespaceNotFoundError):
            project_config.get_namespace("test")

    def test_include_source__cached(self):
        universal_config = UniversalConfig()
        project_config = BaseProjectConfig(universal_config)
        with temporary_dir() as d:
            touch("cumulusci.yml")
            other1 = project_config.include_source({"path": d})
            other2 = project_config.include_source({"path": d})
        assert other1 is other2

    @mock.patch("cumulusci.core.config.project_config.GitHubSource")
    def test_include_source__github(self, source):
        source.return_value = expected_result = mock.Mock()
        universal_config = UniversalConfig()
        project_config = BaseProjectConfig(universal_config)
        other_config = project_config.include_source({"github": "foo/bar"})
        assert other_config.source is expected_result

    def test_include_source__unknown(self):
        universal_config = UniversalConfig()
        project_config = BaseProjectConfig(universal_config)
        with self.assertRaises(Exception):
            project_config.include_source({"foo": "bar"})

    def test_relpath(self):
        universal_config = UniversalConfig()
        project_config = BaseProjectConfig(universal_config)
        assert project_config.relpath(os.path.abspath(".")) == "."

    def test_validate_package_api_version_valid(self):
        """We stringify the float 46.0 as this is what will occur when
        it is formatted into API URLS. This also negates the need to
        test an explicit string (i.e. if this passes we know that '46.0'
        will also pass)."""
        project_config = BaseProjectConfig(UniversalConfig())
        project_config.config["project"]["package"]["api_version"] = str(46.0)
        project_config._validate_package_api_format()

    def test_validate_package_api_version_invalid(self):
        project_config = BaseProjectConfig(UniversalConfig())
        project_config.config["project"]["package"]["api_version"] = str([1, 2, 3])
        with pytest.raises(ConfigError):
            project_config._validate_package_api_format()

        project_config.config["project"]["package"]["api_version"] = "9"
        with pytest.raises(ConfigError):
            project_config._validate_package_api_format()

        project_config.config["project"]["package"]["api_version"] = "9.0"
        with pytest.raises(ConfigError):
            project_config._validate_package_api_format()

        project_config.config["project"]["package"]["api_version"] = "45"
        with pytest.raises(ConfigError):
            project_config._validate_package_api_format()

        project_config.config["project"]["package"]["api_version"] = "45."
        with pytest.raises(ConfigError):
            project_config._validate_package_api_format()

        project_config.config["project"]["package"]["api_version"] = "45.00"
        with pytest.raises(ConfigError):
            project_config._validate_package_api_format()

    @mock.patch("cumulusci.core.config.project_config.git_path")
    def test_git_config_remote_origin_line(self, git_path):
        git_config_file = "test_git_config_file"
        git_path.return_value = git_config_file

        with open(git_config_file, "w") as f:
            f.writelines(
                [
                    '[branch "feature-1"]\n',
                    "\tremote = origin\n",
                    "\tmerge = refs/heads/feature-1\n",
                    '[remote "origin"]\n',
                    "\tfetch = +refs/heads/*:refs/remotes/origin/*\n",
                ]
            )

        project_config = BaseProjectConfig(UniversalConfig())
        actual_line = project_config.git_config_remote_origin_url()
        assert actual_line is None  # no url under [remote "origin"]

        with open(git_config_file, "a") as f:
            f.write("\turl = some.url.here\n")

        actual_line = project_config.git_config_remote_origin_url()
        assert actual_line == "some.url.here"

        os.remove(git_config_file)
        actual_line = project_config.git_config_remote_origin_url()
        assert actual_line is None  # no config file present

    def test_split_repo_url(self):
        name = "Cumulusci"
        owner = "SFDO-Tooling"
        project_config = BaseProjectConfig(UniversalConfig())

        https_url = f"https://github.com/{owner}/{name}.git"
        info = project_config._split_repo_url(https_url)
        assert info["name"] == name
        assert info["owner"] == owner
        assert info["url"] == https_url

        ssh_url = f"git@github.com:{owner}/{name}.git"
        info = project_config._split_repo_url(ssh_url)
        assert info["name"] == name
        assert info["owner"] == owner
        assert info["url"] == ssh_url

    def test_default_package_path(self):
        config = BaseProjectConfig(UniversalConfig())
        assert str(config.default_package_path.relative_to(config.repo_root)) == "src"

    def test_default_package_path__sfdx(self):
        with temporary_dir() as path:
            pathlib.Path(path, ".git").mkdir()
            with pathlib.Path(path, "cumulusci.yml").open("w") as f:
                yaml.dump({"project": {"source_format": "sfdx"}}, f)
            with pathlib.Path(path, "sfdx-project.json").open("w") as f:
                json.dump(
                    {"packageDirectories": [{"path": "force-app", "default": True}]}, f
                )
            config = BaseProjectConfig(UniversalConfig())
            assert (
                str(config.default_package_path.relative_to(config.repo_root))
                == "force-app"
            )


class TestBaseTaskFlowConfig(unittest.TestCase):
    def setUp(self):
        self.task_flow_config = BaseTaskFlowConfig(
            {
                "tasks": {
                    "deploy": {"description": "Deploy Task"},
                    "manage": {},
                    "control": {},
                },
                "flows": {
                    "coffee": {"description": "Coffee Flow"},
                    "juice": {"description": "Juice Flow"},
                },
            }
        )

    def test_list_tasks(self):
        tasks = self.task_flow_config.list_tasks()
        self.assertEqual(len(tasks), 3)
        deploy = [task for task in tasks if task["name"] == "deploy"][0]
        self.assertEqual(deploy["description"], "Deploy Task")

    def test_get_task(self):
        task = self.task_flow_config.get_task("deploy")
        self.assertIsInstance(task, BaseConfig)
        self.assertIn(("description", "Deploy Task"), task.config.items())

    def test_no_task(self):
        with self.assertRaises(TaskNotFoundError):
            self.task_flow_config.get_task("robotic_superstar")

    def test_get_flow(self):
        flow = self.task_flow_config.get_flow("coffee")
        self.assertIsInstance(flow, BaseConfig)
        self.assertIn(("description", "Coffee Flow"), flow.config.items())

    def test_no_flow(self):
        with self.assertRaises(FlowNotFoundError):
            self.task_flow_config.get_flow("water")

    def test_list_flows(self):
        flows = self.task_flow_config.list_flows()
        self.assertEqual(len(flows), 2)
        coffee = [flow for flow in flows if flow["name"] == "coffee"][0]
        self.assertEqual(coffee["description"], "Coffee Flow")

    def test_suggested_name(self):
        flows = self.task_flow_config.flows
        self.assertEqual(len(flows), 2)
        error_msg = self.task_flow_config.get_suggested_name("bofee", flows)
        self.assertIn("coffee", error_msg)


class TestOrgConfig(unittest.TestCase):
    @mock.patch("cumulusci.core.config.OrgConfig.SalesforceOAuth2")
    def test_refresh_oauth_token(self, SalesforceOAuth2):
        config = OrgConfig({"refresh_token": mock.sentinel.refresh_token}, "test")
        config._load_userinfo = mock.Mock()
        config._load_orginfo = mock.Mock()
        keychain = mock.Mock()
        SalesforceOAuth2.return_value = oauth = mock.Mock()
        oauth.refresh_token.return_value = resp = mock.Mock(status_code=200)
        resp.json.return_value = {}

        config.refresh_oauth_token(keychain)

        oauth.refresh_token.assert_called_once_with(mock.sentinel.refresh_token)

    @mock.patch("cumulusci.core.config.OrgConfig.SalesforceOAuth2")
    def test_refresh_oauth_token__bad_refresh_json(self, SalesforceOAuth2):
        config = OrgConfig({"refresh_token": mock.sentinel.refresh_token}, "test")
        SalesforceOAuth2.return_value = oauth = mock.Mock()
        oauth.refresh_token.return_value = resp = mock.Mock(status_code=200)
        keychain = mock.Mock()
        resp.json.side_effect = json.JSONDecodeError("blah", "Blah", 0)

        with pytest.raises(CumulusCIException) as e:
            config.refresh_oauth_token(keychain)
        assert "Cannot decode" in str(e.value)

        oauth.refresh_token.assert_called_once_with(mock.sentinel.refresh_token)

    @responses.activate
    def test_load_user_info__bad_json(self):
        config = OrgConfig(
            {
                "refresh_token": mock.sentinel.refresh_token,
                "instance_url": "http://instance_url_111.com",
            },
            "test",
        )
        keychain = mock.Mock()

        responses.add(
            responses.POST, "http://instance_url_111.com/services/oauth2/token"
        )
        with pytest.raises(CumulusCIException) as e:
            config.refresh_oauth_token(keychain)
        assert "Cannot decode" in str(e.value)

    def test_refresh_oauth_token_no_connected_app(self):
        config = OrgConfig({}, "test")
        with self.assertRaises(AttributeError):
            config.refresh_oauth_token(None)

    @mock.patch("cumulusci.core.config.OrgConfig.SalesforceOAuth2")
    def test_refresh_oauth_token_error(self, SalesforceOAuth2):
        config = OrgConfig({"refresh_token": mock.sentinel.refresh_token}, "test")
        keychain = mock.Mock()
        SalesforceOAuth2.return_value = oauth = mock.Mock()
        oauth.refresh_token.return_value = mock.Mock(status_code=400, text=":(")

        with self.assertRaises(SalesforceCredentialsException):
            config.refresh_oauth_token(keychain)

    @mock.patch("jwt.encode", mock.Mock(return_value="JWT"))
    @responses.activate
    def test_refresh_oauth_token__jwt(self):
        responses.add(
            "POST",
            "https://login.salesforce.com/services/oauth2/token",
            json={
                "access_token": "TOKEN",
                "instance_url": "https://na00.salesforce.com",
            },
        )
        with mock.patch.dict(
            os.environ,
            {"SFDX_CLIENT_ID": "some client id", "SFDX_HUB_KEY": "some private key"},
        ):
            config = OrgConfig({}, "test")
            config._load_userinfo = mock.Mock()
            config._load_orginfo = mock.Mock()
            config.refresh_oauth_token(None)
            assert config.access_token == "TOKEN"

    @mock.patch("jwt.encode", mock.Mock(return_value="JWT"))
    @responses.activate
    def test_refresh_oauth_token__jwt_sandbox(self):
        responses.add(
            "POST",
            "https://cs00.salesforce.com/services/oauth2/token",
            json={
                "access_token": "TOKEN",
                "instance_url": "https://cs00.salesforce.com",
            },
        )
        with mock.patch.dict(
            os.environ,
            {"SFDX_CLIENT_ID": "some client id", "SFDX_HUB_KEY": "some private key"},
        ):
            config = OrgConfig(
                {
                    "instance_url": "https://cs00.salesforce.com",
                },
                "test",
            )
            config._load_userinfo = mock.Mock()
            config._load_orginfo = mock.Mock()
            config.refresh_oauth_token(None)
            assert config.access_token == "TOKEN"

    @mock.patch("jwt.encode", mock.Mock(return_value="JWT"))
    @responses.activate
    def test_refresh_oauth_token__jwt_sandbox_instanceless_url(self):
        responses.add(
            "POST",
            "https://nonobvious--sandbox.my.salesforce.com/services/oauth2/token",
            json={
                "access_token": "TOKEN",
                "instance_url": "https://nonobvious--sandbox.my.salesforce.com",
            },
        )
        with mock.patch.dict(
            os.environ,
            {"SFDX_CLIENT_ID": "some client id", "SFDX_HUB_KEY": "some private key"},
        ):
            config = OrgConfig(
                {
                    "instance_url": "https://nonobvious--sandbox.my.salesforce.com",
                    "id": "https://test.salesforce.com/asdf",
                },
                "test",
            )
            config._load_userinfo = mock.Mock()
            config._load_orginfo = mock.Mock()
            config.refresh_oauth_token(None)
            assert config.access_token == "TOKEN"

    def test_lightning_base_url__instance(self):
        config = OrgConfig({"instance_url": "https://na01.salesforce.com"}, "test")
        self.assertEqual("https://na01.lightning.force.com", config.lightning_base_url)

    def test_lightning_base_url__scratch_org(self):
        config = OrgConfig(
            {"instance_url": "https://foo.cs42.my.salesforce.com"}, "test"
        )
        self.assertEqual("https://foo.lightning.force.com", config.lightning_base_url)

    def test_lightning_base_url__mydomain(self):
        config = OrgConfig({"instance_url": "https://foo.my.salesforce.com"}, "test")
        self.assertEqual("https://foo.lightning.force.com", config.lightning_base_url)

    @responses.activate
    def test_get_salesforce_version(self):
        responses.add(
            "GET", "https://na01.salesforce.com/services/data", json=[{"version": 42.0}]
        )
        config = OrgConfig({"instance_url": "https://na01.salesforce.com"}, "test")
        config.access_token = "TOKEN"
        assert config.latest_api_version == "42.0"

    @responses.activate
    def test_get_salesforce_version_bad_json(self):
        responses.add("GET", "https://na01.salesforce.com/services/data", "NOTJSON!")
        config = OrgConfig({"instance_url": "https://na01.salesforce.com"}, "test")
        config.access_token = "TOKEN"
        with pytest.raises(CumulusCIException) as e:
            assert config.latest_api_version == "42.0"
        assert "NOTJSON" in str(e.value)

    @responses.activate
    def test_get_salesforce_version_weird_json(self):
        responses.add(
            "GET", "https://na01.salesforce.com/services/data", json=["NOTADICT"]
        )
        config = OrgConfig({"instance_url": "https://na01.salesforce.com"}, "test")
        config.access_token = "TOKEN"
        with pytest.raises(CumulusCIException) as e:
            assert config.latest_api_version == "42.0"
        assert "NOTADICT" in str(e.value)

    def test_start_url(self):
        config = OrgConfig(
            {"instance_url": "https://na01.salesforce.com", "access_token": "TOKEN"},
            "test",
        )
        self.assertEqual(
            "https://na01.salesforce.com/secur/frontdoor.jsp?sid=TOKEN",
            config.start_url,
        )

    def test_user_id(self):
        config = OrgConfig({"id": "org/user"}, "test")
        self.assertEqual("user", config.user_id)

    def test_can_delete(self):
        config = OrgConfig({}, "test")
        self.assertFalse(config.can_delete())

    @responses.activate
    def test_load_orginfo(self):
        config = OrgConfig(
            {
                "instance_url": "https://example.com",
                "access_token": "TOKEN",
                "id": "OODxxxxxxxxxxxx/user",
            },
            "test",
        )
        responses.add(
            "GET", "https://example.com/services/data", json=[{"version": 48.0}]
        )

        responses.add(
            "GET",
            "https://example.com/services/data/v48.0/sobjects/Organization/OODxxxxxxxxxxxx",
            json={
                "OrganizationType": "Enterprise Edition",
                "IsSandbox": False,
                "InstanceName": "cs420",
                "NamespacePrefix": "ns",
            },
        )

        config._load_orginfo()

        self.assertEqual("Enterprise Edition", config.org_type)
        self.assertEqual(False, config.is_sandbox)
        self.assertIsNotNone(config.organization_sobject)
        assert config.namespace == "ns"

    @responses.activate
    def test_get_community_info__cached(self):
        """Verify that get_community_info returns data from the cache"""
        config = OrgConfig({}, "test")
        config._community_info_cache = {"Kōkua": {"name": "Kōkua"}}
        info = config.get_community_info("Kōkua")
        self.assertEqual(info["name"], "Kōkua")

    @responses.activate
    def test_get_community_info__fetch_if_not_in_cache(self):
        """Verify that the internal cache is automatically refreshed

        The cache should be refreshed automatically if the requested community
        is not in the cache.
        """
        responses.add("GET", "https://test/services/data", json=[{"version": 48.0}])

        responses.add(
            "GET",
            "https://test/services/data/v48.0/connect/communities",
            json={"communities": [{"name": "Kōkua"}]},
        )

        config = OrgConfig(
            {"instance_url": "https://test", "access_token": "TOKEN"}, "test"
        )
        config._community_info_cache = {}
        info = config.get_community_info("Kōkua")
        self.assertEqual(info["name"], "Kōkua")

    @mock.patch("cumulusci.core.config.OrgConfig._fetch_community_info")
    def test_community_info_force_refresh(self, mock_fetch):
        """Verify that the force_refresh parameter has an effect"""
        mock_fetch.return_value = {"Kōkua": {"name": "Kōkua"}}
        config = OrgConfig({}, "test")

        # With the cache seeded with the target community, first
        # verify that the cache isn't refreshed automatically
        config._community_info_cache = {"Kōkua": {"name": "Kōkua"}}
        config.get_community_info("Kōkua")
        mock_fetch.assert_not_called()

        # Now, set force_refresh and make sure it is refreshed
        config.get_community_info("Kōkua", force_refresh=True)
        mock_fetch.assert_called()

    @mock.patch("cumulusci.core.config.OrgConfig._fetch_community_info")
    def test_community_info_exception(self, mock_fetch):
        """Verify an exception is thrown when the community doesn't exist"""
        config = OrgConfig({}, "test")
        expected_exception = "Unable to find community information for 'bogus'"
        with self.assertRaisesRegex(Exception, expected_exception):
            config.get_community_info("bogus")

    MOCK_TOOLING_PACKAGE_RESULTS = [
        {
            "size": 2,
            "totalSize": 2,
            "done": True,
            "records": [
                {
                    "SubscriberPackage": {
                        "Id": "03350000000DEz4AAG",
                        "NamespacePrefix": "GW_Volunteers",
                    },
                    "SubscriberPackageVersionId": "04t1T00000070yqQAA",
                },
                {
                    "SubscriberPackage": {
                        "Id": "03350000000DEz5AAG",
                        "NamespacePrefix": "GW_Volunteers",
                    },
                    "SubscriberPackageVersionId": "04t000000000001AAA",
                },
                {
                    "SubscriberPackage": {
                        "Id": "03350000000DEz7AAG",
                        "NamespacePrefix": "TESTY",
                    },
                    "SubscriberPackageVersionId": "04t000000000002AAA",
                },
                {
                    "SubscriberPackage": {
                        "Id": "03350000000DEz4AAG",
                        "NamespacePrefix": "blah",
                    },
                    "SubscriberPackageVersionId": "04t0000000BOGUSAAA",
                },
            ],
        },
        {
            "size": 1,
            "totalSize": 1,
            "done": True,
            "records": [
                {
                    "Id": "04t1T00000070yqQAA",
                    "MajorVersion": 3,
                    "MinorVersion": 119,
                    "PatchVersion": 0,
                    "BuildNumber": 5,
                    "IsBeta": False,
                }
            ],
        },
        {
            "size": 1,
            "totalSize": 1,
            "done": True,
            "records": [
                {
                    "Id": "04t000000000001AAA",
                    "MajorVersion": 12,
                    "MinorVersion": 0,
                    "PatchVersion": 1,
                    "BuildNumber": 1,
                    "IsBeta": False,
                }
            ],
        },
        {
            "size": 1,
            "totalSize": 1,
            "done": True,
            "records": [
                {
                    "Id": "04t000000000002AAA",
                    "MajorVersion": 1,
                    "MinorVersion": 10,
                    "PatchVersion": 0,
                    "BuildNumber": 5,
                    "IsBeta": True,
                }
            ],
        },
        {"size": 0, "totalSize": 0, "done": True, "records": []},
    ]

    @mock.patch("cumulusci.core.config.OrgConfig.salesforce_client")
    def test_installed_packages(self, sf):
        config = OrgConfig({}, "test")
        sf.restful.side_effect = self.MOCK_TOOLING_PACKAGE_RESULTS

        expected = {
            "GW_Volunteers": [
                VersionInfo("04t1T00000070yqQAA", StrictVersion("3.119")),
                VersionInfo("04t000000000001AAA", StrictVersion("12.0.1")),
            ],
            "GW_Volunteers@3.119": [
                VersionInfo("04t1T00000070yqQAA", StrictVersion("3.119"))
            ],
            "GW_Volunteers@12.0.1": [
                VersionInfo("04t000000000001AAA", StrictVersion("12.0.1"))
            ],
            "TESTY": [VersionInfo("04t000000000002AAA", StrictVersion("1.10.0b5"))],
            "TESTY@1.10b5": [
                VersionInfo("04t000000000002AAA", StrictVersion("1.10.0b5"))
            ],
            "03350000000DEz4AAG": [
                VersionInfo("04t1T00000070yqQAA", StrictVersion("3.119"))
            ],
            "03350000000DEz5AAG": [
                VersionInfo("04t000000000001AAA", StrictVersion("12.0.1"))
            ],
            "03350000000DEz7AAG": [
                VersionInfo("04t000000000002AAA", StrictVersion("1.10.0b5"))
            ],
        }
        # get it twice so we can make sure it is cached
        assert config.installed_packages == expected
        assert config.installed_packages == expected
        sf.restful.assert_called()

        sf.restful.reset_mock()
        sf.restful.side_effect = self.MOCK_TOOLING_PACKAGE_RESULTS
        config.reset_installed_packages()
        assert config.installed_packages == expected
        sf.restful.assert_called()

    @mock.patch("cumulusci.core.config.OrgConfig.salesforce_client")
    def test_has_minimum_package_version(self, sf):
        config = OrgConfig({}, "test")
        sf.restful.side_effect = self.MOCK_TOOLING_PACKAGE_RESULTS

        assert config.has_minimum_package_version("TESTY", "1.9")
        assert config.has_minimum_package_version("TESTY", "1.10b5")
        assert not config.has_minimum_package_version("TESTY", "1.10b6")
        assert not config.has_minimum_package_version("TESTY", "1.10")
        assert not config.has_minimum_package_version("npsp", "1.0")

        assert config.has_minimum_package_version("03350000000DEz4AAG", "3.119")

        with self.assertRaises(CumulusCIException):
            config.has_minimum_package_version("GW_Volunteers", "1.0")

    def test_orginfo_cache_dir_global(self):
        config = OrgConfig(
            {
                "instance_url": "http://zombo.com/welcome",
                "username": "test-example@example.com",
            },
            "test",
            keychain=DummyKeychain(),
            global_org=True,
        )
        with TemporaryDirectory() as t:
            with mock.patch(
                "cumulusci.tests.util.DummyKeychain.global_config_dir", Path(t)
            ):
                with config.get_orginfo_cache_dir("foo") as directory:
                    assert directory.exists()
                    assert str(t) in directory, (t, directory)
                    assert (
                        str(directory)
                        .replace("\\", "/")
                        .endswith("orginfo/zombo.com__test-example__example.com/foo")
                    ), str(directory).replace("\\", "/")
                    foo = directory / "Foo.txt"
                    with foo.open("w") as f:
                        f.write("Bar")
                    with foo.open("r") as f:
                        assert f.read() == "Bar"

    def test_orginfo_cache_dir_local(self):
        config = OrgConfig(
            {
                "instance_url": "http://zombo.com/welcome",
                "username": "test-example@example.com",
            },
            "test",
            keychain=DummyKeychain(),
            global_org=False,
        )
        with TemporaryDirectory() as t:
            with mock.patch("cumulusci.tests.util.DummyKeychain.cache_dir", Path(t)):

                with config.get_orginfo_cache_dir("bar") as directory:
                    assert str(t) in directory, (t, directory)
                    assert (
                        str(directory)
                        .replace("\\", "/")
                        .endswith("orginfo/zombo.com__test-example__example.com/bar")
                    )
                    assert directory.exists()
                    foo = directory / "Foo.txt"
                    with foo.open("w") as f:
                        f.write("Bar")
                    with foo.open("r") as f:
                        assert f.read() == "Bar"

    @responses.activate
    def test_is_person_accounts_enabled__not_enabled(self):
        config = OrgConfig(
            {
                "instance_url": "https://example.com",
                "access_token": "TOKEN",
                "id": "OODxxxxxxxxxxxx/user",
            },
            "test",
        )
        self.assertIsNone(
            config._is_person_accounts_enabled,
            "_is_person_accounts_enabled should be initialized as None",
        )

        responses.add(
            "GET", "https://example.com/services/data", json=[{"version": 48.0}]
        )

        responses.add(
            "GET",
            "https://example.com/services/data/v48.0/sobjects/Account/describe",
            json={"fields": [{"name": "Id"}]},
        )

        # Verify checks describe if _is_person_accounts_enabled is None.
        actual = config.is_person_accounts_enabled

        self.assertEqual(False, actual, "")
        self.assertEqual(actual, config._is_person_accounts_enabled)

        # Verify subsequent calls return cached value.
        config._is_person_accounts_enabled = True

        self.assertEqual(
            config._is_person_accounts_enabled, config.is_person_accounts_enabled
        )

    @responses.activate
    def test_is_person_accounts_enabled__is_enabled(self):
        config = OrgConfig(
            {
                "instance_url": "https://example.com",
                "access_token": "TOKEN",
                "id": "OODxxxxxxxxxxxx/user",
            },
            "test",
        )
        self.assertIsNone(
            config._is_person_accounts_enabled,
            "_is_person_accounts_enabled should be initialized as None",
        )

        responses.add(
            "GET", "https://example.com/services/data", json=[{"version": 48.0}]
        )

        responses.add(
            "GET",
            "https://example.com/services/data/v48.0/sobjects/Account/describe",
            json={"fields": [{"name": "Id"}, {"name": "IsPersonAccount"}]},
        )

        # Verify checks describe if _is_person_accounts_enabled is None.
        actual = config.is_person_accounts_enabled

        self.assertEqual(True, actual, "")
        self.assertEqual(actual, config._is_person_accounts_enabled)

        # Verify subsequent calls return cached value.
        config._is_person_accounts_enabled = False

        self.assertEqual(
            config._is_person_accounts_enabled, config.is_person_accounts_enabled
        )

    @responses.activate
    def test_is_multi_currency_enabled__not_enabled(self):
        config = OrgConfig(
            {
                "instance_url": "https://example.com",
                "access_token": "TOKEN",
                "id": "OODxxxxxxxxxxxx/user",
            },
            "test",
        )
        assert (
            config._multiple_currencies_is_enabled is False
        ), "_multiple_currencies_is_enabled should be initialized as False"

        # Login call.
        responses.add(
            "GET", "https://example.com/services/data", json=[{"version": 48.0}]
        )

        # CurrencyType describe() call.
        # Since Multiple Currencies is not enabled, CurrencyType Sobject is not exposed.
        # Therefore, the describe call will result in a 404.
        responses.add(
            "GET",
            "https://example.com/services/data/v48.0/sobjects/CurrencyType/describe",
            status=404,
            json={
                "errorCode": "NOT_FOUND",
                "message": "The requested resource does not exist",
            },
        )

        # Add a second 404 to demonstrate we always check the describe until we detect Multiple Currencies is enabled.  From then on, we cache the fact that Multiple Currencies is enabled knowing Multiple Currencies cannot be disabled.
        responses.add(
            "GET",
            "https://example.com/services/data/v48.0/sobjects/CurrencyType/describe",
            status=404,
            json={
                "errorCode": "NOT_FOUND",
                "message": "The requested resource does not exist",
            },
        )

        # Check 1: is_multiple_currencies_enabled should be False since the CurrencyType describe gives a 404.
        actual = config.is_multiple_currencies_enabled
        assert (
            actual is False
        ), "config.is_multiple_currencies_enabled should be False since the CurrencyType describe returns a 404."
        assert (
            config._multiple_currencies_is_enabled is False
        ), "config._multiple_currencies_is_enabled should still be False since the CurrencyType describe returns a 404."

        # Check 2: We should still get the CurrencyType describe since we never cached that multiple currencies is enabled.
        actual = config.is_multiple_currencies_enabled
        assert (
            actual is False
        ), "config.is_multiple_currencies_enabled should be False since the CurrencyType describe returns a 404."
        assert (
            config._multiple_currencies_is_enabled is False
        ), "config._multiple_currencies_is_enabled should still be False since the CurrencyType describe returns a 404."

        # We should have made 3 calls: 1 token call + 2 describe calls
        assert len(responses.calls) == 1 + 2

    @responses.activate
    def test_is_multi_currency_enabled__is_enabled(self):
        config = OrgConfig(
            {
                "instance_url": "https://example.com",
                "access_token": "TOKEN",
                "id": "OODxxxxxxxxxxxx/user",
            },
            "test",
        )

        assert (
            config._multiple_currencies_is_enabled is False
        ), "_multiple_currencies_is_enabled should be initialized as False"

        # Token call.
        responses.add(
            "GET", "https://example.com/services/data", json=[{"version": 48.0}]
        )

        # CurrencyType describe() call.
        # Since Multiple Currencies is enabled, so the describe call returns a 200.
        responses.add(
            "GET",
            "https://example.com/services/data/v48.0/sobjects/CurrencyType/describe",
            json={
                # The actual payload doesn't matter; only matters is we get a 200.
            },
        )

        # Check 1: is_multiple_currencies_enabled should be True since the CurrencyType describe gives a 200.
        actual = config.is_multiple_currencies_enabled
        assert (
            actual is True
        ), "config.is_multiple_currencies_enabled should be True since the CurrencyType describe returns a 200."
        assert (
            config._multiple_currencies_is_enabled is True
        ), "config._multiple_currencies_is_enabled should be True since the CurrencyType describe returns a 200."

        # Check 2: We should have cached that Multiple Currencies is enabled, so we should not make a 2nd descrobe call. This is ok to cache since Multiple Currencies cannot be disabled.
        actual = config.is_multiple_currencies_enabled
        assert (
            actual is True
        ), "config.is_multiple_currencies_enabled should be True since the our cached value in _multiple_currencies_is_enabled is True."
        assert (
            config._multiple_currencies_is_enabled is True
        ), "config._multiple_currencies_is_enabled should still be True."

        # We should have made 2 calls: 1 token call + 1 describe call
        assert len(responses.calls) == 1 + 1

    @responses.activate
    def test_is_advanced_currency_management_enabled__multiple_currencies_not_enabled(
        self,
    ):
        config = OrgConfig(
            {
                "instance_url": "https://example.com",
                "access_token": "TOKEN",
                "id": "OODxxxxxxxxxxxx/user",
            },
            "test",
        )

        # Token call.
        responses.add(
            "GET", "https://example.com/services/data", json=[{"version": 48.0}]
        )

        # DatedConversionRate describe() call.
        # Since Multiple Currencies is not enabled, DatedConversionRate Sobject is not exposed.
        # Therefore, the describe call will result in a 404.
        responses.add(
            "GET",
            "https://example.com/services/data/v48.0/sobjects/DatedConversionRate/describe",
            status=404,
            json={
                "errorCode": "NOT_FOUND",
                "message": "The requested resource does not exist",
            },
        )

        # is_advanced_currency_management_enabled should be False since:
        # - DatedConversionRate describe gives a 404 implying the Sobject is not exposed becuase Multiple Currencies is not enabled.
        actual = config.is_advanced_currency_management_enabled
        assert (
            actual is False
        ), "config.is_advanced_currency_management_enabled should be False since the describe gives a 404."

        # We should have made 2 calls: 1 token call + 1 describe call
        assert len(responses.calls) == 1 + 1

    @responses.activate
    def test_is_advanced_currency_management_enabled__multiple_currencies_enabled__acm_not_enabled(
        self,
    ):
        config = OrgConfig(
            {
                "instance_url": "https://example.com",
                "access_token": "TOKEN",
                "id": "OODxxxxxxxxxxxx/user",
            },
            "test",
        )

        # Token call.
        responses.add(
            "GET", "https://example.com/services/data", json=[{"version": 48.0}]
        )

        # DatedConversionRate describe() call.
        # Since Multiple Currencies is enabled, so the describe call returns a 200.
        # However, ACM is not enabled so DatedConversionRate is not createable.
        responses.add(
            "GET",
            "https://example.com/services/data/v48.0/sobjects/DatedConversionRate/describe",
            json={"createable": False},
        )

        # is_advanced_currency_management_enabled should be False:
        # - DatedConversionRate describe gives a 200, so the Sobject is exposed (because Multiple Currencies is enabled).
        # - But DatedConversionRate is not creatable implying ACM is not enabled.
        actual = config.is_advanced_currency_management_enabled
        assert (
            actual is False
        ), 'config.is_advanced_currency_management_enabled should be False since though the describe gives a 200, the describe is not "createable".'

        # We should have made 2 calls: 1 token call + 1 describe call
        assert len(responses.calls) == 1 + 1

    @responses.activate
    def test_is_advanced_currency_management_enabled__multiple_currencies_enabled__acm_enabled(
        self,
    ):
        config = OrgConfig(
            {
                "instance_url": "https://example.com",
                "access_token": "TOKEN",
                "id": "OODxxxxxxxxxxxx/user",
            },
            "test",
        )

        # Token call.
        responses.add(
            "GET", "https://example.com/services/data", json=[{"version": 48.0}]
        )

        # DatedConversionRate describe() call.
        # Since Multiple Currencies is enabled, so the describe call returns a 200.
        # However, ACM is not enabled so DatedConversionRate is not createable.
        responses.add(
            "GET",
            "https://example.com/services/data/v48.0/sobjects/DatedConversionRate/describe",
            json={"createable": True},
        )

        # is_advanced_currency_management_enabled should be False:
        # - DatedConversionRate describe gives a 200, so the Sobject is exposed (because Multiple Currencies is enabled).
        # - But DatedConversionRate is not creatable implying ACM is not enabled.
        actual = config.is_advanced_currency_management_enabled
        assert (
            actual is True
        ), 'config.is_advanced_currency_management_enabled should be False since both the describe gives a 200 and the describe is "createable".'

        # We should have made 2 calls: 1 token call + 1 describe call
        assert len(responses.calls) == 1 + 1

    def test_resolve_04t_dependencies(self):
        config = OrgConfig({}, "test")
        config._installed_packages = {
            "dep@1.0": [VersionInfo("04t000000000001AAA", "1.0")]
        }
        result = config.resolve_04t_dependencies(
            [{"namespace": "dep", "version": "1.0", "dependencies": []}]
        )
        assert result == [
            {
                "namespace": "dep",
                "version": "1.0",
                "version_id": "04t000000000001AAA",
                "dependencies": [],
            }
        ]

    def test_resolve_04t_dependencies__not_installed(self):
        config = OrgConfig({}, "test")
        config._installed_packages = {}
        with pytest.raises(DependencyResolutionError):
            config.resolve_04t_dependencies([{"namespace": "dep", "version": "1.0"}])
