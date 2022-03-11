import io
import json
import shutil
import tempfile
import zipfile
from base64 import b64encode
from pathlib import Path

import pytest
import requests
import responses
import yaml

from cumulusci.core.config import ServiceConfig, TaskConfig
from cumulusci.core.exceptions import CumulusCIException, TaskOptionsError
from cumulusci.tasks.github.tests.util_github_api import GithubApiTestMixin
from cumulusci.tasks.metadeploy import BaseMetaDeployTask, Publish
from cumulusci.tests.util import create_project_config


class TestBaseMetaDeployTask:
    maxDiff = None

    @responses.activate
    def test_call_api__400(self):
        responses.add("GET", "https://metadeploy/rest", status=400, body=b"message")

        project_config = create_project_config()
        project_config.keychain.set_service(
            "metadeploy",
            "test_alias",
            ServiceConfig({"url": "https://metadeploy", "token": "TOKEN"}),
        )
        task_config = TaskConfig()
        task = BaseMetaDeployTask(project_config, task_config)
        task._init_task()
        with pytest.raises(requests.exceptions.HTTPError):
            task._call_api("GET", "/rest")

    @responses.activate
    def test_call_api__collect_pages(self):
        responses.add(
            "GET",
            "https://metadeploy/rest",
            json={"data": [1], "links": {"next": "https://metadeploy/rest?page=2"}},
        )
        responses.add(
            "GET",
            "https://metadeploy/rest",
            json={"data": [2], "links": {"next": None}},
        )

        project_config = create_project_config()
        project_config.keychain.set_service(
            "metadeploy",
            "test_alias",
            ServiceConfig({"url": "https://metadeploy", "token": "TOKEN"}),
        )
        task_config = TaskConfig()
        task = BaseMetaDeployTask(project_config, task_config)
        task._init_task()
        results = task._call_api("GET", "/rest", collect_pages=True)
        assert [1, 2] == results


class TestPublish(GithubApiTestMixin):
    maxDiff = None

    @responses.activate
    def test_error__base_instead_of_admin_api(self):
        responses.add(
            "GET",
            "https://metadeploy/api/products?repo_url=EXISTING_REPO",
            status=200,
            body=b'{"results":[]}',
        )

        project_config = create_project_config()
        project_config.keychain.set_service(
            "metadeploy",
            "test_alias",
            ServiceConfig({"url": "https://metadeploy/api", "token": "TOKEN"}),
        )
        project_config.config["project"]["git"]["repo_url"] = "EXISTING_REPO"
        project_config.config["plans"] = {
            "install": {
                "title": "Test Install",
                "slug": "install",
                "tier": "primary",
                "steps": {
                    1: {"flow": "install_prod"},
                    2: {
                        "task": "util_sleep",
                        "checks": [{"when": "False", "action": "error"}],
                    },
                },
                "checks": [{"when": "False", "action": "error"}],
            }
        }

        task_config = TaskConfig(
            {
                "options": {
                    "tag": "release/1.0",
                }
            }
        )
        with pytest.raises(CumulusCIException) as e:
            task = Publish(project_config, task_config)
            task()

        assert "Admin API" in str(e.value)

    @responses.activate
    def test_run_task(self):
        project_config = create_project_config()
        project_config.config["project"]["git"]["repo_url"] = "EXISTING_REPO"
        project_config.config["plans"] = {
            "install": {
                "title": "Test Install",
                "slug": "install",
                "tier": "primary",
                "steps": {
                    1: {"flow": "install_prod"},
                    2: {
                        "task": "util_sleep",
                        "checks": [{"when": "False", "action": "error"}],
                    },
                },
                "checks": [{"when": "False", "action": "error"}],
            }
        }
        project_config.keychain.set_service(
            "metadeploy",
            "test_alias",
            ServiceConfig({"url": "https://metadeploy", "token": "TOKEN"}),
        )
        project_config.keychain.set_service(
            "github",
            "test_alias",
            ServiceConfig(
                {"username": "foo", "token": "bar", "email": "foo@example.com"}
            ),
        )

        responses.add(
            "GET",
            "https://metadeploy/products?repo_url=EXISTING_REPO",
            json={
                "data": [
                    {
                        "id": "abcdef",
                        "url": "https://EXISTING_PRODUCT",
                        "slug": "existing",
                    }
                ]
            },
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo",
            json=self._get_expected_repo("TestOwner", "TestRepo"),
        )
        responses.add("PATCH", "https://metadeploy/translations/es", json={})
        responses.add("PATCH", "https://metadeploy/translations/es-bogus", status=404)
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/tags/release/1.0",
            json=self._get_expected_tag_ref("release/1.0", "tag_sha"),
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/tags/tag_sha",
            json=self._get_expected_tag("release/1.0", "commit_sha"),
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
            "https://api.github.com/repos/TestOwner/TestRepo/zipball/commit_sha",
            body=f.getvalue(),
            content_type="application/zip",
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/releases/latest",
            json=self._get_expected_release("release/1.0"),
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
        responses.add(
            "GET",
            "https://metadeploy/versions?product=abcdef&label=1.0",
            json={"data": []},
        )
        responses.add(
            "POST",
            "https://metadeploy/versions",
            json={"url": "https:/metadeploy/versions/1", "id": 1},
        )
        responses.add(
            "GET",
            "https://metadeploy/plantemplates?product=abcdef&name=install",
            json={"data": [{"url": "https://metadeploy/plantemplates/1"}]},
        )
        responses.add(
            "POST",
            "https://metadeploy/plans",
            json={"url": "https://metadeploy/plans/1"},
        )
        responses.add("PATCH", "https://metadeploy/versions/1", json={})

        labels_path = tempfile.mkdtemp()
        en_labels_path = Path(labels_path, "labels_en.json")
        en_labels_path.write_text('{"test": {"title": {}}}')
        es_labels_path = Path(labels_path, "labels_es.json")
        es_labels_path.write_text('{"test": {"title": {}}}')
        bogus_labels_path = Path(labels_path, "labels_es-bogus.json")
        bogus_labels_path.write_text('{"test": {"title": {}}}')

        task_config = TaskConfig(
            {
                "options": {
                    "tag": "release/1.0",
                    "publish": True,
                    "dry_run": "False",
                    "labels_path": labels_path,
                }
            }
        )
        task = Publish(project_config, task_config)
        task()

        steps = json.loads(responses.calls[-2].request.body)["steps"]
        self.maxDiff = None
        assert [
            {
                "is_required": True,
                "kind": "managed",
                "name": "Install Test Product 1.0",
                "path": "install_prod.install_managed",
                "source": None,
                "step_num": "1/2",
                "task_class": "cumulusci.tasks.salesforce.InstallPackageVersion",
                "task_config": {
                    "options": {
                        "namespace": "ns",
                        "version": "1.0",
                        "interactive": False,
                        "base_package_url_format": "{}",
                    },
                    "checks": [],
                },
            },
            {
                "is_required": True,
                "kind": "metadata",
                "name": "Update Admin Profile",
                "path": "install_prod.config_managed.update_admin_profile",
                "source": None,
                "step_num": "1/3/2",
                "task_class": "cumulusci.tasks.salesforce.ProfileGrantAllAccess",
                "task_config": {
                    "options": {
                        "namespace_inject": "ns",
                        "include_packaged_objects": False,
                    },
                    "checks": [],
                },
            },
            {
                "name": "util_sleep",
                "kind": "other",
                "is_required": True,
                "path": "util_sleep",
                "step_num": "2",
                "task_class": "cumulusci.tasks.util.Sleep",
                "task_config": {
                    "options": {"seconds": 5},
                    "checks": [{"when": "False", "action": "error"}],
                },
                "source": None,
            },
        ] == steps

        labels = json.loads(en_labels_path.read_text())
        assert labels == {
            "plan:install": {
                "title": {
                    "message": "Test Install",
                    "description": "title of installation plan",
                }
            },
            "steps": {
                "Install {product} {version}": {
                    "message": "Install {product} {version}",
                    "description": "title of installation step",
                },
                "Update Admin Profile": {
                    "message": "Update Admin Profile",
                    "description": "title of installation step",
                },
                "util_sleep": {
                    "message": "util_sleep",
                    "description": "title of installation step",
                },
            },
            "test": {"title": {}},
        }
        shutil.rmtree(labels_path)

    @responses.activate
    def test_find_or_create_version__already_exists(self):
        responses.add(
            "GET",
            "https://metadeploy/versions?product=abcdef&label=1.0",
            json={"data": [{"url": "http://EXISTING_VERSION"}]},
        )

        project_config = create_project_config()
        project_config.config["project"]["git"]["repo_url"] = "EXISTING_REPO"
        project_config.config["plans"] = {
            "install": {
                "title": "Test Install",
                "slug": "install",
                "tier": "primary",
                "steps": {1: {"flow": "install_prod"}},
            }
        }
        project_config.keychain.set_service(
            "metadeploy",
            "test_alias",
            ServiceConfig({"url": "https://metadeploy", "token": "TOKEN"}),
        )
        task_config = TaskConfig({"options": {"tag": "release/1.0"}})
        task = Publish(project_config, task_config)
        task._init_task()
        version = task._find_or_create_version(
            {"url": "http://EXISTING_PRODUCT", "id": "abcdef"}
        )
        assert version["url"] == "http://EXISTING_VERSION"

    @responses.activate
    def test_find_or_create_version__commit(self):
        responses.add(
            "GET",
            "https://metadeploy/versions?product=abcdef&label=abcdef",
            json={"data": [{"url": "http://EXISTING_VERSION"}]},
        )

        project_config = create_project_config()
        project_config.config["project"]["git"]["repo_url"] = "EXISTING_REPO"
        project_config.config["plans"] = {
            "install": {
                "title": "Test Install",
                "slug": "install",
                "tier": "primary",
                "steps": {1: {"flow": "install_prod"}},
            }
        }
        project_config.keychain.set_service(
            "metadeploy",
            "test_alias",
            ServiceConfig({"url": "https://metadeploy", "token": "TOKEN"}),
        )
        task_config = TaskConfig({"options": {"commit": "abcdef"}})
        task = Publish(project_config, task_config)
        task._init_task()
        version = task._find_or_create_version(
            {"url": "http://EXISTING_PRODUCT", "id": "abcdef"}
        )
        assert version["url"] == "http://EXISTING_VERSION"

    @responses.activate
    def test_find_product__not_found(self):
        responses.add(
            "GET",
            "https://metadeploy/products?repo_url=EXISTING_REPO",
            json={"data": []},
        )
        project_config = create_project_config()
        project_config.config["project"]["git"]["repo_url"] = "EXISTING_REPO"
        project_config.keychain.set_service(
            "metadeploy",
            "test_alias",
            ServiceConfig({"url": "https://metadeploy", "token": "TOKEN"}),
        )
        task_config = TaskConfig({"options": {"tag": "release/1.0"}})
        task = Publish(project_config, task_config)
        task._init_task()
        with pytest.raises(Exception):
            task._find_product()

    def test_init_task__no_tag_or_commit(self):
        project_config = create_project_config()
        project_config.keychain.set_service(
            "metadeploy",
            "test_alias",
            ServiceConfig({"url": "https://metadeploy", "token": "TOKEN"}),
        )
        task_config = TaskConfig({"options": {}})
        task = Publish(project_config, task_config)
        with pytest.raises(TaskOptionsError):
            task._init_task()

    @responses.activate
    def test_init_task__named_plan(self):
        project_config = create_project_config()
        project_config.config["project"]["git"]["repo_url"] = "EXISTING_REPO"
        expected_plans = {
            "install": {
                "title": "Test Install",
                "slug": "install",
                "tier": "primary",
                "steps": {1: {"flow": "install_prod"}},
            }
        }
        project_config.config["plans"] = expected_plans
        project_config.keychain.set_service(
            "metadeploy",
            "test_alias",
            ServiceConfig({"url": "https://metadeploy", "token": "TOKEN"}),
        )
        task_config = TaskConfig({"options": {"tag": "release/1.0", "plan": "install"}})
        task = Publish(project_config, task_config)
        task._init_task()
        assert expected_plans == task.plan_configs

    @responses.activate
    def test_find_or_create_plan_template__not_found(self):
        responses.add(
            "GET",
            "https://metadeploy/plantemplates?product=abcdef&name=install",
            json={"data": []},
        )
        responses.add(
            "POST",
            "https://metadeploy/plantemplates",
            json={"url": "https://NEW_PLANTEMPLATE"},
        )
        responses.add(
            "POST", "https://metadeploy/planslug", json={"url": "http://NEW_PLANSLUG"}
        )

        project_config = create_project_config()
        project_config.config["project"]["git"]["repo_url"] = "EXISTING_REPO"
        expected_plans = {
            "install": {
                "title": "Test Install",
                "slug": "install",
                "tier": "primary",
                "steps": {1: {"flow": "install_prod"}},
            }
        }
        project_config.config["plans"] = expected_plans
        project_config.keychain.set_service(
            "metadeploy",
            "test_alias",
            ServiceConfig({"url": "https://metadeploy", "token": "TOKEN"}),
        )
        task_config = TaskConfig({"options": {"tag": "release/1.0"}})
        task = Publish(project_config, task_config)
        task._init_task()
        plantemplate = task._find_or_create_plan_template(
            {"url": "https://EXISTING_PRODUCT", "id": "abcdef"},
            "install",
            {"slug": "install"},
        )
        assert plantemplate["url"] == "https://NEW_PLANTEMPLATE"

    def test_freeze_steps__skip(self):
        project_config = create_project_config()
        project_config.keychain.set_service(
            "metadeploy",
            "test_alias",
            ServiceConfig({"url": "https://metadeploy", "token": "TOKEN"}),
        )
        plan_config = {
            "title": "Test Install",
            "slug": "install",
            "tier": "primary",
            "steps": {1: {"task": "None"}},
        }
        task_config = TaskConfig({"options": {"tag": "release/1.0"}})
        task = Publish(project_config, task_config)
        task._init_task()
        steps = task._freeze_steps(project_config, plan_config)
        assert steps == []
