import pytest

from io import StringIO
from pathlib import Path
from unittest.mock import patch

from cumulusci.core.exceptions import CumulusCIException
from cumulusci.utils import temporary_dir
from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load, _replace_nbsp


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
    cciyml = cci_safe_load(StringIO(yaml))
    assert not caplog.text

    assert isinstance(cciyml, dict)  # should parse despite funny character
    assert cciyml["xyz"]["y"] == "abc", cciyml


def test_convert_nbsp(caplog):
    yaml = """xyz:
        \u00A0 y: abc"""
    cciyml = cci_safe_load(StringIO(yaml))
    assert "space character" in caplog.text

    assert isinstance(cciyml, dict)  # should parse despite funny character
    assert cciyml["xyz"]["y"] == "abc", cciyml


def test_converter():
    inp = """xyz:
        \u00A0 y: abc"""
    outp = """xyz:
            y: abc"""

    rc = _replace_nbsp(inp)
    assert rc == outp


def test_converter_is_selective():
    inp = """xyz:
            y: abc\u00A0"""

    rc = _replace_nbsp(inp)
    assert rc == inp


def test_invalid_cumulusci_yml_file(cci_yml_file):
    invalid_yml = """xyz: abc   \n>>>\nefg: lmn\n"""
    cci_yml_file.write(invalid_yml)
    cci_yml_file.seek(0)

    with pytest.raises(
        CumulusCIException,
        match="cumulusci.yml at line 1, column 1.\nError message: expected chomping or indentation indicators, but found '>'",
    ):
        cci_safe_load(cci_yml_file)


def test_invalid_string_io():
    invalid_yml_string = """xyz: abc   \n>>>\nefg: lmn\n"""
    with pytest.raises(CumulusCIException) as error:
        cci_safe_load(StringIO(invalid_yml_string))

    assert "Error message: " in error.value.args[0]


@patch("cumulusci.utils.yaml.cumulusci_yml.yaml.safe_load")
def test_generic_exception__with_name_attr(safe_load, cci_yml_file):
    invalid_yml = """xyz: abc   \n>>>\nefg: lmn\n"""
    cci_yml_file.write(invalid_yml)
    cci_yml_file.seek(0)

    safe_load.side_effect = Exception("generic")
    with pytest.raises(CumulusCIException) as error:
        cci_safe_load(cci_yml_file)

    assert "cumulusci.yml.\nError message: generic" in error.value.args[0]


@patch("cumulusci.utils.yaml.cumulusci_yml.yaml.safe_load")
def test_generic_exception__without_name_attr(safe_load):
    invalid_yaml = """xyz: abc   \n>>>\nefg: lmn\n"""
    safe_load.side_effect = Exception("generic")
    with pytest.raises(
        CumulusCIException,
        match="An error occurred parsing a yaml file. Error message: generic",
    ):
        cci_safe_load(StringIO(invalid_yaml))
