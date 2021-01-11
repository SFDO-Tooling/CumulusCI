import pytest

from io import StringIO
from pathlib import Path
from unittest.mock import patch

from cumulusci.core.exceptions import CumulusCIException
from cumulusci.utils import temporary_dir
from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load, _replace_nbsp


class TestCumulusciYml:
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

    def test_invalid_cumulusci_yml_file(self):
        with temporary_dir() as temp_dir:
            cumulusci_yml_filepath = Path(temp_dir) / "cumulusci.yml"

            with open(cumulusci_yml_filepath, "w+") as cumulusci_yml:
                invalid_yml = """xyz: abc   \n>>>\nefg: lmn\n"""
                cumulusci_yml.write(invalid_yml)
                cumulusci_yml.seek(0)

                with pytest.raises(CumulusCIException) as error:
                    cci_safe_load(cumulusci_yml)

        assert error.typename == "CumulusCIException"
        assert (
            "cumulusci.yml at line 1, column 1.\nError message: expected chomping or indentation indicators, but found '>'"
            in error.value.args[0]
        )

    def test_invalid_string_io(self):
        invalid_yml_string = """xyz: abc   \n>>>\nefg: lmn\n"""
        with pytest.raises(CumulusCIException) as error:
            cci_safe_load(StringIO(invalid_yml_string))

        assert error.typename == "CumulusCIException"
        assert "Error message: " in error.value.args[0]

    @patch("cumulusci.utils.yaml.cumulusci_yml.yaml.safe_load")
    def test_generic_exception__with_name_attr(self, safe_load):
        with temporary_dir() as temp_dir:
            cumulusci_yml_filepath = Path(temp_dir) / "cumulusci.yml"

            with open(cumulusci_yml_filepath, "w+") as cumulusci_yml:
                invalid_yml = """xyz: abc   \n>>>\nefg: lmn\n"""
                cumulusci_yml.write(invalid_yml)
                cumulusci_yml.seek(0)

                safe_load.side_effect = Exception("generic")
                with pytest.raises(CumulusCIException) as error:
                    cci_safe_load(cumulusci_yml)

        assert error.typename == "CumulusCIException"
        assert "cumulusci.yml.\nError message: generic" in error.value.args[0]

    @patch("cumulusci.utils.yaml.cumulusci_yml.yaml.safe_load")
    def test_generic_exception__without_name_attr(self, safe_load):
        invalid_yaml = """xyz: abc   \n>>>\nefg: lmn\n"""
        safe_load.side_effect = Exception("generic")
        with pytest.raises(CumulusCIException) as error:
            cci_safe_load(StringIO(invalid_yaml))

        assert error.typename == "CumulusCIException"
        assert (
            "An error occurred parsing a yaml file. Error message: generic"
            == error.value.args[0]
        )
