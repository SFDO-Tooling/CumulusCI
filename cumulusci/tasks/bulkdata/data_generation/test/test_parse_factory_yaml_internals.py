import unittest
from cumulusci.tasks.bulkdata.data_generation.parse_factory_yaml import (
    parse_element,
    ParseContext,
    LineTracker,
    DataGenError,
)

linenum = {"__line__": LineTracker("f", 5)}


class TestParseElement(unittest.TestCase):
    def test_parse_element(self):
        result = parse_element(
            {"object": "a", "b": "c", **linenum},
            "object",
            {"b": str},
            {},
            ParseContext(),
        )
        assert result.b == "c"

    def test_missing_element(self):
        # b is missing
        with self.assertRaises(DataGenError):
            parse_element(
                {"object": "a", **linenum}, "object", {"b": str}, {}, ParseContext()
            )

    def test_unknown_element(self):
        # b is missing
        with self.assertRaises(DataGenError):
            parse_element(
                {"object": "a", "q": "z", **linenum}, "object", {}, {}, ParseContext()
            )

    def test_optional_element(self):
        # b is missing
        result = parse_element(
            {"object": "a", "q": "z", **linenum},
            "object",
            {},
            {"q": str},
            ParseContext(),
        )
        assert result.q == "z"

    def test_defaulted_element(self):
        # q should be defaulted
        result = parse_element(
            {"object": "a", **linenum}, "object", {}, {"q": str}, ParseContext()
        )
        assert result.q is None
