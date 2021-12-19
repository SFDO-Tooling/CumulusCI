import json

import yaml
from jsonschema import validate

from cumulusci.utils.yaml import cumulusci_yml


class TestSchema:
    def test_schema_validates(self, cumulusci_package_path):
        schemapath = cumulusci_package_path / "schema/cumulusci.jsonschema.json"
        with open(schemapath) as f:
            schema = json.load(f)
        try:
            with open(cumulusci_package_path / "../cumulusci.yml") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:  # not present in package artifact
            return
        assert validate(data, schema=schema) is None

    def test_schema_is_current(self, cumulusci_package_path):
        current_schema = cumulusci_yml.CumulusCIRoot.schema()
        schemapath = cumulusci_package_path / "schema/cumulusci.jsonschema.json"
        with open(schemapath) as f:
            saved_schema = json.load(f)

        assert current_schema == saved_schema, (current_schema, saved_schema)
