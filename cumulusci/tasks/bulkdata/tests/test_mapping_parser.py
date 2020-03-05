from pathlib import Path
import logging
from yaml import safe_load, dump
from io import StringIO
from cumulusci.tasks.bulkdata.mapping_parser import parse_mapping_from_yaml


class TestMappingParser:
    def test_simple_parse(self):
        base_path = Path(__file__).parent / "mapping_v2.yml"
        assert parse_mapping_from_yaml(base_path)

    def test_after(self):
        base_path = Path(__file__).parent / "mapping_after.yml"
        result = parse_mapping_from_yaml(base_path)

        step = result["Insert Accounts"]
        lookups = step["lookups"]
        assert lookups
        print(lookups)
        assert "after" in lookups["ParentId"]
        after_list = {l["after"] for l in lookups.values() if "after" in l}
        assert after_list

    def test_deprecation(self, caplog):
        base_path = Path(__file__).parent / "mapping_v2.yml"
        caplog.set_level(logging.WARNING)

        parse_mapping_from_yaml(base_path)
        assert "record_type" in caplog.text

        with open(base_path) as f:
            raw_mapping = safe_load(f)
        print(raw_mapping)
        raw_mapping["Insert Households"]["oid_as_pk"] = True

        parse_mapping_from_yaml(StringIO(dump(raw_mapping)))
        assert "oid_as_pk" in caplog.text
