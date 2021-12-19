import json
import sys

import pytest
import yaml

from cumulusci.utils.yaml import cumulusci_yml


class TestSchema:
    @pytest.mark.skipif(
        sys.version_info < (3, 8), reason="requires python3.8 or higher"
    )
    def test_schema_validates(self, cumulusci_test_repo_root):
        from jsonschema import validate

        schemapath = (
            cumulusci_test_repo_root / "cumulusci/schema/cumulusci.jsonschema.json"
        )
        with open(schemapath) as f:
            schema = json.load(f)
        with open(cumulusci_test_repo_root / "cumulusci.yml") as f:
            data = yaml.safe_load(f)

        assert validate(data, schema=schema) is None

    def test_schema_is_current(self, cumulusci_test_repo_root):
        current_schema = cumulusci_yml.CumulusCIRoot.schema()
        schemapath = (
            cumulusci_test_repo_root / "cumulusci/schema/cumulusci.jsonschema.json"
        )
        with open(schemapath) as f:
            saved_schema = json.load(f)

        assert current_schema == saved_schema, (current_schema, saved_schema)
