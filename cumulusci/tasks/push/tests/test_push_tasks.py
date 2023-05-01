import datetime
import logging
import os
from unittest import mock

import pytest
from dateutil import tz

from cumulusci.core.exceptions import (
    CumulusCIException,
    PushApiObjectNotFound,
    TaskOptionsError,
)
from cumulusci.tasks.push.push_api import (
    MetadataPackage,
    MetadataPackageVersion,
    PackagePushJob,
    PackagePushRequest,
    SalesforcePushApi,
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
CSV_FILE_TEXT = """OrganizationId,OrgName,OrgType,OrgStatus,InstanceName,ErrorSeverity,ErrorTitle,ErrorType,ErrorMessage,Gack Id,Stacktrace Id,\n00D5w000004zXXX,,,,,Error,Unexpected Failure,UnclassifiedError,An unexpected failure was experienced during the upgrade. The subscriber's organization was unaffected. Contact salesforce.com Support through your normal channels and provide the following error number: 1351793968-113330 (-1345328791).,1351793968-113330,-1345328791\n00D5w000005VXXX,,,,,Error,Unexpected Failure,UnclassifiedError,An unexpected failure was experienced during the upgrade. The subscriber's organization was unaffected. Contact salesforce.com Support through your normal channels and provide the following error number: 822524189-80345 (-2096886284).,822524189-80345,-2096886284"""

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
            "start_time": datetime.datetime.now(tz.UTC),
            "batch_size": 10,
        },
    )
    assert task._get_orgs() == ["00DS0000003TJJ6MAO", "00DS0000003TJJ6MAL"]


def test_schedule_push_org_list__get_orgs__non_default_csv_field(tmp_path):
    orgs = tmp_path / ORG_FILE
    orgs.write_text(CSV_FILE_TEXT.replace("OrganizationId", "OrgId"))
    task = create_task(
        SchedulePushOrgList,
        options={
            "version": VERSION,
            "namespace": NAMESPACE,
            "start_time": datetime.datetime.now(tz.UTC),
            "batch_size": 10,
            "csv": orgs,
            "csv_field_name": "OrgId",
        },
    )
    assert task._get_orgs() == ["00D5w000004zXXX", "00D5w000005VXXX"]


def test_schedule_push_org_list_get_orgs_and_csv(tmp_path):
    orgs = tmp_path / ORG_FILE
    orgs.write_text(CSV_FILE_TEXT)
    with pytest.raises(TaskOptionsError):
        create_task(
            SchedulePushOrgList,
            options={
                "orgs": orgs,
                "version": VERSION,
                "namespace": NAMESPACE,
                "start_time": datetime.datetime.now(tz.UTC),
                "batch_size": 10,
                "csv_field_name": "OrganizationId",
                "csv": orgs,
            },
        )


def test_schedule_push_org_list_init_options(org_file):
    task = create_task(
        SchedulePushOrgList,
        options={
            "orgs": ORG_FILE,
            "version": VERSION,
            "start_time": datetime.datetime.now(tz.UTC),
        },
    )
    task._init_task()
    assert task.options["namespace"] == task.project_config.project__package__namespace
    assert task.options["batch_size"] == 200
    assert task.options["orgs"] == ORG_FILE
    assert task.options["version"] == VERSION


# Should set csv_field_name to OrganizationId by default
def test_schedule_push_org_list__init_options__csv_field_default(tmp_path):
    orgs = tmp_path / ORG_FILE
    orgs.write_text(CSV_FILE_TEXT)
    task = create_task(
        SchedulePushOrgList,
        options={
            "version": VERSION,
            "namespace": NAMESPACE,
            "start_time": datetime.datetime.now(),
            "batch_size": 10,
            "csv": orgs,
        },
    )
    assert task._get_orgs() == ["00D5w000004zXXX", "00D5w000005VXXX"]


def test_schedule_push_org_list__init_options__missing_csv(tmp_path):
    orgs = tmp_path / ORG_FILE
    orgs.write_text(CSV_FILE_TEXT)
    with pytest.raises(TaskOptionsError):
        create_task(
            SchedulePushOrgList,
            options={
                "orgs": orgs,
                "version": VERSION,
                "namespace": NAMESPACE,
                "start_time": datetime.datetime.now(),
                "batch_size": 10,
                "csv_field_name": "OrganizationId",
            },
        )


def test_schedule_push_org_list_start_time_in_past(org_file):
    task = create_task(
        SchedulePushOrgList,
        options={
            "orgs": ORG_FILE,
            "version": VERSION,
            "start_time": "2020-06-10T10:15Z",
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
    package_push_job_success, package_push_job_failure, package_push_job_cancel, caplog
):
    caplog.set_level(logging.INFO)
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
    assert "Push complete: 1 succeeded, 1 failed, 1 canceled" in caplog.text


def test_schedule_push_org_query_get_org_error():
    task = create_task(
        SchedulePushOrgQuery,
        options={
            "orgs": ORG,
            "version": VERSION,
            "start_time": None,
            "min_version": "1.1",
        },
    )
    task.push = mock.MagicMock()
    task.push_api = mock.MagicMock()
    task.bulk = mock.MagicMock()
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
    task.bulk = None
    task.sf = mock.Mock()
    task.sf.query_all = mock.MagicMock()
    task.sf.query_all.return_value = PACKAGE_OBJ_SUBSCRIBER
    # task.push_api.return_query_records.return_value = {"totalSize": "1"}
    assert task._get_orgs() == ["bar"]


@mock.patch("cumulusci.tasks.push.push_api.BulkApiQueryOperation")
def test_schedule_push_org_bulk_query_get_org(BulkAPI):  # push_api):
    expected_result = [
        {
            "Id": "0Hb0R0000009fPASAY",
            "MetadataPackageVersionId": "04t1J000000gQziQAE",
            "InstalledStatus": "i",
            "OrgName": "CumulusCI-Test Dev Workspace",
            "OrgKey": "00D0R0000000kN4",
            "OrgStatus": "Trial",
            "OrgType": "Sandbox",
        }
    ]
    push_api = SalesforcePushApi(
        mock.MagicMock(), mock.MagicMock(), None, None, None, mock.MagicMock()
    )
    bulk_api = mock.MagicMock(get_results=mock.MagicMock())
    bulk_api.get_results.return_value = [
        [
            "0Hb0R0000009fPASAY",
            "04t1J000000gQziQAE",
            "i",
            "CumulusCI-Test Dev Workspace",
            "00D0R0000000kN4",
            "Trial",
            "Sandbox",
        ]
    ]
    BulkAPI.return_value = bulk_api
    result = push_api.return_query_records(
        "SELECT Id, MetadataPackageVersionId, InstalledStatus, OrgName, OrgKey, OrgStatus, OrgType from PackageSubscriber WHERE (InstalledStatus = 'i' AND (OrgType = 'Sandbox')",
        [
            "Id",
            "MetadataPackageVersionId",
            "InstalledStatus",
            "OrgName",
            "OrgKey",
            "OrgStatus",
            "OrgType",
        ],
        "foo",
    )
    assert result == expected_result


@pytest.mark.parametrize(
    "test_date_str", ["2028-01-01 12:30:30 CST", "06-18-2022 07:21PM PDT", "2028-28-01"]
)
def test_schedule_push_org_list_run_task_with_bad_datestr(org_file, test_date_str):
    task = create_task(
        SchedulePushOrgList,
        options={
            "orgs": ORG_FILE,
            "version": VERSION,
            "start_time": test_date_str,
            "namespace": NAMESPACE,
        },
    )
    task.push = mock.MagicMock()
    task.sf = mock.MagicMock()
    task.sf.query_all.return_value = PACKAGE_OBJS
    task.push.create_push_request.return_value = ("0DV000000000001", 2)
    with pytest.raises((ValueError, CumulusCIException)):
        task._run_task()


def test_schedule_push_org_list_run_task_with_isofmt_assertion(org_file):
    target_dt = datetime.datetime.now(tz.UTC).replace(microsecond=0)
    target_dt += datetime.timedelta(hours=8)
    start_time_str = target_dt.isoformat()

    task = create_task(
        SchedulePushOrgList,
        options={
            "orgs": ORG_FILE,
            "version": VERSION,
            "start_time": start_time_str,
            "namespace": NAMESPACE,
        },
    )
    task.push = mock.MagicMock()
    task.sf = mock.MagicMock()
    task.sf.query_all.return_value = PACKAGE_OBJS
    task.push.create_push_request.return_value = ("0DV000000000001", 2)
    task._run_task()
    task.push.create_push_request.assert_called_once_with(
        mock.ANY,
        ["00DS0000003TJJ6MAO", "00DS0000003TJJ6MAL"],
        target_dt,
    )


def test_schedule_push_org_list_run_task_without_time(org_file):
    task = create_task(
        SchedulePushOrgList,
        options={"orgs": ORG_FILE, "version": VERSION, "namespace": NAMESPACE},
    )
    task.push = mock.MagicMock()
    task.sf = mock.MagicMock()
    task.sf.query_all.return_value = PACKAGE_OBJS
    task.push.create_push_request.return_value = ("0DV000000000001", 2)
    task._run_task()
    task.push.create_push_request.assert_called_once()


def test_schedule_push_org_list_run_task_without_orgs(empty_org_file):
    target_date = (datetime.datetime.now() + datetime.timedelta(days=1)).replace(
        second=0, microsecond=0
    )
    task = create_task(
        SchedulePushOrgList,
        options={
            "orgs": ORG_FILE,
            "version": VERSION,
            "namespace": NAMESPACE,
            "start_time": target_date.strftime("%Y-%m-%dT%H:%M"),
        },
    )
    task.push = mock.MagicMock()
    task.push_request = mock.MagicMock()
    task.sf = mock.MagicMock()
    task.sf.query_all.return_value = PACKAGE_OBJS
    task.push.create_push_request.return_value = ("0DV000000000001", 0)
    task._run_task()
    task.push.create_push_request.assert_called_once_with(
        mock.ANY, [], target_date.replace(tzinfo=tz.UTC)
    )


def test_schedule_push_org_list_run_task_many_orgs(org_file):
    target_date = (datetime.datetime.now() + datetime.timedelta(days=1)).replace(
        second=0, microsecond=0
    )
    task = create_task(
        SchedulePushOrgList,
        options={
            "orgs": ORG_FILE,
            "version": VERSION,
            "namespace": NAMESPACE,
            "start_time": target_date.strftime("%Y-%m-%dT%H:%M"),
        },
    )
    task.push = mock.MagicMock()
    task.sf = mock.MagicMock()
    task.sf.query_all.return_value = PACKAGE_OBJS
    task.push.create_push_request.return_value = ("0DV000000000001", 1001)
    task._run_task()
    task.push.create_push_request.assert_called_once_with(
        mock.ANY,
        ["00DS0000003TJJ6MAO", "00DS0000003TJJ6MAL"],
        target_date.replace(tzinfo=tz.UTC),
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
    task.push.create_push_request.return_value = ("0DV000000000001", 1001)
    task._run_task()
    task.sf.query_all.assert_called_with(query)
