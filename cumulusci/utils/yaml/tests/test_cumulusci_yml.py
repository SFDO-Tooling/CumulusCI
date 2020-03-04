from unittest.mock import Mock, patch
from pytest import xfail, mark

from cumulusci.utils.yaml.cumulusci_yml import (
    parse_from_yaml,
    cci_safe_load,
)


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

    @mark.skip  # slow and Internet dependent
    def test_from_web(self):
        urls = """
            https://raw.githubusercontent.com/SalesforceFoundation/NPSP/master/cumulusci.yml
            https://raw.githubusercontent.com/SalesforceFoundation/EDA/master/cumulusci.yml
            https://raw.githubusercontent.com/SFDO-Tooling/CumulusCI-Test/master/cumulusci.yml
            https://raw.githubusercontent.com/SalesforceFoundation/Relationships/master/cumulusci.yml
            https://raw.githubusercontent.com/SalesforceFoundation/Volunteers-for-Salesforce/master/cumulusci.yml
            https://raw.githubusercontent.com/SalesforceFoundation/Recurring_Donations/master/cumulusci.yml
        """

        def test(url):
            try:
                parse_from_yaml(url)
                return True
            except Exception as e:
                print(url)
                print(str(e))
                return False

        urls = (url.strip() for url in urls.split("\n"))
        results = [(url, test(url)) for url in urls if url]
        assert [result for (url, result) in results] == [1, 1, 0, 0, 0, 0]

    @mark.skip  # depends on specific local file structure
    def test_from_local(self):
        xfail("Depends on specific directory structure. To be removed.")
        assert parse_from_yaml("../Abacus/cumulusci.yml")
        assert parse_from_yaml("../NPSP/cumulusci.yml")
        assert parse_from_yaml("../CaseMan/cumulusci.yml")
