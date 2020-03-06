from pathlib import Path
import logging
from io import StringIO
import pytest

from yaml import safe_load, dump, YAMLError

from cumulusci.tasks.bulkdata.mapping_parser import parse_from_yaml, ValidationError


class TestMappingParser:
    def test_simple_parse(self):
        base_path = Path(__file__).parent / "mapping_v2.yml"
        assert parse_from_yaml(base_path)

    def test_after(self):
        base_path = Path(__file__).parent / "mapping_after.yml"
        result = parse_from_yaml(base_path)

        step = result["Insert Accounts"]
        lookups = step["lookups"]
        assert lookups
        assert "after" in lookups["ParentId"]
        after_list = {l["after"] for l in lookups.values() if "after" in l}
        assert after_list

    def test_deprecation(self, caplog):
        base_path = Path(__file__).parent / "mapping_v2.yml"
        caplog.set_level(logging.WARNING)

        parse_from_yaml(base_path)
        assert "record_type" in caplog.text

        with open(base_path) as f:
            raw_mapping = safe_load(f)
        raw_mapping["Insert Households"]["oid_as_pk"] = True

        parse_from_yaml(StringIO(dump(raw_mapping)))
        assert "oid_as_pk" in caplog.text

    def test_bad_mapping_syntax(self):
        base_path = Path(__file__).parent / "mapping_v2.yml"
        with open(base_path, "r") as f:
            data = f.read().replace(":", ": abcd")
            with pytest.raises(YAMLError):
                parse_from_yaml(StringIO(data))

    def test_bad_mapping_grammer(self):
        base_path = Path(__file__).parent / "mapping_v2.yml"
        with open(base_path, "r") as f:
            data = f.read().replace("record_type", "xyzzy")
            with pytest.raises(ValidationError):
                parse_from_yaml(StringIO(data))

    def test_load_from_bytes_stream(self):
        base_path = Path(__file__).parent / "mapping_v2.yml"
        with open(base_path, "rb") as f:
            assert parse_from_yaml(f)
