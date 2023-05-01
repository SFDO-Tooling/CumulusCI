import json
import tempfile
from pathlib import Path
from unittest import mock

import pytest
import responses

from cumulusci.core.config import ServiceConfig, TaskConfig
from cumulusci.core.exceptions import (
    GithubApiNotFoundError,
    GithubException,
    TaskOptionsError,
)
from cumulusci.tasks.github.publish import PublishSubtree
from cumulusci.tasks.github.tests.util_github_api import GithubApiTestMixin
from cumulusci.tests.util import create_project_config


class TestPublishSubtree(GithubApiTestMixin):
    def setup_method(self):
        self.repo_owner = "TestOwner"
        self.repo_name = "TestRepo"
        self.repo_api_url = (
            f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}"
        )

        self.public_owner = "TestOwner"
        self.public_name = "PublicRepo"
        self.public_repo_url = (
            f"https://api.github.com/repos/{self.public_owner}/{self.public_name}"
        )

        self.project_config = create_project_config(self.repo_name, self.repo_owner)
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

    def test_run_task__invalid_version_option_value(self):
        task_config = TaskConfig(
            {
                "options": {
                    "branch": "main",
                    "version": "invalue_value",
                    "create_release": True,
                    "repo_url": self.public_repo_url,
                    "includes": ["tasks/foo.py", "unpackaged/pre/foo/package.xml"],
                }
            }
        )

        with pytest.raises(TaskOptionsError):
            PublishSubtree(self.project_config, task_config)

    @mock.patch("cumulusci.tasks.github.publish.download_extract_github_from_repo")
    @mock.patch("cumulusci.tasks.github.publish.CommitDir")
    def test_run_task_tag_name__explicit_tag_name(self, commit_dir, extract_github):
        with responses.RequestsMock() as rsps:
            rsps.add(
                method=responses.GET,
                url=self.repo_api_url,
                json=self._get_expected_repo(
                    owner=self.repo_owner, name=self.repo_name
                ),
            )
            rsps.add(
                method=responses.GET,
                url=self.public_repo_url,
                json=self._get_expected_repo(
                    owner=self.public_owner, name=self.public_name
                ),
            )
            rsps.add(
                method=responses.GET,
                url=self.repo_api_url + "/git/ref/tags/release/1.0",
                status=200,
                json=self._get_expected_tag_ref("release/1.0", "SHA"),
            )
            rsps.add(
                method=responses.GET,
                url=self.repo_api_url + "/git/tags/SHA",
                json=self._get_expected_tag("release/1.0", "SHA"),
                status=200,
            )
            rsps.add(
                responses.GET,
                self.repo_api_url + "/releases/tags/release/1.0",
                json=self._get_expected_release("release/1.0"),
            )
            rsps.add(
                responses.GET,
                self.public_repo_url + "/git/ref/tags/release/1.0",
                status=404,
            )
            rsps.add(
                responses.POST,
                self.public_repo_url + "/releases",
                json=self._get_expected_release("release"),
            )
            task_config = TaskConfig(
                {
                    "options": {
                        "branch": "main",
                        "tag_name": "release/1.0",
                        "create_release": True,
                        "repo_url": self.public_repo_url,
                        "includes": ["tasks/foo.py", "unpackaged/pre/foo/package.xml"],
                    }
                }
            )
            extract_github.return_value.namelist.return_value = [
                "tasks/foo.py",
                "unpackaged/pre/foo/package.xml",
                "force-app",
            ]

            task = PublishSubtree(self.project_config, task_config)
            task()

            expected_release_body = json.dumps(
                {
                    "tag_name": "release/1.0",
                    "name": "1.0",
                    "body": "",
                    "draft": False,
                    "prerelease": False,
                }
            )
            create_release_call = rsps.calls[7]
            assert create_release_call.request.url == self.public_repo_url + "/releases"
            assert create_release_call.request.method == responses.POST
            assert create_release_call.request.body == expected_release_body

    @mock.patch("cumulusci.tasks.github.publish.download_extract_github_from_repo")
    @mock.patch("cumulusci.tasks.github.publish.CommitDir")
    def test_run_task_tag_name__latest(self, commit_dir, extract_github):
        with responses.RequestsMock() as rsps:
            rsps.add(
                method=responses.GET,
                url=self.repo_api_url,
                json=self._get_expected_repo(
                    owner=self.repo_owner, name=self.repo_name
                ),
            )
            rsps.add(
                method=responses.GET,
                url=self.public_repo_url,
                json=self._get_expected_repo(
                    owner=self.public_owner, name=self.public_name
                ),
            )
            rsps.add(
                method=responses.GET,
                url=self.repo_api_url + "/releases/latest",
                status=200,
                json=self._get_expected_release("release/1.0"),
            )
            rsps.add(
                method=responses.GET,
                url=self.repo_api_url + "/git/ref/tags/release/1.0",
                status=200,
                json=self._get_expected_tag_ref("release/1.0", "SHA"),
            )
            rsps.add(
                method=responses.GET,
                url=self.repo_api_url + "/git/tags/SHA",
                json=self._get_expected_tag("release/1.0", "SHA"),
                status=200,
            )
            rsps.add(
                responses.GET,
                self.repo_api_url + "/releases/tags/release/1.0",
                json=self._get_expected_release("release/1.0"),
            )
            rsps.add(
                responses.GET,
                self.public_repo_url + "/git/ref/tags/release/1.0",
                status=404,
            )
            rsps.add(
                responses.POST,
                self.public_repo_url + "/releases",
                json=self._get_expected_release("release"),
            )
            task_config = TaskConfig(
                {
                    "options": {
                        "branch": "main",
                        "tag_name": "latest",
                        "create_release": True,
                        "repo_url": self.public_repo_url,
                        "includes": ["tasks/foo.py", "unpackaged/pre/foo/package.xml"],
                    }
                }
            )
            extract_github.return_value.namelist.return_value = [
                "tasks/foo.py",
                "unpackaged/pre/foo/package.xml",
                "force-app",
            ]

            task = PublishSubtree(self.project_config, task_config)
            task()

            expected_release_body = json.dumps(
                {
                    "tag_name": "release/1.0",
                    "name": "1.0",
                    "body": "",
                    "draft": False,
                    "prerelease": False,
                }
            )
            create_release_call = rsps.calls[9]
            assert create_release_call.request.url == self.public_repo_url + "/releases"
            assert create_release_call.request.method == responses.POST
            assert create_release_call.request.body == expected_release_body

    @mock.patch("cumulusci.tasks.github.publish.download_extract_github_from_repo")
    @mock.patch("cumulusci.tasks.github.publish.CommitDir")
    def test_run_task_version(self, commit_dir, extract_github):
        with responses.RequestsMock() as rsps:
            rsps.add(
                method=responses.GET,
                url=self.repo_api_url,
                json=self._get_expected_repo(
                    owner=self.repo_owner, name=self.repo_name
                ),
            )
            rsps.add(
                method=responses.GET,
                url=self.public_repo_url,
                json=self._get_expected_repo(
                    owner=self.public_owner, name=self.public_name
                ),
            )
            rsps.add(
                method=responses.GET,
                url=self.repo_api_url + "/releases",
                status=200,
                json=self._get_expected_releases(
                    "TestOwner", "TestRepo", ["beta/1.0-Beta_1"]
                ),
            )
            rsps.add(
                method=responses.GET,
                url=self.repo_api_url + "/git/ref/tags/beta/1.0-Beta_1",
                status=200,
                json=self._get_expected_tag_ref("release/1.0", "SHA"),
            )
            rsps.add(
                method=responses.GET,
                url=self.repo_api_url + "/git/tags/SHA",
                json=self._get_expected_tag("release/1.0", "SHA"),
                status=200,
            )
            rsps.add(
                responses.GET,
                self.repo_api_url + "/releases/tags/beta/1.0-Beta_1",
                json=self._get_expected_release("release/1.0"),
            )
            rsps.add(
                responses.GET,
                self.public_repo_url + "/git/ref/tags/beta/1.0-Beta_1",
                status=404,
            )
            rsps.add(
                responses.POST,
                self.public_repo_url + "/releases",
                json=self._get_expected_release("beta/1.0-Beta_1"),
            )
            task_config = TaskConfig(
                {
                    "options": {
                        "branch": "main",
                        "version": "latest_beta",
                        "create_release": True,
                        "repo_url": self.public_repo_url,
                        "includes": ["tasks/foo.py", "unpackaged/pre/foo/package.xml"],
                    }
                }
            )
            extract_github.return_value.namelist.return_value = [
                "tasks/foo.py",
                "unpackaged/pre/foo/package.xml",
                "force-app",
            ]

            task = PublishSubtree(self.project_config, task_config)
            task()

            expected_release_body = json.dumps(
                {
                    "tag_name": "beta/1.0-Beta_1",
                    "name": "1.0 (Beta 1)",
                    "body": "",
                    "draft": False,
                    "prerelease": False,
                }
            )
            create_release_call = rsps.calls[9]
            assert create_release_call.request.url == self.public_repo_url + "/releases"
            assert create_release_call.request.method == responses.POST
            assert create_release_call.request.body == expected_release_body

    @responses.activate
    @mock.patch("cumulusci.tasks.github.publish.download_extract_github_from_repo")
    @mock.patch("cumulusci.tasks.github.publish.CommitDir")
    def test_ref_not_found(self, commit_dir, extract_github):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner=self.repo_owner, name=self.repo_name),
        )
        responses.add(
            method=responses.GET,
            url=self.public_repo_url,
            json=self._get_expected_repo(
                owner=self.public_owner, name=self.public_name
            ),
        )
        responses.add(
            responses.GET,
            self.repo_api_url + "/releases/latest",
            json=self._get_expected_release("release/1.0"),
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/git/ref/tags/release/1.0",
            status=404,
        )
        task_config = TaskConfig(
            {
                "options": {
                    "branch": "main",
                    "tag_name": "release/1.0",
                    "create_release": True,
                    "repo_url": self.public_repo_url,
                    "includes": ["tasks/foo.py", "unpackaged/pre/foo/package.xml"],
                }
            }
        )
        extract_github.return_value.namelist.return_value = [
            "tasks/foo.py",
            "unpackaged/pre/foo/package.xml",
            "force-app",
        ]
        task = PublishSubtree(self.project_config, task_config)
        with pytest.raises(GithubApiNotFoundError) as exc:
            task()
        assert "Could not find reference for 'tags/release/1.0' on GitHub" == str(
            exc.value
        )

    @responses.activate
    @mock.patch("cumulusci.tasks.github.publish.download_extract_github_from_repo")
    @mock.patch("cumulusci.tasks.github.publish.CommitDir")
    def test_tag_not_found(self, commit_dir, extract_github):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner=self.repo_owner, name=self.repo_name),
        )
        responses.add(
            responses.GET,
            self.repo_api_url + "/releases/latest",
            json=self._get_expected_release("release/1.0"),
        )
        responses.add(
            method=responses.GET,
            url=self.public_repo_url,
            json=self._get_expected_repo(
                owner=self.public_owner, name=self.public_name
            ),
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/git/ref/tags/release/1.0",
            status=201,
            json=self._get_expected_tag_ref("release/1.0", "REF_SHA"),
        )
        responses.add(
            responses.GET,
            self.public_repo_url + "/releases/tags/release/1.0",
            json=self._get_expected_release("release/1.0"),
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/git/tags/REF_SHA",
            status=404,
        )
        task_config = TaskConfig(
            {
                "options": {
                    "branch": "main",
                    "tag_name": "release/1.0",
                    "create_release": True,
                    "repo_url": self.public_repo_url,
                    "includes": ["tasks/foo.py", "unpackaged/pre/foo/package.xml"],
                }
            }
        )
        extract_github.return_value.namelist.return_value = [
            "tasks/foo.py",
            "unpackaged/pre/foo/package.xml",
            "force-app",
        ]
        task = PublishSubtree(self.project_config, task_config)
        with pytest.raises(GithubApiNotFoundError) as exc:
            task()
        assert "Could not find tag 'release/1.0' with SHA REF_SHA" in str(exc.value)

    @responses.activate
    @mock.patch("cumulusci.tasks.github.publish.download_extract_github_from_repo")
    @mock.patch("cumulusci.tasks.github.publish.CommitDir")
    def test_release_not_found(self, commit_dir, extract_github):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner=self.repo_owner, name=self.repo_name),
        )
        responses.add(
            responses.GET,
            self.repo_api_url + "/releases/latest",
            json=self._get_expected_release("release/1.0"),
        )
        responses.add(
            method=responses.GET,
            url=self.public_repo_url,
            json=self._get_expected_repo(
                owner=self.public_owner, name=self.public_name
            ),
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/git/ref/tags/release/1.0",
            status=200,
            json=self._get_expected_tag_ref("release/1.0", "SHA"),
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/git/tags/SHA",
            json=self._get_expected_tag("release/1.0", "SHA"),
            status=200,
        )
        responses.add(
            responses.GET, self.repo_api_url + "/releases/tags/release/1.0", status=404
        )
        task_config = TaskConfig(
            {
                "options": {
                    "branch": "master",
                    "tag_name": "release/1.0",
                    "create_release": True,
                    "repo_url": self.public_repo_url,
                    "includes": ["tasks/foo.py", "unpackaged/pre/foo/package.xml"],
                }
            }
        )
        extract_github.return_value.namelist.return_value = [
            "tasks/foo.py",
            "unpackaged/pre/foo/package.xml",
            "force-app",
        ]
        task = PublishSubtree(self.project_config, task_config)
        with pytest.raises(GithubException) as exc:
            task()
        assert str(exc.value) == "Release for release/1.0 not found"

    @responses.activate
    @mock.patch("cumulusci.tasks.github.publish.download_extract_github_from_repo")
    @mock.patch("cumulusci.tasks.github.publish.CommitDir")
    def test_target_release_exists(self, commit_dir, extract_github):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner=self.repo_owner, name=self.repo_name),
        )
        responses.add(
            responses.GET,
            self.repo_api_url + "/releases/latest",
            json=self._get_expected_release("release/1.0"),
        )
        responses.add(
            method=responses.GET,
            url=self.public_repo_url,
            json=self._get_expected_repo(
                owner=self.public_owner, name=self.public_name
            ),
        )
        responses.add(
            method=responses.GET,
            url=self.public_repo_url + "/git/ref/tags/release/1.0",
            status=201,
            json=self._get_expected_tag_ref("release/1.0", "SHA"),
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/git/ref/tags/release/1.0",
            status=201,
            json=self._get_expected_tag_ref("release/1.0", "SHA"),
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/git/tags/SHA",
            json=self._get_expected_tag("release/1.0", "SHA"),
            status=201,
        )
        responses.add(
            responses.GET,
            self.repo_api_url + "/releases/tags/release/1.0",
            json=self._get_expected_release("release/1.0"),
        )
        responses.add(
            responses.GET,
            self.public_repo_url + "/releases/tags/release/1.0",
            json=self._get_expected_release("release/1.0"),
        )
        task_config = TaskConfig(
            {
                "options": {
                    "branch": "master",
                    "tag_name": "release/1.0",
                    "create_release": True,
                    "repo_url": self.public_repo_url,
                    "includes": ["tasks/foo.py", "unpackaged/pre/foo/package.xml"],
                }
            }
        )
        extract_github.return_value.namelist.return_value = [
            "tasks/foo.py",
            "unpackaged/pre/foo/package.xml",
            "force-app",
        ]
        task = PublishSubtree(self.project_config, task_config)
        with pytest.raises(GithubException) as exc:
            task()
        assert str(exc.value) == "Ref for tag release/1.0 already exists in target repo"

    def test_ref_nor_tag_name_error(self):
        task_config = TaskConfig(
            {
                "options": {
                    "branch": "master",
                    "repo_url": self.public_repo_url,
                    "includes": ["tasks/foo.py", "unpackaged/pre/foo/package.xml"],
                }
            }
        )
        with pytest.raises(TaskOptionsError) as exc:
            PublishSubtree(self.project_config, task_config)
        assert str(exc.value) == "Either `ref` or `tag_name` option is required."

    def test_renames_not_list_error(self):
        task_config = TaskConfig(
            {
                "options": {
                    "branch": "master",
                    "repo_url": self.public_repo_url,
                    "includes": ["tasks/foo.py", "unpackaged/pre/foo/package.xml"],
                    "renames": ["tasks/foo.py", "unpackaged/pre/foo/package.xml"],
                }
            }
        )
        with pytest.raises(TaskOptionsError) as exc:
            PublishSubtree(self.project_config, task_config)
        assert (
            "Renamed paths must be a list of dicts with `local:` and `target:` keys."
            == str(exc.value)
        )

    def test_renames_wrong_keys_error(self):
        task_config = TaskConfig(
            {
                "options": {
                    "branch": "master",
                    "repo_url": self.public_repo_url,
                    "includes": ["tasks/foo.py", "unpackaged/pre/foo/package.xml"],
                    "renames": [
                        {
                            "wrong_key": "tasks/foo.py",
                            "target": "unpackaged/pre/foo/package.xml",
                        }
                    ],
                }
            }
        )
        with pytest.raises(TaskOptionsError) as exc:
            PublishSubtree(self.project_config, task_config)
        assert (
            "Renamed paths must be a list of dicts with `local:` and `target:` keys."
            == str(exc.value)
        )

    def test_renames_bad_value_error(self):
        task_config = TaskConfig(
            {
                "options": {
                    "branch": "master",
                    "repo_url": self.public_repo_url,
                    "create_release": True,
                    "includes": ["tasks/foo.py", "unpackaged/pre/foo/package.xml"],
                    "renames": [
                        {
                            "local": "public/target_readme.md",
                            "target": "",
                        }
                    ],
                }
            }
        )
        with pytest.raises(TaskOptionsError) as exc:
            PublishSubtree(self.project_config, task_config)
        assert (
            "Renamed paths must be a list of dicts with `local:` and `target:` keys."
            == str(exc.value)
        )

    def test_path_renames_option(self):
        test_includes = [
            "scripts/anon.cls",
            "scripts/more_anon.cls",
            "tasks/unmoved.py",
            "tasks/move_me.py",
            "public/public_readme.md",
        ]
        test_renames = [
            {"local": "scripts", "target": "apex"},
            {"local": "tasks/move_me.py", "target": "sample_tasks/was_moved.py"},
            {"local": "public/public_readme.md", "target": "README.md"},
            {"local": "missing_path", "target": "should_not_exist"},
        ]
        task_config = TaskConfig(
            {
                "options": {
                    "branch": "master",
                    "ref": "some-branch-name",
                    "repo_url": self.public_repo_url,
                    "include": test_includes,
                    "renames": test_renames,
                }
            }
        )
        task = PublishSubtree(self.project_config, task_config)
        with tempfile.TemporaryDirectory() as target:
            included_paths = [Path(target, local_name) for local_name in test_includes]
            [
                include.parent.mkdir(parents=True, exist_ok=True)
                for include in included_paths
            ]

            assert all([include.write_text("12345") == 5 for include in included_paths])
            assert all([include.exists() for include in included_paths])

            # Renames without a local shouldn't exist
            missing_rename = test_renames.pop()
            missing_local = Path(target, missing_rename["local"])
            assert missing_local not in included_paths

            task._rename_files(target)

            assert not Path(target, missing_rename["target"]).exists()
            unmoved_path = Path(target, "tasks/unmoved.py")
            assert unmoved_path.exists()

            # All of the paths with renames should be gone
            included_paths.remove(unmoved_path)
            assert all([not include.exists() for include in included_paths])

            # All of the renamed paths should exist
            new_paths = [Path(target, rename["target"]) for rename in test_renames]
            assert all([rename.exists() for rename in new_paths])

            # Directory renames should work
            assert Path(target, "apex/anon.cls").exists()
            assert Path(target, "apex/more_anon.cls").exists()

    @mock.patch("cumulusci.tasks.github.publish.download_extract_github_from_repo")
    @mock.patch("cumulusci.tasks.github.publish.CommitDir.__call__")
    def test_run_task_ref(self, commit_dir, extract_github):
        with responses.RequestsMock() as rsps:
            rsps.add(
                method=responses.GET,
                url=self.repo_api_url,
                json=self._get_expected_repo(
                    owner=self.repo_owner, name=self.repo_name
                ),
            )
            rsps.add(
                method=responses.GET,
                url=self.public_repo_url,
                json=self._get_expected_repo(
                    owner=self.public_owner, name=self.public_name
                ),
            )
            task_config = TaskConfig(
                {
                    "options": {
                        "branch": "master",
                        "ref": "feature/publish",
                        "create_release": False,
                        "repo_url": self.public_repo_url,
                        "includes": ["tasks/foo.py", "unpackaged/pre/foo/package.xml"],
                    }
                }
            )
            extract_github.return_value.namelist.return_value = [
                "tasks/foo.py",
                "unpackaged/pre/foo/package.xml",
                "force-app",
            ]

            task = PublishSubtree(self.project_config, task_config)
            task()

            extract_github.assert_called_once()
            assert extract_github.call_args[1]["ref"] == "feature/publish"
            commit_dir.assert_called_once()
            expected_commit_message = "Published content from ref feature/publish"
            assert commit_dir.call_args[1]["commit_message"] == expected_commit_message

    def test_included_dirs_match(self):
        test_includes = [
            "orgs/",
            "public/public_readme.md",
            "scripts/anon.cls",
            "scripts/public",
            "tasks/move_me.py",
        ]
        test_namelist = [
            "orgs/",
            "orgs/dev.json",
            "orgs/feature.json",
            "orgs/prerelease.json",
            "orgs/release.json",
            "orgs/trial.json",
            "public/public_readme.md",
            "scripts/",
            "scripts/anon.cls",
            "scripts/more_anon.cls",
            "scripts/public/",
            "scripts/public/anon.cls",
            "scripts/public_to_global.cls",
            "tasks/",
            "tasks/move_me.py",
            "tasks/unmoved.py",
        ]
        task_config = TaskConfig(
            {
                "options": {
                    "branch": "master",
                    "ref": "some-branch-name",
                    "repo_url": self.public_repo_url,
                    "include": test_includes,
                }
            }
        )
        task = PublishSubtree(self.project_config, task_config)
        expected_namelist = [
            "orgs/",
            "orgs/dev.json",
            "orgs/feature.json",
            "orgs/prerelease.json",
            "orgs/release.json",
            "orgs/trial.json",
            "public/public_readme.md",
            "scripts/anon.cls",
            "scripts/public/",
            "scripts/public/anon.cls",
            "tasks/move_me.py",
        ]
        actual_namelist = task._filter_namelist(test_includes, test_namelist)
        assert sorted(expected_namelist) == sorted(actual_namelist)
