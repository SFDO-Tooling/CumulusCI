import pytest

from cumulusci.tasks.push.tasks import (
    BaseSalesforcePushTask,
    FilterSubscriberList,
    GetSubscriberList,
)
from cumulusci.tasks.salesforce.tests.util import create_task


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
