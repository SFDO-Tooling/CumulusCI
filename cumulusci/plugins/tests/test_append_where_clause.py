import unittest

from cumulusci.plugins.apply_where_clause import append_where_clause
from cumulusci.tasks.bulkdata.mapping_parser import MappingStep


class TestFilterHubUsers(unittest.TestCase):
    def test_run_soql_filter_not_none(self):
        """This test case is to verify when soql_filter is specified with valid filter in the mapping yml"""

        mapping = MappingStep(
            sf_object="Contact",
            fields={"Id": "Id", "Name": "Name"},
            soql_filter="Name = 'John Doe'",
        )

        transformed_soql = append_where_clause("SELECT Id, Name FROM Contact", mapping)
        assert (
            transformed_soql == "SELECT Id, Name FROM Contact WHERE Name = 'John Doe'"
        )

    def test_run_soql_filter_WHERE_clause_specified(self):
        """This test case is to verify when soql_filter is specified with WHERE keyword in the mapping yml"""

        mapping = MappingStep(
            sf_object="Contact",
            fields={"Id": "Id", "Name": "Name"},
            soql_filter="WHERE Name = 'John Doe'",
        )

        transformed_soql = append_where_clause("SELECT Id, Name FROM Contact", mapping)
        assert (
            transformed_soql == "SELECT Id, Name FROM Contact WHERE Name = 'John Doe'"
        ), "WHERE keyword shouldn't cause any issues"

    def test_run_soql_filter_WHERE_clause_lower_case(self):
        """This test case is to verify when soql_filter is specified with lower case where keyword in the mapping yml"""

        mapping = MappingStep(
            sf_object="Contact",
            fields={"Id": "Id", "Name": "Name"},
            soql_filter="where Name = 'John Doe'",
        )

        transformed_soql = append_where_clause("SELECT Id, Name FROM Contact", mapping)
        assert (
            transformed_soql == "SELECT Id, Name FROM Contact where Name = 'John Doe'"
        ), "lower case where shouldn't cause any issues"

    def test_run_soql_filter_no_WHERE_clause(self):
        """This test case is to verify when soql_filter is blank in mapping yml"""

        mapping = MappingStep(
            sf_object="Contact", fields={"Id": "Id", "Name": "Name"}, soql_filter=""
        )

        transformed_soql = append_where_clause("SELECT Id, Name FROM Contact", mapping)
        assert transformed_soql == "SELECT Id, Name FROM Contact"
