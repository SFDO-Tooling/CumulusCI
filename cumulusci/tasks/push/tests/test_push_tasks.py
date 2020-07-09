import pytest
import mock
from cumulusci.tasks.push.tasks import (
    BaseSalesforcePushTask,
    FilterSubscriberList,
    GetSubscriberList,
)
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tasks.push.push_api import MetadataPackage


def test_parse_version():
    task = create_task(BaseSalesforcePushTask, options={})
    assert task._parse_version("1.2.3") == {
        "major": "1",
        "minor": "2",
        "patch": "3",
        "build": None,
        "state": "Released",
    }


def test_parse_version_2():
    task = create_task(BaseSalesforcePushTask, options={})
    assert task._parse_version("1.2 (Beta 3)") == {
        "major": "1",
        "minor": "2",
        "patch": None,
        "build": "3",
        "state": "Beta",
    }


def test_parse_version_3():
    task = create_task(BaseSalesforcePushTask, options={})
    assert task._parse_version("1.2") == {
        "major": "1",
        "minor": "2",
        "patch": None,
        "build": None,
        "state": "Released",
    }


def test_parse_version_5():
    task = create_task(BaseSalesforcePushTask, options={})
    assert task._parse_version("1.2,Beta 3") == {
        "major": "1",
        "minor": "2",
        "patch": None,
        "build": "Beta 3",
        "state": "Beta",
    }


def test_get_version():
    task = create_task(BaseSalesforcePushTask, options={})
    assert task._get_version(
        MetadataPackage(
            push_api=mock.MagicMock(), name="foo", sf_id="033xxxxxxxxx", namespace="foo"
        ),
        "1.2.3.4",
    )
    assert task._get_version(
        MetadataPackage(
            push_api=mock.MagicMock(), name="foo", sf_id="033xxxxxxxxx", namespace="foo"
        ),
        "1.2,Beta 3",
    )
    assert task._get_version(
        MetadataPackage(
            push_api=mock.MagicMock(), name="foo", sf_id="033xxxxxxxxx", namespace="foo"
        ),
        "",
    )


# def test_get_versions():
#     task = create_task(BaseSalesforcePushTask, options={})
#     assert task._get_version("Data Integrity", "1.1") == None
#     # assert package._parse_version("1.2.3") == {
#     #     "major": "1",
#     #     "minor": "2",
#     #     "patch": "3",
#     #     "build": "4",
#     #     "state": "Succeeded",
#     # }


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
