from io import StringIO

import pytest
from pydantic.v1 import ValidationError

from cumulusci.tasks.bulkdata.extract_dataset_utils.extract_yml import (
    ExtractDeclaration,
    ExtractRulesFile,
)


class TestExtractYML:
    def test_simple_parse(self):
        yaml = """
            version: 1
            extract:
                Opportunity:
                    fields:
                        - Name
                        - ContactId
                        - AccountId
                OBJECTS(CUSTOM):
                    fields: FIELDS(CUSTOM)
                OBJECTS(STANDARD):
                    fields: FIELDS(CUSTOM)
        """
        parse_result = ExtractRulesFile.parse_from_yaml(StringIO(yaml))
        assert parse_result.version == 1
        extract = parse_result.extract
        assert tuple(extract.keys()) == (
            "Opportunity",
            "OBJECTS(CUSTOM)",
            "OBJECTS(STANDARD)",
        )
        assert extract["OBJECTS(STANDARD)"].fields == ["FIELDS(CUSTOM)"]
        assert extract["OBJECTS(STANDARD)"].sf_object == "OBJECTS(STANDARD)"
        assert extract["OBJECTS(STANDARD)"].group_type.value == "standard"
        assert extract["Opportunity"].group_type is None

    def test_default_version(self):
        yaml = """
            extract:
                Opportunity:
                    fields:
                        - Name
                        - ContactId
                        - AccountId
        """
        parse_result = ExtractRulesFile.parse_from_yaml(StringIO(yaml))
        assert parse_result.version == 1
        extract = parse_result.extract
        assert tuple(extract.keys()) == ("Opportunity",)

    def test_mini_parser(self):
        assert (
            ExtractDeclaration.parse_field_complex_type("FIELDS(STANDARD)").value
            == "standard"
        )
        assert ExtractDeclaration.parse_field_complex_type("ffff") is None

    def test_weird_syntaxes(self):
        yaml = """
            extract:
                OBJECTS(XYZZY):
                    fields: FIELDS(CUSTOM)
        """
        with pytest.raises(ValidationError, match="xyzzy"):
            ExtractRulesFile.parse_from_yaml(StringIO(yaml))

        yaml = """
            extract:
                OBJECTS(XYZZY):
                    fields:
                        - FIELDS(CUSTOM)
        """
        with pytest.raises(ValidationError, match="xyzzy"):
            ExtractRulesFile.parse_from_yaml(StringIO(yaml))
        yaml = """
            extract:
                OBJECTS(POPULATED):
                    fields: FIELDS(XYZZY)
        """
        with pytest.raises(ValidationError, match="XYZZY"):
            ExtractRulesFile.parse_from_yaml(StringIO(yaml))

        yaml = """
            extract:
                OBJECTS(POPULATED):
                    fields:
                        - FIELDS(XYZZY)
        """
        with pytest.raises(ValidationError, match="XYZZY"):
            ExtractRulesFile.parse_from_yaml(StringIO(yaml))

        yaml = """
            extract:
                OBJECTS(POPULATED):
                    fields:
                        - abcde
                        - FIELDS(XYZZY)
        """
        with pytest.raises(ValidationError, match="XYZZY"):
            ExtractRulesFile.parse_from_yaml(StringIO(yaml))

        yaml = """
            extract:
                abcd.efgh:
                    fields:
                        - Id
        """
        with pytest.raises(ValidationError, match="abcd.efgh"):
            ExtractRulesFile.parse_from_yaml(StringIO(yaml))

        yaml = """
            extract:
                OBJECTS(POPULATED):
                    fields: XYZZY(CUSTOM)
        """
        with pytest.raises(ValidationError, match="XYZZY"):
            ExtractRulesFile.parse_from_yaml(StringIO(yaml))

        yaml = """
            extract:
                OBJECTS(POPULATED):
                    fields:
                        - XYZZY(CUSTOM)
        """
        with pytest.raises(ValidationError, match="XYZZY"):
            ExtractRulesFile.parse_from_yaml(StringIO(yaml))

    def test_parse_real_file(self, cumulusci_test_repo_root):
        parse_result = ExtractRulesFile.parse_from_yaml(
            cumulusci_test_repo_root / "datasets/test.extract.yml"
        )
        assert parse_result.version == 1
        extract = parse_result.extract
        assert tuple(extract.keys()) == (
            "Opportunity",
            "Contact",
            "Account",
            "OBJECTS(CUSTOM)",
        )
