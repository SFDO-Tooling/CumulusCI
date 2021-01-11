from cumulusci.core.exceptions import CumulusCIException
import pytest

from io import StringIO
from unittest.mock import Mock, PropertyMock, patch
from yaml.scanner import ScannerError

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

    @patch("cumulusci.utils.yaml.cumulusci_yml.yaml.safe_load")
    def test_scanner_error(self, safe_load):
        problem_mark = Mock(line=12345, column=54321)
        safe_load.side_effect = ScannerError(problem_mark=problem_mark)

        f_config = Mock()
        f_config.read.return_value = "xyz: abc \n >+>:>%*"  # return invalid yaml
        # mock f_config.name
        type(f_config).name = PropertyMock(return_value="cumulusci.yml")

        with pytest.raises(CumulusCIException) as error:
            cci_safe_load(f_config)

        assert error.typename == "CumulusCIException"
        assert (
            "An error occurred parsing cumulusci.yml at line 12345, column 54321.\nError message: None"
            == error.value.args[0]
        )

    @patch("cumulusci.utils.yaml.cumulusci_yml.yaml.safe_load")
    def test_generic_exception(self, safe_load):
        f_config = Mock()
        f_config.read.return_value = "xyz: abc \n >+>:>%*"  # return invalid yaml
        # Mock objects already have a `name` attribute so we need to mock it specially
        type(f_config).name = PropertyMock(return_value="cumulusci.yml")

        safe_load.side_effect = Exception("generic")
        with pytest.raises(CumulusCIException) as error:
            cci_safe_load(f_config)

        assert error.typename == "CumulusCIException"
        assert (
            "An error occurred parsing cumulusci.yml.\nError message: generic"
            == error.value.args[0]
        )
