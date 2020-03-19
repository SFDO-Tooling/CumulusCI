import os
from io import StringIO
from unittest.mock import MagicMock, Mock, patch

from pytest import mark, raises

from cumulusci.utils.yaml.cumulusci_yml import (
    _replace_nbsp,
    cci_safe_load,
    parse_from_yaml,
)


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

    @mark.skipif(
        not os.environ.get("CCI_EXTENDED_PARSE_TESTS"),
        reason="CCI_EXTENDED_PARSE_TESTS environment variable not set",
    )  # turn this on if you don't mind Internet access in your tests
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

    @mark.skipif(
        not os.environ.get("CCI_LOCAL_DIRECTORY_TESTS"),
        reason="CCI_LOCAL_DIRECTORY_TESTS environment variable not set",
    )  # you can turn this on if you happen to have this local file structure
    def test_from_local(self):
        assert parse_from_yaml("../Abacus/cumulusci.yml")
        assert parse_from_yaml("../NPSP/cumulusci.yml")
        assert parse_from_yaml("../CaseMan/cumulusci.yml")

    def test_steps_flow_and_task_heterogenous(self, caplog):
        yaml = """flows:
                    my_flow:
                        steps:
                            1:
                                flow: a
                            2:
                                task: b
                            """
        cci_data = cci_safe_load(StringIO(yaml))
        assert not caplog.text
        assert cci_data["flows"]["my_flow"]["steps"][1]["flow"] == "a"
        assert cci_data["flows"]["my_flow"]["steps"][2]["task"] == "b"

    def test_steps_as_list(self, caplog):
        yaml = """flows:
                    my_flow:
                        steps:
                            - A
                            - B
                            - C """
        assert not caplog.text
        cci_safe_load(StringIO(yaml))
        assert "my_flow" in caplog.text
        assert "steps" in caplog.text
        assert "dict" in caplog.text

    def test_individual_steps_as_list(self, caplog):
        yaml = """flows:
                    my_flow:
                        steps:
                            1:
                                - task : b
"""
        assert not caplog.text
        cci_safe_load(StringIO(yaml))
        print(caplog.text)
        assert "steps" in caplog.text
        assert "my_flow" in caplog.text
        assert "dict" in caplog.text

    def test_flow_and_task_confusion(self, caplog):
        yaml = """flows:
                    my_flow:
                        steps:
                            1:
                                task: b
                                flow: c
"""
        assert not caplog.text
        cci_safe_load(StringIO(yaml))
        print(caplog.text)
        assert "steps" in caplog.text
        assert "my_flow" in caplog.text

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

        logger = MagicMock()

        rc = _replace_nbsp(inp, "", logger)
        assert rc == outp
        assert logger.mock_calls[0][0] == "warning"
        assert "space character" in logger.mock_calls[0][1][0]

    def test_converter_is_selective(self):
        inp = """xyz:
             y: abc\u00A0"""

        logger = MagicMock()
        rc = _replace_nbsp(inp, "", logger)
        assert rc == inp
        assert not logger.mock_calls

    def test_mutually_exclusive_options(self):
        logger = MagicMock()
        with raises(AssertionError):
            cci_safe_load(StringIO(""), on_error=lambda *args: args, logger=logger)
