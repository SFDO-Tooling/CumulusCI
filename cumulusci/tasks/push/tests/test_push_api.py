from unittest import mock

import pytest
from cumulusci.tasks.push.push_api import (
    BasePushApiObject,
    MetadataPackage,
    MetadataPackageVersion,
    SalesforcePushApi,
    batch_list,
    memoize,
)

NAME = "Chewbacca"
SF_ID = "033xxxxxxxxx"
PUSH_API = "push_api"
NAMESPACE = "namespace"


@pytest.fixture
def sf_push_api():
    return SalesforcePushApi(mock.Mock(), mock.Mock())  # sf  # logger


@pytest.fixture
def metadata_package():
    return MetadataPackage(
        push_api=mock.MagicMock(), name=NAME, sf_id=SF_ID, namespace=NAMESPACE
    )


@pytest.fixture
def metadata_package_version(metadata_package):
    return MetadataPackageVersion(
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


def test_base_push_format_where():
    base_obj = BasePushApiObject()
    field_name = "id_field"
    sf_id = "006000000XXX000"
    where_clause = "id=001000000XXX000"
    base_obj.sf_id = sf_id

    returned = base_obj.format_where(field_name, where_clause)
    assert "{} = '{}' AND ({})".format(field_name, sf_id, where_clause)

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
    metadata_package.push_api.get_package_versions.assert_called_once()
    metadata_package.push_api.get_package_versions.assert_called_with(expected, None)


def test_metadata_package_get_version_objs(metadata_package):
    expected = f"MetadataPackageId = '{SF_ID}'"
    metadata_package.get_package_version_objs()
    metadata_package.push_api.get_package_version_objs.assert_called_once()
    metadata_package.push_api.get_package_version_objs.assert_called_with(
        expected, None
    )


def test_metadata_package_get_versions_by_id(metadata_package):
    expected = f"MetadataPackageId = '{SF_ID}'"
    metadata_package.get_package_versions_by_id()
    metadata_package.push_api.get_package_versions_by_id.assert_called_once()
    metadata_package.push_api.get_package_versions_by_id.assert_called_with(
        expected, None
    )


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
    assert "" == returned

    default_where = "Id='001000000XXX000'"
    sf_push_api.default_where = {"Account": default_where}
    returned = sf_push_api.format_where_clause(None, "Object__c")
    assert "" == returned

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


def test_push_memoize():
    def test_func(number):
        return number

    memoized_func = memoize(test_func)
    memoized_func(10)
    memoized_func(20)

    expected_cache = {"(10,){}": 10, "(20,){}": 20}
    assert expected_cache == memoized_func.cache

    memoized_func(10)
    memoized_func(20)
    # No new items introduced, cache should be same
    assert expected_cache == memoized_func.cache


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
        major="1",
        minor="1",
        patch="1",
        build="1",
    )
    assert package.push_api == PUSH_API
    assert package.package == metadata_package
    assert package.name == NAME
    assert package.sf_id == SF_ID
    assert package.state == "Beta"
    assert package.major == "1"
    assert package.minor == "1"
    assert package.patch == "1"
    assert package.build == "1"


def test_version_number(metadata_package_version):
    actual = metadata_package_version.version_number
    expected = "1.1.1 (Beta 1)"
    assert actual == expected


def test_version_get_newer_query(metadata_package_version):
    patch_actual = metadata_package_version._newer_query()
    expected_patch_where = (
        "OR (MajorVersion = 1 AND MinorVersion = 1 AND PatchVersion > 1)"
    )
    assert expected_patch_where in patch_actual


def test_version_get_older_query(metadata_package_version):
    # metadata_package_version.package.get_package_version_objs = mock.Mock()
    patch_actual = metadata_package_version._older_query()
    expected_patch_where = (
        "OR (MajorVersion = 1 AND MinorVersion = 1 AND PatchVersion < 1)"
    )
    assert expected_patch_where in patch_actual


def test_version_less_than_query(metadata_package_version, metadata_package):
    less_than = MetadataPackageVersion(
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
    actual = metadata_package_version._newer_query(less_than)
    expected_where = "AND (MajorVersion < 2 OR (MajorVersion = 2 AND MinorVersion < 2)"
    expected_patch_where = (
        " OR (MajorVersion = 2 AND MinorVersion = 2 AND PatchVersion < 2)"
    )
    print(actual)
    assert expected_where in actual
    assert expected_patch_where in actual


def test_version_greater_than_query(metadata_package_version, metadata_package):
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
    actual = metadata_package_version._older_query(greater_than)
    print(actual)
    expected_where = "AND (MajorVersion > 2 OR (MajorVersion = 2 AND MinorVersion > 2)"
    expected_patch_where = (
        " OR (MajorVersion = 2 AND MinorVersion = 2 AND PatchVersion > 2)"
    )
    assert expected_where in actual
    assert expected_patch_where in actual


def test_version_base_query(metadata_package_version):
    actual = metadata_package_version._base_query()
    expected = f"MetadataPackageId = '{SF_ID}' AND ReleaseState = 'Released' AND "
    assert expected == actual


def test_version_get_newer(metadata_package_version):
    metadata_package_version.package.get_package_version_objs = mock.MagicMock()
    metadata_package_version.get_newer_released_version_objs()
    expected = f"""
  MetadataPackageId = '{SF_ID}' AND ReleaseState = 'Released' AND (MajorVersion > 1 OR (MajorVersion = 1 AND MinorVersion > 1) OR (MajorVersion = 1 AND MinorVersion = 1 AND PatchVersion > 1))
  """
    metadata_package_version.package.get_package_version_objs.assert_called_with(
        expected.strip()
    )


def test_version_get_older(metadata_package_version):
    metadata_package_version.package.get_package_version_objs = mock.MagicMock()
    metadata_package_version.get_older_released_version_objs()
    expected = f"""
  MetadataPackageId = '{SF_ID}' AND ReleaseState = 'Released' AND (MajorVersion < 1 OR (MajorVersion = 1 AND MinorVersion < 1) OR (MajorVersion = 1 AND MinorVersion = 1 AND PatchVersion < 1))
  """
    metadata_package_version.package.get_package_version_objs.assert_called_with(
        expected.strip()
    )
