import pytest
import mock
import responses
import os
import datetime

from cumulusci.tasks.push.tasks import (
    BaseSalesforcePushTask,
    FilterSubscriberList,
    GetSubscriberList,
    SchedulePushOrgList,
    SalesforcePushApi,
    SchedulePushOrgQuery,
)
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tasks.push.push_api import MetadataPackage, PackagePushJob
from cumulusci.core.exceptions import PushApiObjectNotFound, CumulusCIException


SF_ID = "033xxxxxxxxx"
NAMESPACE = "foo"
NAME = "foo"
ORG = "00DS0000003TJJ6MAO"


def test_parse_version():
    task = create_task(BaseSalesforcePushTask, options={})
    assert task._parse_version("1.2") == {
        "major": "1",
        "minor": "2",
        "patch": None,
        "build": None,
        "state": "Released",
    }
    assert task._parse_version("1.2,Beta 3") == {
        "major": "1",
        "minor": "2",
        "patch": None,
        "build": "Beta 3",
        "state": "Beta",
    }
    assert task._parse_version("1.2,(Beta 3)") == {
        "major": "1",
        "minor": "2",
        "patch": None,
        "build": "(Beta 3",
        "state": "Beta",
    }
    assert task._parse_version("1.2") == {
        "major": "1",
        "minor": "2",
        "patch": None,
        "build": None,
        "state": "Released",
    }


def test_get_version():
    task = create_task(BaseSalesforcePushTask, options={})
    assert task._get_version(
        MetadataPackage(
            push_api=mock.MagicMock(), name=NAME, sf_id=SF_ID, namespace=NAMESPACE
        ),
        "1.2.3.4",
    )
    assert task._get_version(
        MetadataPackage(
            push_api=mock.MagicMock(), name=NAME, sf_id=SF_ID, namespace=NAMESPACE
        ),
        "1.2,Beta 3",
    )


def test_get_version_error():
    package = mock.MagicMock()
    package.get_package_version_objs.return_value = None
    task = create_task(BaseSalesforcePushTask, options={})
    with pytest.raises(PushApiObjectNotFound):
        task._get_version(package, "1.2.3")


def test_get_package():
    task = create_task(BaseSalesforcePushTask, options={})
    task.push = mock.MagicMock()
    task.push.get_package_objs.return_value = [
        {"push_api": "123", "sf_id": SF_ID, "name": NAME, "namespace": NAMESPACE}
    ]
    assert task._get_package(NAMESPACE) == {
        "push_api": "123",
        "sf_id": SF_ID,
        "name": NAME,
        "namespace": NAMESPACE,
    }


def test_get_package_error():
    task = create_task(BaseSalesforcePushTask, options={})
    task.push = mock.MagicMock()
    task.push.get_package_objs.return_value = None
    with pytest.raises(PushApiObjectNotFound):
        task._get_package(NAMESPACE)


def test_schedule_push_org_list_get_orgs():
    with open("output.txt", "w") as file:
        file.write("\n00DS0000003TJJ6MAO\n00DS0000003TJJ6MAL")
    task = create_task(
        SchedulePushOrgList,
        options={
            "orgs": "output.txt",
            "version": "1.2.3",
            "namespace": NAMESPACE,
            "start_time": datetime.datetime.now(),
            "batch_size": 10,
        },
    )
    assert task._get_orgs() == ["00DS0000003TJJ6MAO", "00DS0000003TJJ6MAL"]
    os.remove("output.txt")


def test_schedule_push_org_list_init_options():
    with open("output.txt", "w") as file:
        file.write("\n00DS0000003TJJ6MAO\n00DS0000003TJJ6MAL")
    task = create_task(
        SchedulePushOrgList,
        options={
            "orgs": "output.txt",
            "version": "1.2.3",
            "start_time": datetime.datetime.now(),
        },
    )
    task._init_task()
    task._init_options(
        {
            "orgs": "output.txt",
            "version": "1.2.3",
            "start_time": datetime.datetime.now(),
        }
    )
    assert task.options["namespace"] == None
    assert task.options["batch_size"] == 200
    assert task.options["orgs"] == "output.txt"
    assert task.options["version"] == "1.2.3"
    os.remove("output.txt")


def test_schedule_push_org_list_bad_start_time():
    with open("output.txt", "w") as file:
        file.write("\n00DS0000003TJJ6MAO\n00DS0000003TJJ6MAL")
    task = create_task(
        SchedulePushOrgList,
        options={
            "orgs": "output.txt",
            "version": "1.2.3",
            "start_time": "2020-06-10T10:15",
            "namespace": "foo",
        },
    )
    task.push = mock.MagicMock()
    with pytest.raises(CumulusCIException):
        task._run_task()
    os.remove("output.txt")


def test_load_orgs_file():
    # creating sample org file for testing
    # testing with empty file
    with open("output.txt", "w") as file:
        file.write("\n00DS0000003TJJ6MAO\n00DS0000003TJJ6MAL")
        task = create_task(BaseSalesforcePushTask, options={})
        assert task._load_orgs_file("output.txt") == []
    #
    # testing with multiple orgs
    with open("output.txt", "r") as file:
        assert task._load_orgs_file("output.txt") == [
            "00DS0000003TJJ6MAO",
            "00DS0000003TJJ6MAL",
        ]
    os.remove("output.txt")


def test_get_subs_raises_err():
    task = create_task(GetSubscriberList, options={"filename": "in.csv"})
    with pytest.raises(NotImplementedError):
        task()


def test_filter_subs_raises_err():
    task = create_task(
        FilterSubscriberList, options={"file_in": "in.csv", "file_out": "out.txt"}
    )
    with pytest.raises(NotImplementedError):
        task()


def test_base_push_task_raises_err():
    task = create_task(BaseSalesforcePushTask, options={})
    with pytest.raises(NotImplementedError):
        task()

