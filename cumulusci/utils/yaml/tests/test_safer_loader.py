import pytest

from io import StringIO
from pathlib import Path
from unittest.mock import patch

from cumulusci.core.exceptions import YAMLParseException
from cumulusci.utils import temporary_dir
from cumulusci.utils.yaml.safer_loader import load_yaml_data, _replace_nbsp


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
    with pytest.raises(YAMLParseException) as error:
        load_yaml_data(cci_yml_file)

    assert "cumulusci.yml.\nError message: generic" in error.value.args[0]


@patch("cumulusci.utils.yaml.safer_loader.yaml.safe_load")
def test_generic_exception__without_name_attr(safe_load):
    invalid_yaml = """xyz: abc   \n>>>\nefg: lmn\n"""
    safe_load.side_effect = Exception("generic")
    with pytest.raises(
        YAMLParseException,
        match="An error occurred parsing a yaml file.\nError message: generic",
    ):
        load_yaml_data(StringIO(invalid_yaml))
