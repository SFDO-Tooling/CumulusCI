from io import StringIO

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
