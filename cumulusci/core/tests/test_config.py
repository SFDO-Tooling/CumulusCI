from __future__ import absolute_import
import os
import unittest

import mock
import responses

from github3.exceptions import NotFoundError
from cumulusci.core.config import BaseConfig
from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import BaseTaskFlowConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.exceptions import ConfigError
from cumulusci.core.exceptions import DependencyResolutionError
from cumulusci.core.exceptions import KeychainNotFound
from cumulusci.core.exceptions import FlowNotFoundError
from cumulusci.core.exceptions import TaskNotFoundError
from cumulusci.utils import temporary_dir


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
    default_branch = "master"
    _api = "http://"

    def __init__(self, owner, name, contents, releases=None):
        self.owner = owner
        self.name = name
        self.html_url = "https://github.com/{}/{}".format(owner, name)
        self._contents = contents
        self._releases = releases or []

    def file_contents(self, path, **kw):
        try:
            return self._contents[path]
        except KeyError:
            raise AssertionError("Accessed unexpected file: {}".format(path))

    def directory_contents(self, path, **kw):
        try:
            return self._contents[path]
        except KeyError:
            raise NotFoundError(
                DummyResponse("Accessed unexpected directory: {}".format(path), 404)
            )

    def _build_url(self, *args, **kw):
        return self._api

    def releases(self):
        return iter(self._releases)

    def latest_release(self):
        for release in self._releases:
            if release.tag_name.startswith("release/"):
                return release

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
            raise AssertionError("Unexpected repository: {}".format(name))


class DummyService(object):
    password = "password"

    def __init__(self, name):
        self.name = name


class DummyKeychain(object):
    def get_service(self, name):
        return DummyService(name)


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
                DummyRelease("release/1.0", "1.0"),
                DummyRelease("beta-wrongprefix", "wrong"),
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

    def test_config_global_local(self):
        global_config = BaseGlobalConfig()
        global_config.config_global_local = {}
        config = BaseProjectConfig(global_config)
        self.assertIs(global_config.config_global_local, config.config_global_local)

    def test_config_global(self):
        global_config = BaseGlobalConfig()
        global_config.config_global = {}
        config = BaseProjectConfig(global_config)
        self.assertIs(global_config.config_global, config.config_global)

    def test_repo_info(self):
        env = {
            "CUMULUSCI_AUTO_DETECT": "1",
            "HEROKU_TEST_RUN_ID": "TEST1",
            "HEROKU_TEST_RUN_BRANCH": "master",
            "HEROKU_TEST_RUN_COMMIT_VERSION": "HEAD",
            "CUMULUSCI_REPO_BRANCH": "feature/test",
            "CUMULUSCI_REPO_COMMIT": "HEAD~1",
            "CUMULUSCI_REPO_ROOT": ".",
            "CUMULUSCI_REPO_URL": "https://github.com/SFDO-Tooling/CumulusCI-Test.git",
        }
        with mock.patch.dict(os.environ, env):
            config = BaseProjectConfig(BaseGlobalConfig())
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
            "HEROKU_TEST_RUN_BRANCH": "master",
            "HEROKU_TEST_RUN_COMMIT_VERSION": "HEAD",
            "CUMULUSCI_REPO_BRANCH": "feature/test",
            "CUMULUSCI_REPO_COMMIT": "HEAD~1",
            "CUMULUSCI_REPO_ROOT": ".",
        }
        with mock.patch.dict(os.environ, env):
            with self.assertRaises(ConfigError):
                config = BaseProjectConfig(BaseGlobalConfig())
                config.repo_info

    def test_repo_root_from_env(self):
        config = BaseProjectConfig(BaseGlobalConfig())
        config._repo_info = {"root": "."}
        self.assertEqual(".", config.repo_root)

    def test_repo_name_from_repo_info(self):
        config = BaseProjectConfig(BaseGlobalConfig())
        config._repo_info = {"name": "CumulusCI"}
        self.assertEqual("CumulusCI", config.repo_name)

    def test_repo_name_no_repo_root(self):
        config = BaseProjectConfig(BaseGlobalConfig())
        with temporary_dir():
            self.assertIsNone(config.repo_name)

    def test_repo_name_from_git(self):
        config = BaseProjectConfig(BaseGlobalConfig())
        self.assertEqual("CumulusCI", config.repo_name)

    def test_repo_url_from_repo_info(self):
        config = BaseProjectConfig(BaseGlobalConfig())
        config._repo_info = {"url": "https://github.com/SFDO-Tooling/CumulusCI"}
        self.assertEqual("https://github.com/SFDO-Tooling/CumulusCI", config.repo_url)

    def test_repo_url_no_repo_root(self):
        config = BaseProjectConfig(BaseGlobalConfig())
        with temporary_dir():
            self.assertIsNone(config.repo_url)

    def test_repo_url_from_git(self):
        config = BaseProjectConfig(BaseGlobalConfig())
        self.assertIn("/CumulusCI", config.repo_url)

    def test_repo_owner_from_repo_info(self):
        config = BaseProjectConfig(BaseGlobalConfig())
        config._repo_info = {"owner": "SFDO-Tooling"}
        self.assertEqual("SFDO-Tooling", config.repo_owner)

    def test_repo_owner_no_repo_root(self):
        config = BaseProjectConfig(BaseGlobalConfig())
        with temporary_dir():
            self.assertIsNone(config.repo_owner)

    def test_repo_branch_from_repo_info(self):
        config = BaseProjectConfig(BaseGlobalConfig())
        config._repo_info = {"branch": "master"}
        self.assertEqual("master", config.repo_branch)

    def test_repo_branch_no_repo_root(self):
        config = BaseProjectConfig(BaseGlobalConfig())
        with temporary_dir():
            self.assertIsNone(config.repo_branch)

    def test_repo_commit_from_repo_info(self):
        config = BaseProjectConfig(BaseGlobalConfig())
        config._repo_info = {"commit": "abcdef"}
        self.assertEqual("abcdef", config.repo_commit)

    def test_repo_commit_no_repo_root(self):
        config = BaseProjectConfig(BaseGlobalConfig())
        with temporary_dir():
            self.assertIsNone(config.repo_commit)

    def test_repo_commit_no_repo_branch(self):
        config = BaseProjectConfig(BaseGlobalConfig())
        with temporary_dir() as d:
            os.mkdir(os.path.join(d, ".git"))
            with open(os.path.join(d, ".git", "HEAD"), "w") as f:
                f.write("abcdef")

            self.assertIsNone(config.repo_commit)

    def test_repo_commit_packed_refs(self):
        config = BaseProjectConfig(BaseGlobalConfig())
        with temporary_dir() as d:
            os.system("git init")
            with open(os.path.join(d, ".git", "packed-refs"), "w") as f:
                f.write("# pack-refs with: peeled fully-peeled sorted\n")
                f.write("#\n")
                f.write(
                    "8ce67f4519190cd1ec9785105168e21b9599bc27 refs/remotes/origin/master\n"
                )

            self.assertIsNotNone(config.repo_commit)

    def test_use_sentry(self):
        config = BaseProjectConfig(BaseGlobalConfig())
        config.keychain = mock.Mock()
        self.assertTrue(config.use_sentry)

    @mock.patch("raven.Client")
    def test_init_sentry(self, raven_client):
        config = BaseProjectConfig(BaseGlobalConfig())
        config.keychain = mock.Mock()
        config.init_sentry()
        self.assertEqual(
            {"repo", "commit", "cci version", "branch"},
            set(raven_client.call_args[1]["tags"].keys()),
        )

    def test_get_latest_tag(self):
        config = BaseProjectConfig(
            BaseGlobalConfig(),
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
            BaseGlobalConfig(),
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
            BaseGlobalConfig(),
            {
                "project": {
                    "git": {"prefix_beta": "beta/", "prefix_release": "release/"}
                }
            },
        )
        config.get_github_api = mock.Mock(return_value=self._make_github())
        result = config.get_latest_tag(beta=True)
        self.assertEqual("beta/1.0-Beta_2", result)

    def test_get_latest_version(self):
        config = BaseProjectConfig(
            BaseGlobalConfig(),
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
            BaseGlobalConfig(),
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
            BaseGlobalConfig(),
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
        config = BaseProjectConfig(BaseGlobalConfig())
        with temporary_dir():
            self.assertIsNone(config.config_project_path)

    def test_get_tag_for_version(self):
        config = BaseProjectConfig(
            BaseGlobalConfig(), {"project": {"git": {"prefix_release": "release/"}}}
        )
        self.assertEqual("release/1.0", config.get_tag_for_version("1.0"))

    def test_get_tag_for_version_beta(self):
        config = BaseProjectConfig(
            BaseGlobalConfig(), {"project": {"git": {"prefix_beta": "beta/"}}}
        )
        self.assertEqual("beta/1.0-Beta_1", config.get_tag_for_version("1.0 (Beta 1)"))

    def test_get_version_for_tag(self):
        config = BaseProjectConfig(
            BaseGlobalConfig(),
            {
                "project": {
                    "git": {"prefix_beta": "beta/", "prefix_release": "release/"}
                }
            },
        )
        self.assertEqual("1.0", config.get_version_for_tag("release/1.0"))

    def test_get_version_for_tag_invalid_beta(self):
        config = BaseProjectConfig(
            BaseGlobalConfig(),
            {
                "project": {
                    "git": {"prefix_beta": "beta/", "prefix_release": "release/"}
                }
            },
        )
        self.assertEqual(None, config.get_version_for_tag("beta/invalid-format"))

    def test_check_keychain(self):
        config = BaseProjectConfig(BaseGlobalConfig())
        with self.assertRaises(KeychainNotFound):
            config._check_keychain()

    def test_get_static_dependencies(self):
        dep = {"namespace": "npsp", "version": "3"}
        config = BaseProjectConfig(
            BaseGlobalConfig(), {"project": {"dependencies": [dep]}}
        )
        self.assertEqual([dep], config.get_static_dependencies())

    def test_get_static_dependencies_no_dependencies(self):
        config = BaseProjectConfig(BaseGlobalConfig())
        self.assertEqual([], config.get_static_dependencies())

    def test_pretty_dependencies(self):
        dep = {
            "namespace": "npsp",
            "version": "3",
            "boolean": False,
            "dependencies": [{"repo_name": "TestRepo", "dependencies": []}],
        }
        config = BaseProjectConfig(BaseGlobalConfig())
        result = "\n".join(config.pretty_dependencies([dep]))
        self.assertEqual(
            """  - dependencies: \n    \n      - repo_name: TestRepo\n    namespace: npsp\n    version: 3""",
            result,
        )

    def test_process_github_dependency(self):
        global_config = BaseGlobalConfig()
        config = BaseProjectConfig(global_config)
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
                    u"name": "Deploy unpackaged/pre/pre",
                    u"repo_owner": "SFDO-Tooling",
                    u"repo_name": "CumulusCI-Test",
                    u"ref": "commit_sha",
                    u"subfolder": u"unpackaged/pre/pre",
                    u"unmanaged": True,
                    u"namespace_inject": None,
                    u"namespace_strip": None,
                    u"namespace_tokenize": None,
                },
                {
                    u"name": "Install CumulusCI-Test-Dep 2.0",
                    u"version": "2.0",
                    u"namespace": "ccitestdep",
                },
                {
                    u"name": "Deploy CumulusCI-Test",
                    u"repo_owner": "SFDO-Tooling",
                    u"repo_name": "CumulusCI-Test",
                    u"ref": "commit_sha",
                    u"subfolder": u"src",
                    u"unmanaged": True,
                    u"namespace_inject": None,
                    u"namespace_strip": None,
                    u"namespace_tokenize": None,
                },
                {
                    u"name": "Deploy unpackaged/post/post",
                    u"repo_owner": "SFDO-Tooling",
                    u"repo_name": "CumulusCI-Test",
                    u"ref": "commit_sha",
                    u"subfolder": u"unpackaged/post/post",
                    u"unmanaged": True,
                    u"namespace_inject": "ccitest",
                    u"namespace_strip": None,
                    u"namespace_tokenize": None,
                },
            ],
        )

    def test_process_github_dependency_no_unpackaged(self):
        global_config = BaseGlobalConfig()
        config = BaseProjectConfig(global_config)
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
                    u"name": "Install CumulusCI-Test-Dep 2.0",
                    u"version": "2.0",
                    u"namespace": "ccitestdep",
                },
                {
                    u"name": "Deploy CumulusCI-Test",
                    u"repo_owner": "SFDO-Tooling",
                    u"repo_name": "CumulusCI-Test",
                    u"ref": "commit_sha",
                    u"subfolder": u"src",
                    u"unmanaged": True,
                    u"namespace_inject": None,
                    u"namespace_strip": None,
                    u"namespace_tokenize": None,
                },
            ],
        )

    def test_process_github_dependency_with_tag(self):
        global_config = BaseGlobalConfig()
        config = BaseProjectConfig(global_config)
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
        global_config = BaseGlobalConfig()
        config = BaseProjectConfig(global_config)
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
                    u"name": "Deploy unpackaged/pre/pre",
                    u"repo_owner": "SFDO-Tooling",
                    u"repo_name": "CumulusCI-Test",
                    u"ref": "commit_sha",
                    u"subfolder": u"unpackaged/pre/pre",
                    u"unmanaged": True,
                    u"namespace_inject": None,
                    u"namespace_strip": None,
                    u"namespace_tokenize": None,
                },
                {
                    u"name": "Install CumulusCI-Test-Dep 1.1 (Beta 1)",
                    u"version": "1.1 (Beta 1)",
                    u"namespace": "ccitestdep",
                },
                {
                    u"name": "Deploy CumulusCI-Test",
                    u"repo_owner": "SFDO-Tooling",
                    u"repo_name": "CumulusCI-Test",
                    u"ref": "commit_sha",
                    u"subfolder": u"src",
                    u"unmanaged": True,
                    u"namespace_inject": None,
                    u"namespace_strip": None,
                    u"namespace_tokenize": None,
                },
                {
                    u"name": "Deploy unpackaged/post/post",
                    u"repo_owner": "SFDO-Tooling",
                    u"repo_name": "CumulusCI-Test",
                    u"ref": "commit_sha",
                    u"subfolder": u"unpackaged/post/post",
                    u"unmanaged": True,
                    u"namespace_inject": "ccitest",
                    u"namespace_strip": None,
                    u"namespace_tokenize": None,
                },
            ],
        )

    def test_process_github_dependency_ref(self):
        global_config = BaseGlobalConfig()
        config = BaseProjectConfig(global_config)
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
                    u"name": "Deploy unpackaged/pre/pre",
                    u"repo_owner": "SFDO-Tooling",
                    u"repo_name": "CumulusCI-Test",
                    u"ref": "other_commit_sha",
                    u"subfolder": u"unpackaged/pre/pre",
                    u"unmanaged": True,
                    u"namespace_inject": None,
                    u"namespace_strip": None,
                    u"namespace_tokenize": None,
                },
                {
                    u"name": "Install CumulusCI-Test-Dep 2.0",
                    u"version": "2.0",
                    u"namespace": "ccitestdep",
                },
                {
                    u"name": "Deploy CumulusCI-Test",
                    u"repo_owner": "SFDO-Tooling",
                    u"repo_name": "CumulusCI-Test",
                    u"ref": "other_commit_sha",
                    u"subfolder": u"src",
                    u"unmanaged": True,
                    u"namespace_inject": None,
                    u"namespace_strip": None,
                    u"namespace_tokenize": None,
                },
                {
                    u"name": "Deploy unpackaged/post/post",
                    u"repo_owner": "SFDO-Tooling",
                    u"repo_name": "CumulusCI-Test",
                    u"ref": "other_commit_sha",
                    u"subfolder": u"unpackaged/post/post",
                    u"unmanaged": True,
                    u"namespace_inject": "ccitest",
                    u"namespace_strip": None,
                    u"namespace_tokenize": None,
                },
            ],
        )

    def test_process_github_dependency_cannot_find_latest(self):
        global_config = BaseGlobalConfig()
        config = BaseProjectConfig(global_config)
        config.keychain = DummyKeychain()
        github = self._make_github()
        github.repositories["CumulusCI-Test-Dep"]._releases = []
        config.get_github_api = mock.Mock(return_value=github)

        with self.assertRaises(DependencyResolutionError):
            config.process_github_dependency(
                {"github": "https://github.com/SFDO-Tooling/CumulusCI-Test-Dep.git"}
            )

    def test_process_github_dependency_tag_not_found(self):
        global_config = BaseGlobalConfig()
        config = BaseProjectConfig(global_config)
        config.keychain = DummyKeychain()
        config.get_github_api = mock.Mock(return_value=self._make_github())

        with self.assertRaises(DependencyResolutionError):
            config.process_github_dependency(
                {
                    "github": "https://github.com/SFDO-Tooling/CumulusCI-Test-Dep.git",
                    "tag": "bogus",
                }
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


class TestOrgConfig(unittest.TestCase):
    @mock.patch("cumulusci.core.config.OrgConfig.SalesforceOAuth2")
    def test_refresh_oauth_token(self, SalesforceOAuth2):
        config = OrgConfig({"refresh_token": mock.sentinel.refresh_token}, "test")
        config._load_userinfo = mock.Mock()
        config._load_orginfo = mock.Mock()
        keychain = mock.Mock()
        SalesforceOAuth2.return_value = oauth = mock.Mock()
        oauth.refresh_token.return_value = resp = mock.Mock()
        resp.json.return_value = {}

        config.refresh_oauth_token(keychain)

        oauth.refresh_token.assert_called_once_with(mock.sentinel.refresh_token)

    def test_refresh_oauth_token_no_connected_app(self):
        config = OrgConfig({}, "test")
        with self.assertRaises(AttributeError):
            config.refresh_oauth_token(None)

    def test_lightning_base_url(self):
        config = OrgConfig({"instance_url": "https://na01.salesforce.com"}, "test")
        self.assertEqual("https://na01.lightning.force.com", config.lightning_base_url)

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
            "GET",
            "https://example.com/services/data/v45.0/sobjects/Organization/OODxxxxxxxxxxxx",
            json={"OrganizationType": "Enterprise Edition", "IsSandbox": False},
        )

        config._load_orginfo()

        self.assertEqual("Enterprise Edition", config.org_type)
        self.assertEqual(False, config.is_sandbox)
