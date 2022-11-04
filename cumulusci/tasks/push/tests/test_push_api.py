import datetime
import json
from unittest import mock

import pytest
from simple_salesforce import SalesforceMalformedRequest

from cumulusci.tasks.push.push_api import (
    BasePushApiObject,
    MetadataPackage,
    MetadataPackageVersion,
    PackagePushError,
    PackagePushJob,
    PackagePushRequest,
    PackageSubscriber,
    SalesforcePushApi,
    batch_list,
)

NAME = "Chewbacca"
SF_ID = "033xxxxxxxxx"
PUSH_API = "push_api"
NAMESPACE = "namespace"
ORG_KEY = "bar"


@pytest.fixture
def metadata_package_versions(metadata_package):
    return [
        MetadataPackageVersion(
            push_api=PUSH_API,
            package=metadata_package,
            name=NAME,
            sf_id=SF_ID,
            state="Beta",
            major="3",
            minor="1",
            patch="1",
            build="1",
        ),
        MetadataPackageVersion(
            push_api=PUSH_API,
            package=metadata_package,
            name=NAME,
            sf_id=SF_ID,
            state="Beta",
            major="2",
            minor="1",
            patch="1",
            build="1",
        ),
        MetadataPackageVersion(
            push_api=PUSH_API,
            package=metadata_package,
            name=NAME,
            sf_id=SF_ID,
            state="Beta",
            major="1",
            minor="1",
            patch="1",
            build="1",
        ),
        MetadataPackageVersion(
            push_api=PUSH_API,
            package=metadata_package,
            name=NAME,
            sf_id=SF_ID,
            state="Beta",
            major="1",
            minor="1",
            patch="1",
            build="1",
        ),
        MetadataPackageVersion(
            push_api=PUSH_API,
            package=metadata_package,
            name=NAME,
            sf_id=SF_ID,
            state="Beta",
            major="1",
            minor="89",
            patch="1",
            build="1",
        ),
        MetadataPackageVersion(
            push_api=PUSH_API,
            package=metadata_package,
            name=NAME,
            sf_id=SF_ID,
            state="Beta",
            major="89",
            minor="1",
            patch="1",
            build="1",
        ),
        MetadataPackageVersion(
            push_api=PUSH_API,
            package=metadata_package,
            name=NAME,
            sf_id=SF_ID,
            state="Beta",
            major="1",
            minor="1",
            patch="89",
            build="1",
        ),
        MetadataPackageVersion(
            push_api=PUSH_API,
            package=metadata_package,
            name=NAME,
            sf_id=SF_ID,
            state="Beta",
            major="1",
            minor="1",
            patch="1",
            build="89",
        ),
        MetadataPackageVersion(
            push_api=PUSH_API,
            package=metadata_package,
            name=NAME,
            sf_id=SF_ID,
            state="Beta",
            major="4",
            minor="3",
            patch="1",
            build="1",
        ),
    ]


@pytest.fixture
def sf_push_api():
    return SalesforcePushApi(sf=mock.Mock(), logger=mock.Mock())


@pytest.fixture
def metadata_package():
    return MetadataPackage(
        push_api=mock.MagicMock(), name=NAME, sf_id=SF_ID, namespace=NAMESPACE
    )


@pytest.fixture
def metadata_package_version(metadata_package):
    return MetadataPackageVersion(
        push_api=mock.MagicMock(),
        package=metadata_package,
        name=NAME,
        sf_id=SF_ID,
        state="Beta",
        major="4",
        minor="3",
        patch="2",
        build="1",
    )


@pytest.fixture
def package_push_job():
    return PackagePushJob(
        push_api=mock.MagicMock(),
        request="",
        org="00DS0000003TJJ6MAO",
        status="Succeeded",
        sf_id=SF_ID,
    )


@pytest.fixture
def package_subscriber():
    return PackageSubscriber(
        push_api=mock.MagicMock(),
        version="1.2.3",
        status="Succeeded",
        org_name="foo",
        org_key="bar",
        org_status="Succeeded",
        org_type="Sandbox",
        sf_id=SF_ID,
    )


@pytest.fixture
def package_push_error():
    return PackagePushError(
        push_api="foo",
        sf_id=SF_ID,
        job="Foo",
        severity="high",
        error_type="bar",
        title="foo_bar",
        message="The foo hit the bar",
        details="foo bar, foo, foo bar",
    )


@pytest.fixture
def package_push_request():
    return PackagePushRequest(
        push_api=mock.MagicMock(),
        version="1.2.3",
        start_time="12:03",
        status="Succeeded",
        sf_id=SF_ID,
    )


def test_base_push_format_where():
    base_obj = BasePushApiObject()
    field_name = "id_field"
    sf_id = "006000000XXX000"
    where_clause = "id=001000000XXX000"
    base_obj.sf_id = sf_id

    returned = base_obj.format_where(field_name, where_clause)
    assert "{} = '{}' AND ({})".format(field_name, sf_id, where_clause) == returned

    returned = base_obj.format_where(field_name, None)
    assert "{} = '{}'".format(field_name, sf_id) == returned


def test_metadata_package_init():

    package = MetadataPackage(PUSH_API, NAME)
    assert package.push_api == PUSH_API
    assert package.sf_id is None
    assert package.name == NAME
    assert package.namespace is None

    package = MetadataPackage(PUSH_API, NAME, SF_ID, NAMESPACE)
    assert package.push_api == PUSH_API
    assert package.sf_id == SF_ID
    assert package.name == NAME
    assert package.namespace == NAMESPACE


def test_metadata_package_get_versions(metadata_package):
    expected = f"MetadataPackageId = '{SF_ID}'"
    metadata_package.get_package_versions()
    metadata_package.push_api.get_package_versions.assert_called_once_with(
        expected, None
    )


def test_metadata_package_get_version_objs(metadata_package):
    expected = f"MetadataPackageId = '{SF_ID}'"
    metadata_package.get_package_version_objs()
    metadata_package.push_api.get_package_version_objs.assert_called_once_with(
        expected, None
    )


def test_metadata_package_get_versions_by_id(metadata_package):
    expected = f"MetadataPackageId = '{SF_ID}'"
    metadata_package.get_package_versions_by_id()
    metadata_package.push_api.get_package_versions_by_id.assert_called_once_with(
        expected, None
    )


def test_metadata_package_version_version_number(metadata_package_version):
    expected = "4.3.2 (Beta 1)"
    actual = metadata_package_version.version_number
    assert expected == actual


def test_sf_push_return_query_records(sf_push_api):
    query = "SELECT Id FROM Account"
    records = ["record 1", "record 2", "record 3"]
    results = {"totalSize": 10, "records": records}

    sf_push_api.sf.query_all.return_value = results
    returned = sf_push_api.return_query_records(query)
    assert len(records) == len(returned)

    results["totalSize"] = 0
    sf_push_api.sf.query_all.return_value = results
    returned = sf_push_api.return_query_records(query)
    assert [] == returned


def test_sf_push_format_where(sf_push_api):
    returned = sf_push_api.format_where_clause(None)
    assert returned == ""

    default_where = "Id='001000000XXX000'"
    sf_push_api.default_where = {"Account": default_where}
    returned = sf_push_api.format_where_clause(None, "Object__c")
    assert returned == ""

    returned = sf_push_api.format_where_clause(None, "Account")
    assert " WHERE ({})".format(default_where) == returned

    where = "IsDeleted=False"
    returned = sf_push_api.format_where_clause(where)
    assert " WHERE {}".format(where) == returned
    # No default where for Object__C
    returned = sf_push_api.format_where_clause(where, "Object__c")
    assert " WHERE {}".format(where) == returned

    returned = sf_push_api.format_where_clause(where, "Account")
    assert " WHERE ({}) AND ({})".format(default_where, where) == returned


def test_sf_push_add_query_limit(sf_push_api):
    query = "SELECT Id FROM Account"
    limit = 100
    returned = sf_push_api.add_query_limit(query, limit)
    assert "{} LIMIT {}".format(query, limit) == returned


def test_sf_push_add_query_no_limit(sf_push_api):
    query = "SELECT Id FROM Account"
    returned = sf_push_api.add_query_limit(query, None)
    assert f"{query}" == returned


def test_sf_push_get_packages(sf_push_api):
    query = "SELECT id, name, namespaceprefix FROM MetadataPackage WHERE Name='foo'"
    sf_push_api.return_query_records = mock.MagicMock()
    sf_push_api.get_packages("Name='foo'", None)
    sf_push_api.return_query_records.assert_called_once_with(query)


def test_sf_push_get_package_objs(sf_push_api, metadata_package):
    sf_push_api.get_packages = mock.MagicMock()
    packages = {
        "Id": metadata_package.sf_id,
        "Name": metadata_package.name,
        "NamespacePrefix": metadata_package.namespace,
    }
    sf_push_api.get_packages.return_value = [packages]
    actual_result_list = sf_push_api.get_package_objs("Name='foo'", None)
    assert len(actual_result_list) == 1
    actual_result = actual_result_list[0]
    assert packages["Id"] == actual_result.sf_id
    assert packages["Name"] == actual_result.name
    assert packages["NamespacePrefix"] == actual_result.namespace


def test_sf_push_get_packages_by_id(sf_push_api, metadata_package):
    sf_push_api.get_package_objs = mock.MagicMock()
    sf_push_api.get_package_objs.return_value = [metadata_package]
    package_expected = {metadata_package.sf_id: metadata_package}
    package_result = sf_push_api.get_packages_by_id("Name='foo'", None)
    sf_push_api.get_package_objs.assert_called_with("Name='foo'", None)
    assert package_expected == package_result


def test_sf_push_get_package_versions(sf_push_api):
    query = "SELECT Id, Name, MetadataPackageId, ReleaseState, MajorVersion, MinorVersion, PatchVersion, BuildNumber FROM MetadataPackageVersion WHERE Name='foo' ORDER BY MajorVersion DESC, MinorVersion DESC, PatchVersion, BuildNumber DESC"
    sf_push_api.return_query_records = mock.MagicMock()
    sf_push_api.get_package_versions("Name='foo'", None)
    sf_push_api.return_query_records.assert_called_once_with(query)


def test_sf_push_get_package_version_objs(sf_push_api):
    query = "SELECT Id, Name, MetadataPackageId, ReleaseState, MajorVersion, MinorVersion, PatchVersion, BuildNumber FROM MetadataPackageVersion WHERE Name='foo' ORDER BY MajorVersion DESC, MinorVersion DESC, PatchVersion, BuildNumber DESC"
    sf_push_api.return_query_records = mock.MagicMock()
    sf_push_api.get_package_version_objs("Name='foo'", None)
    sf_push_api.return_query_records.assert_called_with(query)


def test_sf_push_get_package_version_by_id(sf_push_api, metadata_package_version):
    sf_push_api.get_package_version_objs = mock.MagicMock()
    sf_push_api.get_package_version_objs.return_value = [metadata_package_version]
    package_expected = {metadata_package_version.sf_id: metadata_package_version}
    package_result = sf_push_api.get_package_versions_by_id("Name='foo'", None)
    sf_push_api.get_package_version_objs.assert_called_with("Name='foo'", None)
    assert package_expected == package_result


def test_sf_push_get_subscribers(sf_push_api):
    query = "SELECT Id, MetadataPackageVersionId, InstalledStatus, InstanceName, OrgName, OrgKey, OrgStatus, OrgType from PackageSubscriber WHERE Name='foo'"
    sf_push_api.return_query_records = mock.MagicMock()
    field_names = [
        "Id",
        "MetadataPackageVersionId",
        "InstalledStatus",
        "InstanceName",
        "OrgName",
        "OrgKey",
        "OrgStatus",
        "OrgType",
    ]
    sf_push_api.get_subscribers("Name='foo'", None)
    sf_push_api.return_query_records.assert_called_with(
        query, field_names=field_names, sobject="PackageSubscriber"
    )


def test_sf_push_get_subscriber_objs(sf_push_api):
    query = "SELECT Id, MetadataPackageVersionId, InstalledStatus, InstanceName, OrgName, OrgKey, OrgStatus, OrgType from PackageSubscriber WHERE Name='foo'"
    sf_push_api.return_query_records = mock.MagicMock()
    sf_push_api.get_subscriber_objs("Name='foo'", None)
    field_names = [
        "Id",
        "MetadataPackageVersionId",
        "InstalledStatus",
        "InstanceName",
        "OrgName",
        "OrgKey",
        "OrgStatus",
        "OrgType",
    ]
    sf_push_api.return_query_records.assert_called_with(
        query, field_names=field_names, sobject="PackageSubscriber"
    )


def test_sf_push_get_subscribers_by_org_key(sf_push_api, package_subscriber):
    sf_push_api.get_subscriber_objs = mock.MagicMock()
    sf_push_api.get_subscriber_objs.return_value = [package_subscriber]
    package_expected = {package_subscriber.org_key: package_subscriber}
    package_result = sf_push_api.get_subscribers_by_org_key("Name='foo'", None)
    sf_push_api.get_subscriber_objs.assert_called_with("Name='foo'", None)
    assert package_expected == package_result


def test_sf_push_get_push_requests(sf_push_api):
    query = "SELECT Id, PackageVersionId, ScheduledStartTime, Status FROM PackagePushRequest WHERE Name='foo' ORDER BY ScheduledStartTime DESC"
    sf_push_api.return_query_records = mock.MagicMock()
    sf_push_api.get_push_requests("Name='foo'", None)
    field_names = ["Id", "PackageVersionId", "ScheduledStartTime", "Status"]
    sf_push_api.return_query_records.assert_called_with(
        query, field_names=field_names, sobject="PackagePushRequest"
    )


def test_sf_push_get_push_request_objs(sf_push_api):
    query = "SELECT Id, PackageVersionId, ScheduledStartTime, Status FROM PackagePushRequest WHERE Name='foo' ORDER BY ScheduledStartTime DESC"
    sf_push_api.return_query_records = mock.MagicMock()
    sf_push_api.get_push_request_objs("Name='foo'", None)
    field_names = ["Id", "PackageVersionId", "ScheduledStartTime", "Status"]
    sf_push_api.return_query_records.assert_called_with(
        query, field_names=field_names, sobject="PackagePushRequest"
    )


def test_sf_push_get_push_requests_by_id(sf_push_api, package_push_request):
    sf_push_api.get_push_request_objs = mock.MagicMock()
    sf_push_api.get_push_request_objs.return_value = [package_push_request]
    package_expected = {package_push_request.sf_id: package_push_request}
    package_result = sf_push_api.get_push_requests_by_id("Name='foo'", None)
    sf_push_api.get_push_request_objs.assert_called_with("Name='foo'", None)
    assert package_expected == package_result


def test_sf_push_get_push_jobs(sf_push_api):
    query = "SELECT Id, PackagePushRequestId, SubscriberOrganizationKey, Status FROM PackagePushJob WHERE Name='foo'"
    sf_push_api.return_query_records = mock.MagicMock()
    sf_push_api.get_push_jobs("Name='foo'", None)
    sobject = "PackagePushJob"
    field_names = ["Id", "PackagePushRequestId", "SubscriberOrganizationKey", "Status"]
    sf_push_api.return_query_records.assert_called_with(
        query, field_names=field_names, sobject=sobject
    )


def test_sf_push_get_push_job_objs(sf_push_api):
    sobject = "PackagePushJob"
    field_names = ["Id", "PackagePushRequestId", "SubscriberOrganizationKey", "Status"]
    query = f"SELECT Id, PackagePushRequestId, SubscriberOrganizationKey, Status FROM {sobject} WHERE Name='foo'"
    sf_push_api.return_query_records = mock.MagicMock()
    sf_push_api.get_push_job_objs("Name='foo'", None)
    sf_push_api.return_query_records.assert_called_with(
        query, field_names=field_names, sobject=sobject
    )


def test_sf_push_get_push_jobs_by_id(sf_push_api, package_push_job):
    sf_push_api.get_push_job_objs = mock.MagicMock()
    sf_push_api.get_push_job_objs.return_value = [package_push_job]
    package_expected = {package_push_job.sf_id: package_push_job}
    package_result = sf_push_api.get_push_jobs_by_id("Name='foo'", None)
    sf_push_api.get_push_job_objs.assert_called_with("Name='foo'", None)
    assert package_expected == package_result


def test_sf_push_get_push_errors(sf_push_api):
    query = "SELECT Id, PackagePushJobId, ErrorSeverity, ErrorType, ErrorTitle, ErrorMessage, ErrorDetails FROM PackagePushError WHERE Name='foo'"
    sf_push_api.return_query_records = mock.MagicMock()
    sf_push_api.get_push_errors("Name='foo'", None)
    field_names = [
        "Id",
        "PackagePushJobId",
        "ErrorSeverity",
        "ErrorType",
        "ErrorTitle",
        "ErrorMessage",
        "ErrorDetails",
    ]
    sobject = "PackagePushError"
    sf_push_api.return_query_records.assert_called_with(
        query, field_names=field_names, sobject=sobject
    )


def test_sf_push_get_push_error_objs(sf_push_api, package_push_job, package_push_error):
    sf_push_api.get_push_job_objs = mock.MagicMock()
    sf_push_api.get_push_job_objs.return_value = [package_push_job]
    sf_push_api.lazy = ["jobs"]
    sf_push_api.get_push_errors = mock.MagicMock()
    record = {
        "ErrorSeverity": "high",
        "ErrorType": "bar",
        "ErrorTitle": "foo_bar",
        "ErrorMessage": "The foo hit the bar",
        "ErrorDetails": "foo bar, foo, foo bar",
        "Id": SF_ID,
        "PackagePushJobId": "pkg_push_id",
    }
    sf_push_api.get_push_errors.return_value = [record]

    actual_result_list = sf_push_api.get_push_error_objs("Name='foo'", None)
    sf_push_api.get_push_job_objs.assert_called_once_with(where="Id = 'pkg_push_id'")
    assert len(actual_result_list) == 1
    actual_result = actual_result_list[0]
    assert record["ErrorMessage"] == actual_result.message
    assert record["ErrorDetails"] == actual_result.details
    assert record["Id"] == actual_result.sf_id
    assert actual_result.job == package_push_job


def test_sf_push_get_push_errors_by_id(sf_push_api, package_push_error):
    sf_push_api.get_push_error_objs = mock.MagicMock()
    sf_push_api.get_push_error_objs.return_value = [package_push_error]
    push_error_expected = {package_push_error.sf_id: package_push_error}
    push_error_result = sf_push_api.get_push_errors_by_id("Name='foo'", None)
    sf_push_api.get_push_error_objs.assert_called_with("Name='foo'", None)
    assert push_error_expected == push_error_result


def test_sf_push_cancel_push_request(sf_push_api):
    ref_id = "12"
    sf_push_api.cancel_push_request(ref_id)
    sf_push_api.sf.PackagePushRequest.update.assert_called_once_with(
        ref_id, {"Status": "Canceled"}
    )


def test_sf_push_run_push_request(sf_push_api):
    ref_id = "12"
    sf_push_api.run_push_request(ref_id)
    sf_push_api.sf.PackagePushRequest.update.assert_called_once_with(
        ref_id, {"Status": "Pending"}
    )


def test_sf_push_create_push_request(sf_push_api, metadata_package_version):
    sf_push_api.batch_size = 1
    push_request_id = "0DV?xxxxxx?"
    version_id = metadata_package_version.sf_id = "0KM?xxxxx?"
    orgs = ["00D000000001", "00D000000002"]
    batch_0, batch_1 = [orgs[0]], [orgs[1]]
    start_time = datetime.datetime.now()

    sf_push_api.sf.PackagePushRequest.create.return_value = {"id": push_request_id}
    sf_push_api.sf.base_url = "url"
    sf_push_api._add_batch = mock.MagicMock(side_effect=[batch_0, batch_1])

    actual_id, actual_org_count = sf_push_api.create_push_request(
        metadata_package_version.sf_id, orgs, start_time
    )

    sf_push_api.sf.PackagePushRequest.create.assert_called_once_with(
        {
            "PackageVersionId": version_id,
            "ScheduledStartTime": start_time.isoformat(timespec="seconds"),
        }
    )
    assert mock.call(batch_0, push_request_id) in sf_push_api._add_batch.call_args_list
    assert mock.call(batch_1, push_request_id) in sf_push_api._add_batch.call_args_list
    assert push_request_id == actual_id
    assert 2 == actual_org_count


def test_sf_push_add_push_batch(sf_push_api, metadata_package_version):
    push_request_id = "0DV?xxxxxx?"
    metadata_package_version.sf_id = "0KM?xxxxx?"
    orgs = ["00D000000001", "00D000000002"]
    expected_records_json = json.dumps(
        {
            "records": [
                {
                    "attributes": {"type": "PackagePushJob", "referenceId": orgs[0]},
                    "PackagePushRequestId": push_request_id,
                    "SubscriberOrganizationKey": orgs[0],
                },
                {
                    "attributes": {"type": "PackagePushJob", "referenceId": orgs[1]},
                    "PackagePushRequestId": push_request_id,
                    "SubscriberOrganizationKey": orgs[1],
                },
            ]
        }
    )

    sf_push_api.sf.base_url = "base_url/"

    returned_batch = sf_push_api._add_batch(orgs, push_request_id)
    sf_push_api.sf._call_salesforce.assert_called_once_with(
        "POST", "base_url/composite/tree/PackagePushJob", data=expected_records_json
    )
    assert ["00D000000001", "00D000000002"] == returned_batch


def test_sf_push_add_push_batch_retry(sf_push_api, metadata_package_version):
    push_request_id = "0DV?xxxxxx?"
    orgs = ["00D000000001", "00D000000002", "00D000000003"]
    retry_response = {
        "results": [
            {
                "referenceId": orgs[0],
                "errors": [
                    {"message": "Something bad has happened! Whatever could it be?"}
                ],
            }
        ]
    }
    duplicate_response = {
        "results": [
            {
                "referenceId": orgs[1],
                "errors": [{"message": "", "statusCode": "DUPLICATE_VALUE"}],
            }
        ]
    }
    invalid_response = {
        "results": [
            {
                "referenceId": orgs[2],
                "errors": [{"message": "", "statusCode": "INVALID_OPERATION"}],
            }
        ]
    }

    sf_push_api.sf.base_url = "base_url/"
    sf_push_api.sf._call_salesforce.side_effect = [
        SalesforceMalformedRequest(
            "base_url/composite/tree/PackagePushJob",
            400,
            "resource_name",
            retry_response,
        ),
        SalesforceMalformedRequest(
            "base_url/composite/tree/PackagePushJob",
            400,
            "resource_name",
            duplicate_response,
        ),
        SalesforceMalformedRequest(
            "base_url/composite/tree/PackagePushJob",
            400,
            "resource_name",
            invalid_response,
        ),
        [],
    ]

    returned_batch = sf_push_api._add_batch(orgs, push_request_id)

    assert [orgs[0]] == returned_batch  # only remaining org should be retry-able
    assert 4 == sf_push_api.sf._call_salesforce.call_count


def test_push_batch_list():
    data = ["zero", "one", "two", "three"]

    actual_batch_list = batch_list(data, 1)
    expected_batch_list = [["zero"], ["one"], ["two"], ["three"]]
    assert expected_batch_list == actual_batch_list

    actual_batch_list = batch_list(data, 2)
    expected_batch_list = [["zero", "one"], ["two", "three"]]
    assert expected_batch_list == actual_batch_list

    actual_batch_list = batch_list(data, 3)
    expected_batch_list = [["zero", "one", "two"], ["three"]]
    assert expected_batch_list == actual_batch_list

    actual_batch_list = batch_list(data, 4)
    expected_batch_list = [["zero", "one", "two", "three"]]
    assert expected_batch_list == actual_batch_list

    actual_batch_list = batch_list(data, 5)
    assert expected_batch_list == actual_batch_list

    actual_batch_list = batch_list([], 2)
    expected_batch_list = []
    assert expected_batch_list == actual_batch_list


def test_version_init(metadata_package):
    package = MetadataPackageVersion(
        push_api=PUSH_API,
        package=metadata_package,
        name=NAME,
        sf_id=SF_ID,
        state="Beta",
        major="4",
        minor="3",
        patch="2",
        build="1",
    )
    assert package.push_api == PUSH_API
    assert package.package == metadata_package
    assert package.name == NAME
    assert package.sf_id == SF_ID
    assert package.state == "Beta"
    assert package.major == "4"
    assert package.minor == "3"
    assert package.patch == "2"
    assert package.build == "1"


def test_version_number(metadata_package_version):
    actual = metadata_package_version.version_number
    expected = "4.3.2 (Beta 1)"
    assert actual == expected


def test_metadata_package_get_subscribers(metadata_package_version):
    expected = f"MetadataPackageVersionId = '{SF_ID}'"
    metadata_package_version.get_subscribers()
    metadata_package_version.push_api.get_subscribers.assert_called_once_with(
        expected, None
    )


def test_metadata_package_get_subscriber_objects(metadata_package_version):
    expected = f"MetadataPackageVersionId = '{SF_ID}'"
    metadata_package_version.get_subscriber_objs()
    metadata_package_version.push_api.get_subscriber_objs.assert_called_once_with(
        expected, None
    )


def test_metadata_package_get_subscribers_by_org_key(metadata_package_version):
    expected = f"MetadataPackageVersionId = '{SF_ID}'"
    metadata_package_version.get_subscribers_by_org_key()
    metadata_package_version.push_api.get_subscribers_by_org_key.assert_called_once_with(
        expected, None
    )


def test_metadata_package_push_requests(metadata_package_version):
    expected = f"PackageVersionId = '{SF_ID}'"
    metadata_package_version.get_push_requests()
    metadata_package_version.push_api.get_push_requests.assert_called_once_with(
        expected, None
    )


def test_metadata_package_push_request_objs(metadata_package_version):
    expected = f"PackageVersionId = '{SF_ID}'"
    metadata_package_version.get_push_request_objs()
    metadata_package_version.push_api.get_push_request_objs.assert_called_once_with(
        expected, None
    )


def test_metadata_package_push_requests_by_id(metadata_package_version):
    expected = f"PackageVersionId = '{SF_ID}'"
    metadata_package_version.get_push_requests_by_id()
    metadata_package_version.push_api.get_push_requests_by_id.assert_called_once_with(
        expected, None
    )


def test_version_get_newer_query(metadata_package_version):
    expected = "MetadataPackageId = '033xxxxxxxxx' AND (MetadataPackageId = '033xxxxxxxxx' AND ReleaseState = 'Released')"
    metadata_package_version.get_newer_released_version_objs()
    metadata_package_version.package.push_api.get_package_version_objs.assert_called_once_with(
        expected, None
    )


def test_version_get_older_query(metadata_package_version):
    expected = "MetadataPackageId = '033xxxxxxxxx' AND (MetadataPackageId = '033xxxxxxxxx' AND ReleaseState = 'Released')"
    metadata_package_version.get_older_released_version_objs()
    metadata_package_version.package.push_api.get_package_version_objs.assert_called_once_with(
        expected, None
    )


def test_version_min_version_query(metadata_package_version, metadata_package):
    expected = "MetadataPackageId = '033xxxxxxxxx' AND (MetadataPackageId = '033xxxxxxxxx' AND ReleaseState = 'Released')"
    greater_than = MetadataPackageVersion(
        push_api=PUSH_API,
        package=metadata_package,
        name=NAME,
        sf_id=SF_ID,
        state="Beta",
        major="2",
        minor="2",
        patch="2",
        build="1",
    )
    metadata_package_version.get_older_released_version_objs(greater_than)
    metadata_package_version.package.push_api.get_package_version_objs.assert_called_once_with(
        expected, None
    )


def test_version_min_version_query_integration(
    metadata_package_version, metadata_package_versions, metadata_package
):
    expected = "MetadataPackageId = '033xxxxxxxxx' AND (MetadataPackageId = '033xxxxxxxxx' AND ReleaseState = 'Released')"
    min_version = MetadataPackageVersion(
        push_api=PUSH_API,
        package=metadata_package,
        name=NAME,
        sf_id=SF_ID,
        state="Beta",
        major="2",
        minor="1",
        patch="1",
        build="1",
    )
    metadata_package_version.package.push_api.get_package_version_objs.return_value = (
        metadata_package_versions
    )
    assert (
        len(metadata_package_version.get_older_released_version_objs(min_version)) == 3
    )
    metadata_package_version.package.push_api.get_package_version_objs.assert_called_once_with(
        expected, None
    )


def test_version_get_newer(metadata_package_version):
    expected = "MetadataPackageId = '033xxxxxxxxx' AND ReleaseState = 'Released'"  # AND (MajorVersion > 1 OR (MajorVersion = 1 AND MinorVersion > 2) OR (MajorVersion = 1 AND MinorVersion = 2 AND PatchVersion >= 3))"
    metadata_package_version.package.get_package_version_objs = mock.MagicMock()
    metadata_package_version.get_newer_released_version_objs()
    metadata_package_version.package.get_package_version_objs.assert_called_once_with(
        expected
    )


def test_version_get_older(
    metadata_package_version, metadata_package_versions, metadata_package
):
    expected = "MetadataPackageId = '033xxxxxxxxx' AND ReleaseState = 'Released'"
    metadata_package_version.package.get_package_version_objs = mock.MagicMock()
    metadata_package_version.package.get_package_version_objs.return_value = (
        metadata_package_versions
    )
    min_version = MetadataPackageVersion(
        push_api=PUSH_API,
        package=metadata_package,
        name=NAME,
        sf_id=SF_ID,
        state="Beta",
        major="1",
        minor="1",
        patch="1",
        build="1",
    )
    assert (
        len(metadata_package_version.get_older_released_version_objs(min_version)) == 8
    )
    metadata_package_version.package.get_package_version_objs.assert_called_once_with(
        expected
    )


def test_package_push_job_get_push_errors(package_push_job):
    expected = f"PackagePushJobId = '{SF_ID}'"
    package_push_job.get_push_errors()
    package_push_job.push_api.get_push_errors.assert_called_once_with(expected, None)


def test_package_push_job_get_push_error_objects(package_push_job):
    expected = f"PackagePushJobId = '{SF_ID}'"
    package_push_job.get_push_error_objs()
    package_push_job.push_api.get_push_error_objs.assert_called_once_with(
        expected, None
    )


def test_package_push_job_get_push_errors_by_id(package_push_job):
    expected = f"PackagePushJobId = '{SF_ID}'"
    package_push_job.get_push_errors_by_id()
    package_push_job.push_api.get_push_errors_by_id.assert_called_once_with(
        expected, None
    )


def test_package_push_errors(package_push_error):
    assert package_push_error.push_api == "foo"
    assert package_push_error.sf_id == SF_ID
    assert package_push_error.job == "Foo"
    assert package_push_error.severity == "high"

    assert package_push_error.error_type == "bar"
    assert package_push_error.title == "foo_bar"
    assert package_push_error.message == "The foo hit the bar"
    assert package_push_error.details == "foo bar, foo, foo bar"


def test_package_push_request_get_push_jobs(package_push_request):
    expected = f"PackagePushRequestId = '{SF_ID}'"
    package_push_request.get_push_jobs()
    package_push_request.push_api.get_push_jobs.assert_called_once_with(expected, None)


def test_package_push_request_get_push_job_objects(package_push_request):
    expected = f"PackagePushRequestId = '{SF_ID}'"
    package_push_request.get_push_job_objs()
    package_push_request.push_api.get_push_job_objs.assert_called_once_with(
        expected, None
    )


def test_package_push_request_get_push_jobs_by_id(package_push_request):
    expected = f"PackagePushRequestId = '{SF_ID}'"
    package_push_request.get_push_jobs_by_id()
    package_push_request.push_api.get_push_jobs_by_id.assert_called_once_with(
        expected, None
    )


def test_format_where(package_subscriber):
    assert package_subscriber.format_where("foo") == "foo = 'bar'"
    assert (
        package_subscriber.format_where("foo", "foobar") == "foo = 'bar' AND (foobar)"
    )


def test_package_subscriber_get_push_jobs(package_subscriber):
    expected = f"SubscriberOrganizationKey = '{ORG_KEY}'"
    package_subscriber.get_push_jobs()
    package_subscriber.push_api.get_push_jobs.assert_called_once_with(expected, None)


def test_package_subscriber_get_push_job_objects(package_subscriber):
    expected = f"SubscriberOrganizationKey = '{ORG_KEY}'"
    package_subscriber.get_push_job_objs()
    package_subscriber.push_api.get_push_job_objs.assert_called_once_with(
        expected, None
    )


def test_package_subscriber_get_push_jobs_by_id(package_subscriber):
    expected = f"SubscriberOrganizationKey = '{ORG_KEY}'"
    package_subscriber.get_push_jobs_by_id()
    package_subscriber.push_api.get_push_jobs_by_id.assert_called_once_with(
        expected, None
    )
