import os
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from pytest import mark, raises
import pytest

from cumulusci.core.exceptions import YAMLParseException
from cumulusci.utils import temporary_dir
from cumulusci.utils.yaml.safer_loader import load_yaml_data, _replace_nbsp
from cumulusci.utils.yaml.cumulusci_yml import (
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


@pytest.fixture
def cci_yml_file():
    "Yields a cumulusci file obj for writing to. Cleans up when finished."
    with temporary_dir() as temp_dir:
        cumulusci_yml_filepath = Path(temp_dir) / "cumulusci.yml"

        with open(cumulusci_yml_filepath, "w+") as cumulusci_yml:
            yield cumulusci_yml


def test_simple_load(caplog):
    yaml = """xyz:
        y: abc"""
    cciyml = load_yaml_data(StringIO(yaml))
    assert not caplog.text

    assert isinstance(cciyml, dict)  # should parse despite funny character
    assert cciyml["xyz"]["y"] == "abc", cciyml


def test_convert_nbsp(caplog):
    yaml = """xyz:
        \u00A0 y: abc"""
    cciyml = load_yaml_data(StringIO(yaml))
    assert "space character" in caplog.text

    assert isinstance(cciyml, dict)  # should parse despite funny character
    assert cciyml["xyz"]["y"] == "abc", cciyml


def test_converter():
    inp = """xyz:
        \u00A0 y: abc"""
    outp = """xyz:
          y: abc"""

    rc = _replace_nbsp(inp, "filename")
    assert rc == outp


def test_converter_is_selective():
    inp = """xyz:
            y: abc\u00A0"""

    rc = _replace_nbsp(inp, "filename")
    assert rc == inp


def test_invalid_cumulusci_yml_file(cci_yml_file):
    invalid_yml = """xyz: abc   \n>>>\nefg: lmn\n"""
    cci_yml_file.write(invalid_yml)
    cci_yml_file.seek(0)

    with pytest.raises(
        YAMLParseException,
        match="An error occurred parsing yaml file at line 2, column 1.*",
    ):
        load_yaml_data(cci_yml_file)


def test_invalid_string_io():
    invalid_yml_string = """xyz: abc   \n>>>\nefg: lmn\n"""
    with pytest.raises(YAMLParseException) as error:
        load_yaml_data(StringIO(invalid_yml_string))

    assert "Error message: " in error.value.args[0]


@patch("cumulusci.utils.yaml.safer_loader.yaml.safe_load")
def test_generic_exception__with_name_attr(safe_load, cci_yml_file):
    invalid_yml = """xyz: abc   \n>>>\nefg: lmn\n"""
    cci_yml_file.write(invalid_yml)
    cci_yml_file.seek(0)

    safe_load.side_effect = Exception("generic")
    with pytest.raises(YAMLParseException):
        load_yaml_data(cci_yml_file)

    def test_mutually_exclusive_options(self):
        logger = MagicMock()
        with raises(AssertionError):
            cci_safe_load(StringIO(""), on_error=lambda *args: args, logger=logger)


@patch("cumulusci.utils.yaml.safer_loader.yaml.safe_load")
def test_generic_exception__without_name_attr(safe_load):
    invalid_yaml = """xyz: abc   \n>>>\nefg: lmn\n"""
    safe_load.side_effect = Exception("generic")
    with pytest.raises(
        YAMLParseException,
        match="An error occurred parsing a yaml file.\nError message: generic",
    ):
        load_yaml_data(StringIO(invalid_yaml))
