import unittest
from cumulusci.tasks.bulkdata.data_generation.data_generator_runtime_dom import (
    FieldFactory,
    SimpleValue,
    RuntimeContext,
    StructuredValue,
    ObjectTemplate,
    DataGenError,
)
from cumulusci.tasks.bulkdata.data_generation.output_streams import DebugOutputStream

x = RuntimeContext(None, None)
line = {"filename": "abc.yml", "line_num": 42}


class TestDataGeneratorRuntimeDom(unittest.TestCase):
    def test_field_factory_string(self):
        definition = SimpleValue("abc", "abc.yml", 10)
        repr(definition)
        f = FieldFactory("field", definition, "abc.yml", 10)
        repr(f)
        x = f.generate_value(RuntimeContext(None, None))
        assert x == "abc"

    def test_field_factory_int(self):
        definition = SimpleValue(5, "abc.yml", 10)
        repr(definition)
        f = FieldFactory("field", definition, "abc.yml", 10)
        repr(f)
        x = f.generate_value(RuntimeContext(None, None))
        assert x == 5

    def test_field_factory_calculation(self):
        definition = SimpleValue("<<5*3>>", "abc.yml", 10)
        repr(definition)
        f = FieldFactory("field", definition, "abc.yml", 10)
        repr(f)
        x = f.generate_value(RuntimeContext(None, None))
        assert x == 15

    def test_structured_value(self):
        definition = StructuredValue(
            "random_choice",
            [SimpleValue("abc", "", 1), SimpleValue("def", "", 1)],
            "abc.yml",
            10,
        )
        repr(definition)
        f = FieldFactory("field", definition, "abc.yml", 10)
        x = f.generate_value(RuntimeContext(None, None))
        assert x in ["abc", "def"]

    def test_render_empty_object_template(self):
        o = ObjectTemplate("abcd", filename="abc.yml", line_num=10)
        o.generate_rows(DebugOutputStream(), RuntimeContext(None, None))

    def test_fail_render_object_template(self):
        o = ObjectTemplate("abcd", filename="abc.yml", line_num=10)
        with self.assertRaises(DataGenError):
            o.generate_rows(None, RuntimeContext(None, None))

    def test_fail_render_weird_type(self):
        with self.assertRaises(DataGenError):
            o = ObjectTemplate(
                "abcd",
                filename="abc.yml",
                line_num=10,
                fields=[
                    FieldFactory(
                        "x",
                        SimpleValue(b"junk", filename="abc.yml", line_num=42),
                        **line
                    )
                ],
            )
            o.generate_rows(DebugOutputStream(), RuntimeContext(None, None))

    def test_fail_render_weird_template(self):
        with self.assertRaises(DataGenError):
            o = ObjectTemplate(
                "abcd",
                filename="abc.yml",
                line_num=10,
                fields=[
                    FieldFactory(
                        "x",
                        SimpleValue("<<5()>>", filename="abc.yml", line_num=42),
                        **line
                    )
                ],
            )
            o.generate_rows(DebugOutputStream(), RuntimeContext(None, None))

    def test_structured_value_errors(self):
        with self.assertRaises(DataGenError) as e:
            StructuredValue("this.that.foo", [], **line).render(
                RuntimeContext(None, None)
            )
        assert "only one" in str(e.exception)

        with self.assertRaises(DataGenError) as e:
            StructuredValue("bar", [], **line).render(RuntimeContext(None, None))
        assert "Cannot find func" in str(e.exception)
        assert "bar" in str(e.exception)

        with self.assertRaises(DataGenError) as e:
            StructuredValue("xyzzy.abc", [], **line).render(RuntimeContext(None, None))
        assert "Cannot find defini" in str(e.exception)
        assert "xyzzy" in str(e.exception)

        with self.assertRaises(DataGenError) as e:
            StructuredValue("this.abc", [], **line).render(RuntimeContext(None, None))
        assert "Cannot find defini" in str(e.exception)
        assert "abc" in str(e.exception)
