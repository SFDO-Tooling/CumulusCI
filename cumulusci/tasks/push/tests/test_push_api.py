from unittest import mock

import pytest
from cumulusci.tasks.push.push_api import (
    BasePushApiObject,
    MetadataPackage,
    SalesforcePushApi,
    batch_list,
    memoize,
)


@pytest.fixture
def sf_push_api():
    return SalesforcePushApi(mock.Mock(), mock.Mock())  # sf  # logger


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
    NAME = "Chewbacca"
    SF_ID = "sf_id"
    PUSH_API = "push_api"
    NAMESPACE = "namespace"

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
