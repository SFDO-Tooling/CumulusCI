import datetime
import os
from unittest import mock
import pytest

from cumulusci.core.exceptions import CumulusCIException, PushApiObjectNotFound
from cumulusci.tasks.push.push_api import (
    MetadataPackage,
    MetadataPackageVersion,
    PackagePushRequest,
    PackagePushJob,
)
from cumulusci.tasks.push.tasks import (
    BaseSalesforcePushTask,
    SchedulePushOrgList,
    SchedulePushOrgQuery,
)
from cumulusci.tasks.salesforce.tests.util import create_task


SF_ID = "033xxxxxxxxx"
NAMESPACE = "foo"
NAME = "foo"
ORG_FILE = "output.txt"
VERSION = "1.2.3"
ORG = "00DS0000003TJJ6MAO"
ORG_FILE_TEXT = "\n00DS0000003TJJ6MAO\n00DS0000003TJJ6MAL"

PACKAGE_OBJ_SUBSCRIBER = {
    "totalSize": 1,
    "done": True,
    "records": [
        {
            "attributes": {
                "type": "PackageSubscribers",
                "url": "/services/data/v48.0/sobjects/PackageSubscribers/0DV1R000000k9dEWAQ",
            },
            "Id": "0DV1R000000k9dEWAQ",
            "NamespacePrefix": "2020-07-02T08:03:49.000+0000",
            "Name": "cci",
            "MetadataPackageId": "0DV1R000000k9dEWAQ",
            "PackageVersionId": "0DV1R000000k9dEWAQ",
            "ReleaseState": "Failed",
            "ScheduledStartTime": "2020-07-02T08:03:49.000+0000",
            "MajorVersion": "1",
            "MinorVersion": "2",
            "PatchVersion": "3",
            "BuildNumber": "4",
            "Status": "Failed",
            "SubscriberOrganizationKey": "00DS0000003TJJ6MAA",
            "MetadataPackageVersionId": "0DV1R000000k9dEWAQ",
            "InstalledStatus": "Success",
            "PackagePushRequestId": "0DV1R000000k9dEWAQ",
            "OrgName": "bar",
            "OrgKey": "bar",
            "OrgStatus": "bar",
            "OrgType": "Production",
            "PackagePushJobId": "0DV1R000000k9dEWAQ",
            "ErrorSeverity": "",
            "ErrorType": "",
            "ErrorTitle": "",
            "ErrorMessage": "",
            "ErrorDetails": "",
        }
    ],
}
PACKAGE_OBJS = {
    "totalSize": 1,
    "done": True,
    "records": [
        {
            "attributes": {
                "type": "PackagePushRequest",
                "url": "/services/data/v48.0/sobjects/PackagePushRequest/0DV1R000000k9dEWAQ",
            },
            "Id": "0DV1R000000k9dEWAQ",
            "NamespacePrefix": "2020-07-02T08:03:49.000+0000",
            "Name": "cci",
            "MetadataPackageId": "0DV1R000000k9dEWAQ",
            "PackageVersionId": "0DV1R000000k9dEWAQ",
            "ReleaseState": "Failed",
            "ScheduledStartTime": "2020-07-02T08:03:49.000+0000",
            "MajorVersion": "1",
            "MinorVersion": "2",
            "PatchVersion": "3",
            "BuildNumber": "4",
            "Status": "Failed",
            "SubscriberOrganizationKey": "00DS0000003TJJ6MAO",
            "MetadataPackageVersionId": "0DV1R000000k9dEWAQ",
            "InstalledStatus": "Success",
            "PackagePushRequestId": "0DV1R000000k9dEWAQ",
            "OrgName": "foo",
            "OrgKey": "foo",
            "OrgStatus": "foo",
            "OrgType": "Sandbox",
            "PackagePushJobId": "0DV1R000000k9dEWAQ",
            "ErrorSeverity": "",
            "ErrorType": "",
            "ErrorTitle": "",
            "ErrorMessage": "",
            "ErrorDetails": "",
        }
    ],
}


@pytest.fixture
def org_file():
    with open(ORG_FILE, "w") as file:
        file.write(ORG_FILE_TEXT)
    try:
        yield  # this is where the test using the fixture runs
    finally:
        os.remove(ORG_FILE)


@pytest.fixture
def empty_org_file():
    with open(ORG_FILE, "w") as file:
        file.write("")
    try:
        yield  # this is where the test using the fixture runs
    finally:
        os.remove(ORG_FILE)


@pytest.fixture
def metadata_package():
    return MetadataPackage(
        push_api=mock.MagicMock(), name=NAME, sf_id=SF_ID, namespace=NAMESPACE
    )


@pytest.fixture
def metadata_package_version_1(metadata_package):
    return MetadataPackageVersion(
        push_api=mock.MagicMock(),
        package=metadata_package,
        name=NAME,
        sf_id=SF_ID,
        state="Beta",
        major="1",
        minor="2",
        patch="3",
        build="4",
    )


@pytest.fixture
def metadata_package_version_2(metadata_package):
    return MetadataPackageVersion(
        push_api=mock.MagicMock(),
        package=metadata_package,
        name=NAME,
        sf_id=SF_ID,
        state="Beta",
        major="1",
        minor="1",
        patch="1",
        build="1",
    )


@pytest.fixture
def package_push_job_success():
    return PackagePushJob(
        push_api=mock.MagicMock(),
        request=mock.Mock(),
        org="00D63000000ApoXEAS",
        status="Succeeded",
        sf_id=SF_ID,
    )


@pytest.fixture
def package_push_job_failure():
    return PackagePushJob(
        push_api=mock.MagicMock(),
        request=mock.Mock(),
        org="00D63000000ApoXEAS",
        status="Failed",
        sf_id=SF_ID,
    )


@pytest.fixture
def package_push_job_cancel():
    return PackagePushJob(
        push_api=mock.MagicMock(),
        request=mock.Mock(),
        org="00D63000000ApoXEAS",
        status="Canceled",
        sf_id=SF_ID,
    )


@pytest.fixture
def package_push_request_failure():
    return PackagePushRequest(
        push_api=mock.MagicMock(),
        version="1.2.3",
        start_time="12:03",
        status="Failed",
        sf_id=SF_ID,
    )


@pytest.fixture
def package_push_request_cancel():
    return PackagePushRequest(
        push_api=mock.MagicMock(),
        version="1.2.3",
        start_time="12:03",
        status="Canceled",
        sf_id=SF_ID,
    )


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


def test_get_version(
    metadata_package, metadata_package_version_1, metadata_package_version_2
):
    task = create_task(BaseSalesforcePushTask, options={})
    metadata_package.push_api = mock.MagicMock()
    metadata_package.push_api.get_package_version_objs.return_value = [
        metadata_package_version_1,
        metadata_package_version_2,
    ]
    assert task._get_version(metadata_package, "1.2.3.4") == metadata_package_version_1
    assert task._get_version(metadata_package, "1.2,Beta 3")


def test_get_version_error():
    package = mock.MagicMock()
    package.get_package_version_objs.return_value = []
    task = create_task(BaseSalesforcePushTask, options={})
    with pytest.raises(PushApiObjectNotFound):
        task._get_version(package, VERSION)


def test_get_package(metadata_package):
    task = create_task(BaseSalesforcePushTask, options={})
    task.push = mock.MagicMock()
    task.push.get_package_objs.return_value = [metadata_package]
    assert task._get_package(NAMESPACE) == metadata_package


def test_get_package_error():
    task = create_task(BaseSalesforcePushTask, options={})
    task.push = mock.MagicMock()
    task.push.get_package_objs.return_value = []
    with pytest.raises(PushApiObjectNotFound):
        task._get_package(NAMESPACE)


def test_schedule_push_org_list_get_orgs(org_file):
    task = create_task(
        SchedulePushOrgList,
        options={
            "orgs": ORG_FILE,
            "version": VERSION,
            "namespace": NAMESPACE,
            "start_time": datetime.datetime.now(),
            "batch_size": 10,
        },
    )
    assert task._get_orgs() == ["00DS0000003TJJ6MAO", "00DS0000003TJJ6MAL"]


def test_schedule_push_org_list_init_options(org_file):
    task = create_task(
        SchedulePushOrgList,
        options={
            "orgs": ORG_FILE,
            "version": VERSION,
            "start_time": datetime.datetime.now(),
        },
    )
    task._init_task()
    assert task.options["namespace"] is None
    assert task.options["batch_size"] == 200
    assert task.options["orgs"] == ORG_FILE
    assert task.options["version"] == VERSION


def test_schedule_push_org_list_bad_start_time(org_file):
    task = create_task(
        SchedulePushOrgList,
        options={
            "orgs": ORG_FILE,
            "version": VERSION,
            "start_time": "2020-06-10T10:15",
            "namespace": NAMESPACE,
        },
    )
    task.push = mock.MagicMock()
    with pytest.raises(CumulusCIException):
        task._run_task()


def test_load_orgs_file(org_file):
    task = create_task(BaseSalesforcePushTask, options={})
    # testing with multiple orgs
    assert task._load_orgs_file(ORG_FILE) == [
        "00DS0000003TJJ6MAO",
        "00DS0000003TJJ6MAL",
    ]


def test_report_push_status_error():
    task = create_task(BaseSalesforcePushTask, options={})
    task.sf = mock.MagicMock()
    task.push_report = mock.MagicMock()
    task.sf.query_all.return_value = {"totalSize": 0, "records": []}
    with pytest.raises(PushApiObjectNotFound):
        task._report_push_status("0DV1R000000k9dEWAQ")


def test_get_push_request_job_results(
    package_push_job_success, package_push_job_failure, package_push_job_cancel
):
    task = create_task(BaseSalesforcePushTask, options={})
    task.sf = mock.MagicMock()
    task.push_report = mock.MagicMock()
    task.push_request = mock.MagicMock()
    task.push_request.get_push_job_objs.return_value = [
        package_push_job_success,
        package_push_job_failure,
        package_push_job_cancel,
    ]
    task._get_push_request_job_results()
    task.push_request.get_push_job_objs.assert_called_once()


def test_schedule_push_org_query_get_org_error():
    task = create_task(
        SchedulePushOrgQuery,
        options={
            "orgs": ORG,
            "version": VERSION,
            "namespace": NAMESPACE,
            "start_time": None,
            "batch_size": "200",
            "min_version": "1.1",
        },
    )
    task.push = mock.MagicMock()
    task.push_api = mock.MagicMock()
    task.sf = mock.Mock()
    task.push_api.return_query_records = mock.MagicMock()
    task.push_api.return_query_records.return_value = {"totalSize": "1"}
    task.sf.query_all.return_value = PACKAGE_OBJS
    with pytest.raises(ValueError):
        assert task._get_orgs() == [NAME]


def test_schedule_push_org_query_get_org():
    task = create_task(
        SchedulePushOrgQuery,
        options={
            "orgs": ORG,
            "version": VERSION,
            "namespace": NAMESPACE,
            "start_time": None,
            "batch_size": "200",
            "subscriber_where": "OrgType = 'Sandbox'",
        },
    )
    task.push = mock.MagicMock()
    task.push_api = mock.MagicMock()
    task.sf = mock.Mock()
    task.sf.query_all.return_value = PACKAGE_OBJ_SUBSCRIBER
    assert task._get_orgs() == ["bar"]


def test_schedule_push_org_list_run_task_with_time_assertion(org_file):
    task = create_task(
        SchedulePushOrgList,
        options={
            "orgs": ORG_FILE,
            "version": VERSION,
            "start_time": datetime.datetime(2021, 8, 20, 3, 55).strftime(
                "%Y-%m-%dT%H:%M"
            ),
            "namespace": NAMESPACE,
        },
    )
    task.push = mock.MagicMock()
    task.sf = mock.MagicMock()
    task.sf.query_all.return_value = PACKAGE_OBJS
    task.push.create_push_request.return_value = (task.sf.query_all.return_value, 2)
    task._run_task()
    task.push.create_push_request.assert_called_once_with(
        task.push.get_package_objs()
        .__getitem__()
        .get_package_version_objs()
        .__getitem__(),
        ["00DS0000003TJJ6MAO", "00DS0000003TJJ6MAL"],
        datetime.datetime(2021, 8, 20, 3, 55),
    )


def test_schedule_push_org_list_run_task_without_time(org_file):
    task = create_task(
        SchedulePushOrgList,
        options={"orgs": ORG_FILE, "version": VERSION, "namespace": NAMESPACE},
    )
    task.push = mock.MagicMock()
    task.sf = mock.MagicMock()
    task.sf.query_all.return_value = PACKAGE_OBJS
    task.push.create_push_request.return_value = (task.sf.query_all.return_value, 2)
    task._run_task()
    task.push.create_push_request.assert_called_once()


def test_schedule_push_org_list_run_task_without_orgs(empty_org_file):
    task = create_task(
        SchedulePushOrgList,
        options={
            "orgs": ORG_FILE,
            "version": VERSION,
            "namespace": NAMESPACE,
            "start_time": datetime.datetime(2021, 8, 19, 23, 18, 34).strftime(
                "%Y-%m-%dT%H:%M"
            ),
        },
    )
    task.push = mock.MagicMock()
    task.push_request = mock.MagicMock()
    task.sf = mock.MagicMock()
    task.sf.query_all.return_value = PACKAGE_OBJS
    task.push.create_push_request.return_value = (task.sf.query_all.return_value, 0)
    task._run_task()
    task.push.create_push_request.assert_called_once_with(
        task.push.get_package_objs()
        .__getitem__()
        .get_package_version_objs()
        .__getitem__(),
        [],
        datetime.datetime(2021, 8, 19, 23, 18),
    )


def test_schedule_push_org_list_run_task_many_orgs(org_file):
    task = create_task(
        SchedulePushOrgList,
        options={
            "orgs": ORG_FILE,
            "version": VERSION,
            "namespace": NAMESPACE,
            "start_time": datetime.datetime(2021, 8, 19, 23, 18, 34).strftime(
                "%Y-%m-%dT%H:%M"
            ),
        },
    )
    task.push = mock.MagicMock()
    task.sf = mock.MagicMock()
    task.sf.query_all.return_value = PACKAGE_OBJS
    task.push.create_push_request.return_value = (task.sf.query_all.return_value, 1001)
    task._run_task()
    task.push.create_push_request.assert_called_once_with(
        task.push.get_package_objs()
        .__getitem__()
        .get_package_version_objs()
        .__getitem__(),
        ["00DS0000003TJJ6MAO", "00DS0000003TJJ6MAL"],
        datetime.datetime(2021, 8, 19, 23, 18),
    )


def test_schedule_push_org_list_run_task_many_orgs_now(org_file):
    query = "SELECT Id, PackagePushRequestId, SubscriberOrganizationKey, Status FROM PackagePushJob WHERE Id = '0DV1R000000k9dEWAQ'"
    task = create_task(
        SchedulePushOrgList,
        options={
            "orgs": ORG_FILE,
            "version": VERSION,
            "namespace": NAMESPACE,
            "start_time": "now",
        },
    )
    task.push = mock.MagicMock()
    task.sf = mock.MagicMock()
    task.sf.query_all.return_value = PACKAGE_OBJS
    task.push.create_push_request.return_value = (task.sf.query_all.return_value, 1001)
    task._run_task()
    task.sf.query_all.assert_called_with(query)
