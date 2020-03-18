from unittest.mock import Mock, patch
from pytest import xfail, mark
from io import StringIO

from cumulusci.utils.yaml.cumulusci_yml import (
    parse_from_yaml,
    cci_safe_load,
    _replace_nbsp,
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
        cciyml = cci_safe_load(StringIO(yaml), "foo", on_error=lf)
        assert isinstance(cciyml, dict)  # should parse despite model errors
        lf.assert_called()
        assert "foo" in str(lf.mock_calls[0][1][0])
        assert "xyz" in str(lf.mock_calls[0][1][0])

    @patch("cumulusci.utils.yaml.cumulusci_yml.validate_data")
    def test_unexpected_exceptions(self, validate_data):
        validate_data.side_effect = AssertionError("Boom!")
        yaml = """xyz:
            y: abc"""
        logfunc = Mock()
        cciyml = cci_safe_load(StringIO(yaml), "foo", on_error=logfunc)

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

    def test_simple_load(self, caplog):
        yaml = """xyz:
            y: abc"""
        cciyml = cci_safe_load(StringIO(yaml))
        assert not caplog.text

        assert isinstance(cciyml, dict)  # should parse despite funny character
        assert cciyml["xyz"]["y"] == "abc", cciyml

    def test_convert_nbsp(self, caplog):
        yaml = """xyz:
           \u00A0 y: abc"""
        cciyml = cci_safe_load(StringIO(yaml))
        assert "space character" in caplog.text

        assert isinstance(cciyml, dict)  # should parse despite funny character
        assert cciyml["xyz"]["y"] == "abc", cciyml

    def test_converter(self):
        inp = """xyz:
           \u00A0 y: abc"""
        outp = """xyz:
             y: abc"""

        rc = _replace_nbsp(inp)
        assert rc == outp

    def test_converter_is_selective(self):
        inp = """xyz:
             y: abc\u00A0"""

        rc = _replace_nbsp(inp)
        assert rc == inp
