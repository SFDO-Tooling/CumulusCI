import datetime
import os
from unittest import mock

import pytest

from cumulusci.core.exceptions import CumulusCIException, PushApiObjectNotFound
from cumulusci.tasks.push.push_api import MetadataPackage
from cumulusci.tasks.push.tasks import (
    BaseSalesforcePushTask,
    FilterSubscriberList,
    GetSubscriberList,
    SchedulePushOrgList,
    SchedulePushOrgQuery,
)
from cumulusci.tasks.salesforce.tests.util import create_task

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
    assert task.options["namespace"] is None
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


def test_load_orgs_file_space():
    # creating sample org file for testing
    # testing with empty file
    with open("output.txt", "w") as file:
        file.write("  \n")
        task = create_task(BaseSalesforcePushTask, options={})
        assert task._load_orgs_file("output.txt") == []
    #
    # testing with multiple orgs
    with open("output.txt", "r") as file:
        assert task._load_orgs_file("output.txt") == []
    os.remove("output.txt")


def test_load_orgs_file():
    # creating sample org file for testing
    # testing with empty file
    with open("output.txt", "w") as file:
        file.write(
            "OrganizationId,OrgName,OrgType,OrgStatus,InstanceName,ErrorSeverity,ErrorTitle,ErrorType,ErrorMessage,Gack Id,Stacktrace Id,\n00D5w000004zLhX,,,,,Error,Unexpected Failure,UnclassifiedError,An unexpected failure was experienced during the upgrade. The subscriber's organization was unaffected. Contact salesforce.com Support through your normal channels and provide the following error number: 1351793968-113330 (-1345328791).,1351793968-113330,-1345328791\n00D5w000005V5Dq,,,,,Error,Unexpected Failure,UnclassifiedError,An unexpected failure was experienced during the upgrade. The subscriber's organization was unaffected. Contact salesforce.com Support through your normal channels and provide the following error number: 822524189-80345 (-2096886284).,822524189-80345,-2096886284"
        )
        task = create_task(BaseSalesforcePushTask, options={})
        assert task._load_orgs_file("output.txt") == []
    #
    # testing with multiple orgs
    with open("output.txt", "r") as file:
        assert task._load_orgs_file("output.txt") == [
            "OrganizationId",
            "00D5w000004zLhX",
            "00D5w000005V5Dq",
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


def test_report_push_status_error():
    task = create_task(BaseSalesforcePushTask, options={})
    task.sf = mock.MagicMock()
    task.push_report = mock.MagicMock()
    task.sf.query_all.return_value = {"totalSize": 1, "records": []}
    with pytest.raises(PushApiObjectNotFound):
        task._report_push_status("0DV1R000000k9dEWAQ")


def test_get_push_request_job_results():
    task = create_task(BaseSalesforcePushTask, options={})
    task.sf = mock.MagicMock()
    task.push_report = mock.MagicMock()
    task.push_request = mock.MagicMock()
    assert task._get_push_request_job_results() is None


# def test_report_push_status():
#     query1 = "SELECT Id, PackagePushRequestId, SubscriberOrganizationKey, Status FROM PackagePushJob WHERE Id = '0DV1R000000k9dEWAQ'"
#     query2 = "SELECT Id, MetadataPackageVersionId, InstalledStatus, OrgName, OrgKey, OrgStatus, OrgType from PackageSubscriber WHERE OrgKey = '00DS0000003TJJ6MAO'"
#     task = create_task(BaseSalesforcePushTask, options={})
#     task.sf = mock.MagicMock()
#     task.push_report = mock.MagicMock()

#     # push_request_result = {
#     #     "totalSize": 1,
#     #     "done": True,
#     #     "records": [
#     #         {
#     #             "attributes": {
#     #                 "type": "PackagePushRequest",
#     #                 "url": "/services/data/v48.0/sobjects/PackagePushRequest/0DV1R000000k9dEWAQ",
#     #             },
#     #             "Id": "0DV1R000000k9dEWAQ",
#     #             "PackageVersionId": "04t1R000000s4PJQAY",
#     #             "ScheduledStartTime": "2020-07-02T08:03:49.000+0000",
#     #             "Status": "Failed",
#     #         }
#     #     ],
#     # }
#     push_request_result_succeded = copy.deepcopy(PACKAGE_OBJS)
#     # push_request_result_inprogress = copy.deepcopy(push_request_result)
#     push_request_result_succeded["records"][0]["Status"] = "X-GAMES"
#     # push_request_result_succeded["Name"] = push_request_result_succeded
#     # get_package_objs_result["Name"] = "cci"
#     task.sf.query_all.return_value = PACKAGE_OBJS
#     task.push_report.get_push_request_objs.return_value = task.sf.query_all.return_value

#     # task.push_report.get_push_request_objs.side_effect = [
#     #     push_request_result_succeded,
#     #     PACKAGE_OBJS,
#     # ]

#     task._report_push_status("0DV1R000000k9dEWAQ")
#     task.sf.query_all.assert_called_with(query1)


# ##########WIP################


def test_schedule_push_org_query_get_org_error():
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
    with pytest.raises(ValueError):
        assert task._get_orgs() == [NAME]


def test_schedule_push_org_query_get_org():
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
    assert task._get_orgs() == [NAME]


def test_schedule_push_org_list_run_task_with_time():
    query = "SELECT Id, PackagePushRequestId, SubscriberOrganizationKey, Status FROM PackagePushJob WHERE Id = '0DV1R000000k9dEWAQ'"

    with open("output.txt", "w") as file:
        file.write("\n00DS0000003TJJ6MAO\n00DS0000003TJJ6MAL")
    task = create_task(
        SchedulePushOrgList,
        options={
            "orgs": "output.txt",
            "version": "1.2.3",
            "start_time": "now",
            "namespace": "foo",
        },
    )
    task.push = mock.MagicMock()
    task.sf = mock.MagicMock()
    task.sf.query_all.return_value = PACKAGE_OBJS
    task.push.create_push_request.return_value = (task.sf.query_all.return_value, 1)
    task._run_task()
    task.sf.query_all.assert_called_with(query)


def test_schedule_push_org_list_run_task_without_time():
    with open("output.txt", "w") as file:
        file.write("\n00DS0000003TJJ6MAO\n00DS0000003TJJ6MAL")
    task = create_task(
        SchedulePushOrgList,
        options={"orgs": "output.txt", "version": "1.2.3", "namespace": "foo"},
    )
    task.push = mock.MagicMock()
    task.sf = mock.MagicMock()
    task.sf.query_all.return_value = PACKAGE_OBJS
    task.push.create_push_request.return_value = (task.sf.query_all.return_value, 1)
    assert task._run_task() is None


def test_schedule_push_org_list_run_task_without_orgs():
    with open("output.txt", "w") as file:
        file.write("\n00DS0000003TJJ6MAO\n00DS0000003TJJ6MAL")
    task = create_task(
        SchedulePushOrgList,
        options={
            "orgs": "output.txt",
            "version": "1.2.3",
            "namespace": "foo",
            "start_time": "now",
        },
    )
    task.push = mock.MagicMock()
    task.sf = mock.MagicMock()
    task.sf.query_all.return_value = PACKAGE_OBJS
    task.push.create_push_request.return_value = (task.sf.query_all.return_value, 0)
    assert task._run_task() is None


def test_schedule_push_org_list_run_task_many_orgs():
    with open("output.txt", "w") as file:
        file.write("\n00DS0000003TJJ6MAO\n00DS0000003TJJ6MAL")
    task = create_task(
        SchedulePushOrgList,
        options={
            "orgs": "output.txt",
            "version": "1.2.3",
            "namespace": "foo",
            "start_time": "now",
        },
    )
    task.push = mock.MagicMock()
    task.sf = mock.MagicMock()
    task.sf.query_all.return_value = PACKAGE_OBJS
    task.push.create_push_request.return_value = (task.sf.query_all.return_value, 1001)
    assert task._run_task() is None
