import pytest
import mock
import responses
import os
import copy
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


def test_report_push_status():
    query = "SELECT Id, PackagePushRequestId, SubscriberOrganizationKey, Status FROM PackagePushJob WHERE Id = '0DV1R000000k9dEWAQ'"
    task = create_task(BaseSalesforcePushTask, options={})
    task.sf = mock.MagicMock()
    task.push_report = mock.MagicMock()
    # task.push_report.get_push_request_objs.return_value = None
    get_package_objs_result = {
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
    push_request_result_succeded = copy.deepcopy(push_request_result)
    push_request_result_inprogress = copy.deepcopy(push_request_result)
    push_request_result_succeded["records"][0]["Status"] = "Succeeded"
    push_request_result_inprogress["records"][0]["Status"] = "In Progress"
    task.sf.query_all.return_value = None
    task.push_report.get_package_objs.side_effect = [
        push_request_result_inprogress,
        push_request_result_succeded,
    ]

    # task.get_packages = mock.MagicMock(return_value={"Name": NAME})
    with pytest.raises(PushApiObjectNotFound):
        task._report_push_status("0DV1R000000k9dEWAQ")
    # task.sf.query_all.assert_called_with(query)


#######WIP################
def test_report_push_status():
    query = "SELECT Id, PackagePushRequestId, SubscriberOrganizationKey, Status FROM PackagePushJob WHERE Id = '0DV1R000000k9dEWAQ'"
    task = create_task(BaseSalesforcePushTask, options={})
    task.sf = mock.MagicMock()
    task.push_report = mock.MagicMock()

    task.push_report.get_push_request_objs.return_value = None
    push_request_result = {
        "totalSize": 1,
        "done": True,
        "records": [
            {
                "attributes": {
                    "type": "PackagePushRequest",
                    "url": "/services/data/v48.0/sobjects/PackagePushRequest/0DV1R000000k9dEWAQ",
                },
                "Id": "0DV1R000000k9dEWAQ",
                "PackageVersionId": "04t1R000000s4PJQAY",
                "ScheduledStartTime": "2020-07-02T08:03:49.000+0000",
                "Status": "Failed",
            }
        ],
    }
    get_package_objs_result = {
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
    push_request_result_succeded = copy.deepcopy(push_request_result)
    push_request_result_inprogress = copy.deepcopy(push_request_result)
    push_request_result_succeded["records"][0]["Status"] = "Succeeded"
    push_request_result_inprogress["records"][0]["Status"] = "In Progress"
    task.sf.query_all.return_value = get_package_objs_result
    task.push_report.get_package_objs.side_effect = [
        push_request_result_inprogress,
        push_request_result_succeded,
    ]

    # task.get_packages = mock.MagicMock(return_value={"Name": NAME})
    task._report_push_status("0DV1R000000k9dEWAQ")
    task.sf.query_all.assert_called_with(query)


###########WIP################


def test_schedule_push_org_query_get_org_error():
    query = "SELECT Id, MetadataPackageVersionId, InstalledStatus, OrgName, OrgKey, OrgStatus, OrgType from PackageSubscriber"
    task = create_task(
        SchedulePushOrgQuery,
        options={
            "orgs": ORG,
            "version": "1.2.3",
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
    # task._get_orgs()
    with pytest.raises(ValueError):
        assert task._get_orgs() == [NAME]


def test_schedule_push_org_query_get_org():
    query = "SELECT Id, MetadataPackageVersionId, InstalledStatus, OrgName, OrgKey, OrgStatus, OrgType from PackageSubscriber"
    task = create_task(
        SchedulePushOrgQuery,
        options={
            "orgs": ORG,
            "version": "1.2.3",
            "namespace": NAMESPACE,
            "start_time": None,
            "batch_size": "200",
        },
    )
    task.push = mock.MagicMock()
    task.push_api = mock.MagicMock()
    task.sf = mock.Mock()
    task.push_api.return_query_records = mock.MagicMock()
    task.push_api.return_query_records.return_value = {"totalSize": "1"}
    task.sf.query_all.return_value = PACKAGE_OBJS
    # task._get_orgs()
    assert task._get_orgs() == [NAME]


# def test_schedule_push_org_list_run_task():
#     with open("output.txt", "w") as file:
#         file.write("\n00DS0000003TJJ6MAO\n00DS0000003TJJ6MAL")
#     task = create_task(
#         SchedulePushOrgList,
#         options={
#             "orgs": "output.txt",
#             "version": "1.2.3",
#             "start_time": "now",
#             "namespace": "foo",
#         },
#     )
#     task.push = mock.MagicMock()
#     task.sf = mock.MagicMock()
#     task.push.create_push_request.return_value = ("033xxxxxxxxx", 1)
#     task._run_task()
#     task._run_task.assert_called_once_with(task.options)
#     assert task.options[
#         "start_time"
#     ] == datetime.datetime.utcnow() + datetime.timedelta(seconds=5)
#     os.remove("output.txt")
# def test_schedule_push_org_list_run_task():
#     with open("output.txt", "w") as file:
#         file.write("\n00DS0000003TJJ6MAO\n00DS0000003TJJ6MAL")
#     task = create_task(
#         SchedulePushOrgList,
#         options={
#             "orgs": "output.txt",
#             "version": "1.2.3",
#             "start_time": "2020-07-10T10:15",
#             "namespace": "foo",
#         },
#     )
#     task.push = mock.MagicMock()
#     task._run_task()
#     os.remove("output.txt")
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
