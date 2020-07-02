from unittest import mock
import pytest

from cumulusci.tasks.push.push_api import BasePushApiObject
from cumulusci.tasks.push.push_api import SalesforcePushApi
from cumulusci.tasks.push.push_api import (
    memoize,
    batch_list,
    MetadataPackage,
    MetadataPackageVersion,
    PackageSubscriber,
    PackagePushError,
    PackagePushJob,
    PackagePushRequest,
)


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


class TestMetadataPacakageVersion:
    """Provides coverage for MetadataPackageVersion"""

    NAME = "foo"
    SF_ID = "006000000XXX000"
    PUSH_API = "push_api"
    PACKAGE = "foo"
    STATE = "Released"
    MAJOR = "1"
    MINOR = "2"
    PATCH = "3"
    BUILD = "5"

    @pytest.fixture
    def package(self):
        return MetadataPackageVersion(
            self.PUSH_API,
            self.PACKAGE,
            self.NAME,
            self.STATE,
            self.MAJOR,
            self.MINOR,
            self.PATCH,
            self.BUILD,
            self.SF_ID,
        )

    def test_init(self):
        package = MetadataPackageVersion(
            self.PUSH_API,
            self.PACKAGE,
            self.NAME,
            self.STATE,
            self.MAJOR,
            self.MINOR,
            self.PATCH,
            self.BUILD,
        )
        assert package.push_api == self.PUSH_API
        assert package.sf_id is None
        assert package.name == self.NAME

        package = MetadataPackageVersion(
            self.PUSH_API,
            self.PACKAGE,
            self.NAME,
            self.STATE,
            self.MAJOR,
            self.MINOR,
            self.PATCH,
            self.BUILD,
            self.SF_ID,
        )
        assert package.push_api == self.PUSH_API
        assert package.package == self.PACKAGE
        assert package.name == self.NAME

        assert package.state == self.STATE
        assert package.major == self.MAJOR
        assert package.minor == self.MINOR

        assert package.patch == self.PATCH
        assert package.build == self.BUILD
        assert package.sf_id == self.SF_ID

        assert package.version_number == "1.2.3"

        package = MetadataPackageVersion(
            self.PUSH_API,
            self.PACKAGE,
            self.NAME,
            "Beta",
            self.MAJOR,
            self.MINOR,
            self.PATCH,
            self.BUILD,
            self.SF_ID,
        )

        assert package.version_number == "1.2.3 (Beta 5)"


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


class TestPackageSubscriber:
    """Provides coverage for PackageSubscriber"""

    NAME = "foo"
    PUSH_API = "push_api"
    SF_ID = "006000000XXX000"
    VERSION = "1.2.3"
    STATUS = "Complete"
    ORG_NAME = "foo"
    ORG_KEY = "bar"
    ORG_STATUS = "Complete"
    ORG_TYPE = "Sandbox"

    @pytest.fixture
    def package(self):
        return PackageSubscriber(
            self.PUSH_API,
            self.VERSION,
            self.STATUS,
            self.ORG_NAME,
            self.ORG_KEY,
            self.ORG_STATUS,
            self.ORG_TYPE,
            self.SF_ID,
        )

    def test_init(self):
        package = PackageSubscriber(
            self.PUSH_API,
            self.VERSION,
            self.STATUS,
            self.ORG_NAME,
            self.ORG_KEY,
            self.ORG_STATUS,
            self.ORG_TYPE,
            self.SF_ID,
        )

        assert package.push_api == self.PUSH_API
        assert package.sf_id == self.SF_ID
        assert package.org_name == self.ORG_NAME
        assert package.version == self.VERSION

        assert package.org_key == self.ORG_KEY
        assert package.org_status == self.ORG_STATUS
        assert package.org_type == self.ORG_TYPE

        assert package.format_where("foo") == "foo = 'bar'"
        assert package.format_where("foo", "foobar") == "foo = 'bar' AND (foobar)"


class TestPackagePushJob:
    """Provides coverage for PackagePushError"""

    PUSH_API = "push_api"
    SF_ID = "006000000XXX000"
    JOB = "foo"
    SEVERITY = "Low"
    ERROR_TYPE = "Exception Error"
    TITLE = "BAR"
    MESSAGE = "Message Here"
    DETAILS = "Details Here"

    @pytest.fixture
    def package(self):
        return PackagePushError(
            self.PUSH_API,
            self.JOB,
            self.SEVERITY,
            self.ERROR_TYPE,
            self.TITLE,
            self.MESSAGE,
            self.DETAILS,
            self.SF_ID,
        )

    def test_init(self):
        package = PackagePushError(
            self.PUSH_API,
            self.JOB,
            self.SEVERITY,
            self.ERROR_TYPE,
            self.TITLE,
            self.MESSAGE,
            self.DETAILS,
            self.SF_ID,
        )

        assert package.push_api == self.PUSH_API
        assert package.sf_id == self.SF_ID
        assert package.job == self.JOB
        assert package.severity == self.SEVERITY

        assert package.error_type == self.ERROR_TYPE
        assert package.title == self.TITLE
        assert package.message == self.MESSAGE
        assert package.details == self.DETAILS


class TestPackagePushRequest:
    """Provides coverage for PackagePushRequest"""

    PUSH_API = "push_api"
    VERSION = "1.2.3"
    START_TIME = "12:03"
    STATUS = "Complete"
    SF_ID = "006000000XXX000"

    @pytest.fixture
    def package(self):
        return PackagePushRequest(
            self.PUSH_API, self.VERSION, self.START_TIME, self.STATUS, self.SF_ID
        )

    def test_init(self):
        package = PackagePushRequest(
            self.PUSH_API, self.VERSION, self.START_TIME, self.STATUS
        )

        assert package.push_api == self.PUSH_API
        assert package.sf_id is None
        assert package.version == self.VERSION

        assert package.start_time == self.START_TIME
        assert package.status == self.STATUS


class TestPackagePushError:
    """Provides coverage for PackagePushJob"""

    PUSH_API = "push_api"
    REQUEST = "foo"
    ORG = "Low"
    STATUS = "Complete"
    SF_ID = "006000000XXX000"

    @pytest.fixture
    def package(self):
        return PackagePushJob(
            self.PUSH_API, self.REQUEST, self.ORG, self.STATUS, self.SF_ID
        )

    def test_init(self):
        package = PackagePushJob(self.PUSH_API, self.REQUEST, self.ORG, self.STATUS)

        assert package.push_api == self.PUSH_API
        assert package.sf_id is None
        assert package.request == self.REQUEST

        assert package.org == self.ORG
        assert package.status == self.STATUS

