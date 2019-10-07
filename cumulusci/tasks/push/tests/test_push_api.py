from unittest import mock
import pytest

from cumulusci.tasks.push.push_api import BasePushApiObject
from cumulusci.tasks.push.push_api import SalesforcePushApi
from cumulusci.tasks.push.push_api import memoize, batch_list, MetadataPackage


def test_memoize():
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


def test_batch_list():
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


class TestBasePushApiObject:
    @pytest.fixture
    def base_obj(self):
        return BasePushApiObject()

    def test_format_where(self, base_obj):
        field_name = "id_field"
        sf_id = "006000000XXX000"
        where_clause = "id=001000000XXX000"
        base_obj.sf_id = sf_id

        returned = base_obj.format_where(field_name, where_clause)
        assert "{} = '{}' AND ({})".format(field_name, sf_id, where_clause)

        returned = base_obj.format_where(field_name, None)
        assert "{} = '{}'".format(field_name, sf_id) == returned


class TestMetadataPacakage:
    """Provides coverage for MetadataPackage"""

    NAME = "Chewbacca"
    SF_ID = "sf_id"
    PUSH_API = "push_api"
    NAMESPACE = "namespace"

    @pytest.fixture
    def package(self):
        return MetadataPackage(self.PUSH_API, self.NAME, self.SF_ID, self.NAMESPACE)

    def test_init(self):
        package = MetadataPackage(self.PUSH_API, self.NAME)
        assert package.push_api == self.PUSH_API
        assert package.sf_id is None
        assert package.name == self.NAME
        assert package.namespace is None

        package = MetadataPackage(self.PUSH_API, self.NAME, self.SF_ID, self.NAMESPACE)
        assert package.push_api == self.PUSH_API
        assert package.sf_id == self.SF_ID
        assert package.name == self.NAME
        assert package.namespace == self.NAMESPACE


class TestSalesforcePushApi:
    """Provides coverage for SalesforcePushApi"""

    @pytest.fixture
    def sf_push_api(self):
        return SalesforcePushApi(mock.Mock(), mock.Mock())  # sf  # logger

    def test_return_query_records(self, sf_push_api):
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

    def test_format_where(self, sf_push_api):
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

    def test_add_query_limit(self, sf_push_api):
        query = "SELECT Id FROM Account"
        limit = 100
        returned = sf_push_api.add_query_limit(query, limit)
        assert "{} LIMIT {}".format(query, limit) == returned
