import json
import sys

import pytest
import yaml

from cumulusci.utils.yaml import cumulusci_yml


class TestSchema:
    @pytest.mark.skipif(
        sys.version_info < (3, 7), reason="requires python3.7 or higher"
    )
    def test_schema_validates(self, cumulusci_package_path):
        from jsonschema import validate

        schemapath = cumulusci_package_path / "schema/cumulusci.jsonschema.json"
        with open(schemapath) as f:
            schema = json.load(f)
        try:
            with open(cumulusci_package_path / "../cumulusci.yml") as f:
                data = yaml.safe_load(f)
        except IOError:
            pass  # The path is not present when running tests for an installed cumulusci
        else:
            assert validate(data, schema=schema) is None

    def test_schema_is_current(self, cumulusci_package_path):
        current_schema = cumulusci_yml.CumulusCIRoot.schema()
        schemapath = cumulusci_package_path / "schema/cumulusci.jsonschema.json"
        with open(schemapath) as f:
            saved_schema = json.load(f)

        assert current_schema == saved_schema, (current_schema, saved_schema)
