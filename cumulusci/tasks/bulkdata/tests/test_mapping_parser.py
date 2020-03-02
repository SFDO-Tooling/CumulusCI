from pathlib import Path

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
