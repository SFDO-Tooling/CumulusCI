from unittest import mock
import json
import os

from cumulusci.core.config import OrgConfig
from cumulusci.tasks.salesforce.sourcetracking import ListChanges
from cumulusci.tasks.salesforce.sourcetracking import RetrieveChanges
from cumulusci.tasks.salesforce.sourcetracking import SnapshotChanges
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tests.util import create_project_config
from cumulusci.utils import temporary_dir
from .util import create_task_fixture


class TestListChanges:
    """List the changes from a scratch org"""

    def test_run_task(self):
        task = create_task(ListChanges, {"exclude": "Ignore"})
        task._init_task()
        task.tooling = mock.Mock()
        task.logger = mock.Mock()
        task.tooling.query_all.return_value = {
            "totalSize": 1,
            "records": [
                {
                    "MemberType": "CustomObject",
                    "MemberName": "Test__c",
                    "RevisionCounter": 1,
                },
                {
                    "MemberType": "CustomObject",
                    "MemberName": "Ignored__c",
                    "RevisionCounter": 2,
                },
            ],
        }
        task._run_task()
        assert "CustomObject: Test__c" in task.logger.info.call_args[0][0]

    def test_run_task__no_changes(self):
        task = create_task(ListChanges)
        task._init_task()
        task.tooling = mock.Mock()
        task.logger = mock.Mock()
        task.tooling.query_all.return_value = {"totalSize": 0, "records": []}
        task._run_task()
        assert "Found no changes." in task.logger.info.call_args[0][0]

    def test_run_task__snapshot(self, create_task_fixture):
        with temporary_dir():
            task = create_task_fixture(ListChanges, {"snapshot": True})
            task._init_task()
            task.tooling = mock.Mock()
            messages = []
            task.logger = mock.Mock()
            task.logger.info = messages.append
            task.tooling.query_all.return_value = {
                "totalSize": 1,
                "records": [
                    {
                        "MemberType": "CustomObject",
                        "MemberName": "Test__c",
                        "RevisionCounter": 1,
                    }
                ],
            }
            task._run_task()
            assert os.path.exists(
                os.path.join(
                    task.project_config.project_cache_dir, "snapshot", "test.json"
                )
            )

            assert "CustomObject: Test__c" in messages

            task = create_task_fixture(ListChanges)
            task._init_task()
            task.tooling = mock.Mock()
            task.logger = mock.Mock()
            task.logger.info = messages.append
            task.tooling.query_all.return_value = {
                "totalSize": 1,
                "records": [
                    {
                        "MemberType": "CustomObject",
                        "MemberName": "Test__c",
                        "RevisionCounter": 1,
                    }
                ],
            }
            task._run_task()
            assert "Found no changes." in messages

    def test_filter_changes__include(self):
        foo = {
            "MemberType": "CustomObject",
            "MemberName": "foo__c",
            "RevisionCounter": 1,
        }
        bar = {
            "MemberType": "CustomObject",
            "MemberName": "bar__c",
            "RevisionCounter": 1,
        }
        foobar = {
            "MemberType": "CustomObject",
            "MemberName": "foobar__c",
            "RevisionCounter": 1,
        }
        task = create_task(ListChanges, {"include": "foo", "exclude": "bar"})
        filtered, ignored = task._filter_changes([foo, bar, foobar])
        assert filtered == [foo]

    def test_filter_changes__null_revnum(self):
        foo = {
            "MemberType": "CustomObject",
            "MemberName": "foo__c",
            "RevisionCounter": None,
        }
        bar = {
            "MemberType": "CustomObject",
            "MemberName": "bar__c",
            "RevisionCounter": 1,
        }
        task = create_task(ListChanges, {})
        filtered, ignored = task._filter_changes([foo, bar])
        assert filtered == [foo, bar]


@mock.patch("cumulusci.tasks.salesforce.sourcetracking.sfdx")
class TestRetrieveChanges:
    """Retrieve changed components from a scratch org"""

    def test_init_options__sfdx_format(self, sfdx):
        with temporary_dir():
            project_config = create_project_config()
            project_config.project__source_format = "sfdx"
            with open("sfdx-project.json", "w") as f:
                json.dump(
                    {"packageDirectories": [{"path": "force-app", "default": True}]}, f
                )
            task = create_task(RetrieveChanges, {}, project_config)
            assert not task.md_format
            assert task.options["path"] == "force-app"

    def test_run_task(self, sfdx, create_task_fixture):
        sfdx_calls = []
        sfdx.side_effect = lambda cmd, *args, **kw: sfdx_calls.append(cmd)

        with temporary_dir():
            task = create_task(
                RetrieveChanges, {"include": "Test", "namespace_tokenize": "ns"}
            )
            task._init_task()
            task.tooling = mock.Mock()
            task.tooling.query_all.return_value = {
                "totalSize": 1,
                "records": [
                    {
                        "MemberType": "CustomObject",
                        "MemberName": "Test__c",
                        "RevisionCounter": 1,
                    }
                ],
            }

            task._run_task()

            assert sfdx_calls == [
                "force:mdapi:convert",
                "force:source:retrieve",
                "force:source:convert",
            ]
            assert os.path.exists(os.path.join("src", "package.xml"))

    def test_run_task__no_changes(self, sfdx, create_task_fixture):
        with temporary_dir() as path:
            task = create_task_fixture(RetrieveChanges, {"path": path})
            task._init_task()
            messages = []
            task.tooling = mock.Mock()
            task.tooling.query_all.return_value = {"totalSize": 0, "records": []}
            task.logger = mock.Mock()
            task.logger.info = messages.append
            task._run_task()
            assert "No changes to retrieve" in messages


class TestSnapshotChanges:
    @mock.patch("cumulusci.tasks.salesforce.sourcetracking.sfdx")
    def test_run_task(self, sfdx, create_task_fixture):
        with temporary_dir():
            org_config = OrgConfig(
                {
                    "username": "test-cci@example.com",
                    "scratch": True,
                    "instance_url": "https://test.salesforce.com",
                    "access_token": "TOKEN",
                },
                "test",
            )
            task = create_task_fixture(SnapshotChanges, org_config=org_config)
            task._init_task()
            task.tooling.query = mock.Mock(
                side_effect=[
                    {"totalSize": 0, "records": [], "done": True},
                    {
                        "totalSize": 1,
                        "done": True,
                        "records": [
                            {
                                "MemberType": "CustomObject",
                                "MemberName": "Object2",
                                "RevisionCounter": 1,
                            }
                        ],
                    },
                ]
            )
            task._reset_sfdx_snapshot = mock.Mock()
            task._run_task()
            task._reset_sfdx_snapshot.assert_called_once()

    def test_freeze(self):
        task = create_task(SnapshotChanges)
        steps = task.freeze(None)
        assert steps == []


flake8 = (create_task_fixture,)
