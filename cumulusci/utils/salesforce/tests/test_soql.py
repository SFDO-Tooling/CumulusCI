import pytest
import vcr

from cumulusci.utils.salesforce.soql import format_subscriber_package_version_where_clause


class TestSoql:
    spv_id = "04t000000000000"

    @pytest.mark.vcr()
    def test_format_subscriber_package_version_where_clause_simple(self):
        where_clause = format_subscriber_package_version_where_clause(self.spv_id)
        assert f"Id='{self.spv_id}'" in where_clause
        assert f" AND InstallationKey =" not in where_clause

    @pytest.mark.vcr()
    def format_subscriber_package_version_where_clause_install_key(self):
        install_key = "hunter2"
        where_clause = format_subscriber_package_version_where_clause(self.spv_id, install_key)
        assert f"Id='{self.spv_id}'" in where_clause
        assert f" AND InstallationKey ='{install_key}'" in where_clause
