import json

import yaml
from jsonschema import validate

from cumulusci.utils.yaml import cumulusci_yml


class TestSchema:
    def test_schema_validates(self, cumulusci_test_repo_root):
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

        assert current_schema == saved_schema, (
            "The models used to validate cumulusci.yml do not match cumulusci.jsonschema.json. "
            "Use `make schema` to update the jsonschema file."
        )
