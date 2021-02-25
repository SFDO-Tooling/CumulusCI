from io import StringIO
from unittest.mock import Mock

import pytest
from cumulusci.utils.yaml.model_parser import (
    CCIDictModel,
    CCIModel,
)
from cumulusci.utils.yaml.line_number_annotator import (
    LineNumberAnnotator,
    ConfigValidationError,
)
from pydantic import Field


class Foo(CCIModel):
    bar: str = None
    fields_ = Field([], alias="fields")


class Document(CCIModel):
    __root__: Foo


class FakeLineNoHandler:
    def exception_with_line_numbers(self, e, path):
        return ConfigValidationError(e.errors())


fake_lna = FakeLineNoHandler()


class TestCCIModel:
    def test_fields_property(self):
        # JSON is YAML. Strange but true.
        foo = Document.parse_from_yaml(StringIO("{bar: 'blah'}"))
        assert type(foo) == Foo
        assert foo.fields_ == []
        assert foo.fields == []

        foo = Document.parse_from_yaml(StringIO("{bar: 'blah', fields: [1,2]}"))
        assert foo.fields == [1, 2]

        foo.fields = ["a", "b"]
        assert foo.fields == ["a", "b"]

    def test_parse_from_dict(self):
        assert Document.parse_obj({"bar": "blah"}, fake_lna)

    def test_validate_data__success(self):
        assert Document.validate_data({"bar": "blah"}, fake_lna)

    def test_validate_data__without_error_handler(self):
        assert not Document.validate_data({"foo": "fail"}, fake_lna, context="pytest")

    def test_validate_data__with_error_handler(self):
        lf = Mock()
        lna = LineNumberAnnotator()
        lna.annotated_data = {}  # not realistic, but convenient
        lna.line_numbers = {}  # not realistic, but convenient
        assert not Document.validate_data(
            {"foo": "fail"}, lna, context="pytest", on_error=lf
        )
        lf.assert_called()
        assert "pytest" in str(lf.mock_calls[0][1][0])
        assert "foo" in str(lf.mock_calls[0][1][0])

    def test_validate_on_error_param(self):
        with pytest.raises(Exception) as e:
            assert not Document.validate_data({"qqq": "zzz"}, fake_lna, on_error="barn")
        assert e.value.__class__ in [ValueError, TypeError]

    def test_getattr_missing(self):
        with pytest.raises(AttributeError):
            x = Document.parse_obj({}, fake_lna)
            assert x
            x.foo

    def test_error_messages(self):
        class FooWithError(CCIModel):
            bar: int = None

        class DocumentWithError(CCIModel):
            __root__: FooWithError

        s = StringIO("{bar: 'blah'}")
        s.name = "some_filename"
        with pytest.raises(ConfigValidationError) as e:
            DocumentWithError.parse_from_yaml(s)
        assert "some_filename" in str(e.value)

    def test_error_messages__nested(self):
        class Foo(CCIModel):
            bar: int  # required

        class Bar(CCIModel):
            foo: Foo = None

        class Baz(CCIModel):
            bar: Bar = None

        class Document(CCIModel):
            __root__: Baz

        s = StringIO("{bar: {foo: {}}}")
        s.name = "some_filename"
        with pytest.raises(ConfigValidationError) as e:
            Document.parse_from_yaml(s)
        assert "some_filename" in str(e.value)

    def test_fields_no_alias(self):
        class Foo(CCIDictModel):
            bar: str = None

        x = Foo.parse_obj({}, fake_lna)
        assert x
        with pytest.raises(AttributeError):
            x.fields

    def test_copy(self):
        class Foo(CCIDictModel):
            bar: str = None

        x = Foo(bar="abc")
        y = x.copy()
        y.bar = "def"
        assert x.bar == "abc"
        assert y.bar == "def"


class TestCCIDictModel:
    def test_fields_items(self):
        class Foo(CCIDictModel):
            bar: str = None
            fields_ = Field([], alias="fields")

        class Document(CCIDictModel):
            __root__: Foo

        # JSON is YAML. Strange but true.
        foo = Document.parse_from_yaml(StringIO("{bar: 'blah'}"))
        assert type(foo) == Foo
        assert foo["fields"] == []

        foo = Document.parse_from_yaml(StringIO("{bar: 'blah', fields: [1,2]}"))
        assert foo["fields"] == [1, 2]

        foo["fields"] = ["a", "b"]
        assert foo["fields"] == ["a", "b"]

    def test_getitem_missing(self):
        class Foo(CCIDictModel):
            bar: str = None
            fields_ = Field([], alias="fields")

        x = Foo.parse_obj({}, fake_lna)
        assert x
        with pytest.raises(IndexError):
            x["foo"]

        assert "bar" in x
        assert "fields" in x
        assert x["fields"] == []

    def test_get(self):
        class Foo(CCIDictModel):
            bar: str = None
            fields_ = Field([], alias="fields")

        x = Foo.parse_obj({"bar": "q"}, fake_lna)
        assert x.get("bar") == x.bar == x["bar"] == "q"
        assert x.get("xyzzy", 0) == 0
        assert x.get("xyzzy") is None
        assert x.get("fields") == []

    def test_del(self):
        class Foo(CCIDictModel):
            bar: str = None
            fields_ = Field([], alias="fields")

        x = Foo.parse_obj({"bar": "q"}, fake_lna)
        assert x["bar"] == x.bar == "q"
        assert "bar" in x
        del x["bar"]
        assert "bar" not in x
        assert x.get("bar") is None

        assert x["fields"] == x.fields == []
        assert "fields" in x
        del x["fields"]
        assert "fields" not in x
        assert x.get("fields") is None


class TestEnhanceLocations:
    def test_exception_with_line_numbers__1(self):
        # JSON is YAML. Strange but true.
        with pytest.raises(ConfigValidationError) as err:
            Document.parse_from_yaml(StringIO("{zzzz: 'blah'}"))

        assert "<stream>:1" in str(err.value), str(err.value)
        assert "zzzz" in str(err.value), str(err.value)

    def test_exception_with_line_numbers__2(self):
        # JSON is YAML. Strange but true.
        yaml = """
            bar: baz
            xyzzy: blah
            """
        with pytest.raises(ConfigValidationError) as err:
            Document.parse_from_yaml(StringIO(yaml))

        assert "<stream>:3" in str(err.value), str(err.value)
        assert "xyzzy" in str(err.value), str(err.value)
