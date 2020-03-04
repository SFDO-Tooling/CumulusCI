from unittest.mock import Mock, patch
from pytest import xfail

from cumulusci.utils.yaml.cumulusci_yml import parse_from_yaml, cci_safe_load


# fill this out.
class TestCumulusciYml:
    def test_cumulusci_yaml(self):
        cciyml = parse_from_yaml("cumulusci.yml")
        assert cciyml.project.package.name == "CumulusCI"
        assert cciyml["project"]["package"]["name"] == "CumulusCI"
        assert (
            cciyml.tasks["robot"].options["suites"]
            == cciyml["tasks"]["robot"]["options"]["suites"]
            == "cumulusci/robotframework/tests"
        )

    def test_cumulusci_cumulusci_yaml(self):
        cciyml = parse_from_yaml("cumulusci/cumulusci.yml")
        assert cciyml.tasks["connected_app"].options["overwrite"] is False

    def test_parse_cumulusci_yaml(self):
        yaml = """xyz:
                    y: abc"""
        lf = Mock()
        cciyml = cci_safe_load(yaml, "foo", on_error="warn", logfunc=lf)
        assert isinstance(cciyml, dict)  # should parse despite model errors
        lf.assert_called()
        assert "foo" in lf.mock_calls[0][1][0]
        assert "xyz" in lf.mock_calls[0][1][0]

    @patch("cumulusci.utils.yaml.cumulusci_yml.validate_data")
    def test_unexpected_exceptions(self, validate_data):
        validate_data.side_effect = AssertionError("Boom!")
        yaml = """xyz:
            y: abc"""
        logfunc = Mock()
        cciyml = cci_safe_load(yaml, "foo", on_error="warn", logfunc=logfunc)

        assert isinstance(cciyml, dict)  # should parse despite model errors
        logfunc.assert_called()
        validate_data.assert_called()

    def test_from_web(self):

        assert parse_from_yaml(
            "https://raw.githubusercontent.com/SalesforceFoundation/NPSP/master/cumulusci.yml"
        )
        assert parse_from_yaml(
            "https://raw.githubusercontent.com/SalesforceFoundation/EDA/master/cumulusci.yml"
        )
        xfail("Requires Internet Access and some of these YAMLs are buggy or obsolete")
        # buggy? obsolete?
        assert parse_from_yaml(
            "https://raw.githubusercontent.com/SFDO-Tooling/CumulusCI-Test/master/cumulusci.yml"
        )
        # buggy? obsolete?
        assert parse_from_yaml(
            "https://raw.githubusercontent.com/SalesforceFoundation/Relationships/master/cumulusci.yml"
        )
        # buggy? obsolete?
        assert parse_from_yaml(
            "https://raw.githubusercontent.com/SalesforceFoundation/Volunteers-for-Salesforce/master/cumulusci.yml"
        )
        # buggy? obsolete?
        assert parse_from_yaml(
            "https://raw.githubusercontent.com/SalesforceFoundation/Recurring_Donations/master/cumulusci.yml"
        )
