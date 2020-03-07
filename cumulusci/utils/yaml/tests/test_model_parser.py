from io import StringIO
from unittest.mock import Mock

import pytest
from cumulusci.utils.yaml.model_parser import (
    CCIDictModel,
    CCIModel,
    ValidationError,
)
from pydantic import Field


class Foo(CCIModel):
    bar: str = None
    fields_ = Field([], alias="fields")


class Document(CCIModel):
    __root__: Foo


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
        assert Document.parse_obj({"bar": "blah"})

    def test_validate_data__success(self):
        assert Document.validate_data({"bar": "blah"})

    def test_validate_data__without_error_handler(self):
        assert not Document.validate_data({"foo": "fail"}, context="pytest")

    def test_validate_data__with_error_handler(self):
        lf = Mock()
        assert not Document.validate_data(
            {"foo": "fail"}, context="pytest", on_error=lf
        )
        lf.assert_called()
        assert "pytest" in str(lf.mock_calls[0][1][0])
        assert "foo" in str(lf.mock_calls[0][1][0])

    def test_validate_on_error_param(self):
        with pytest.raises(Exception) as e:
            assert not Document.validate_data({"qqq": "zzz"}, on_error="barn")
        assert e.value.__class__ in [ValueError, TypeError]

    def test_getattr_missing(self):
        with pytest.raises(AttributeError):
            x = Document.parse_obj({})
            assert x
            x.foo

    def test_error_messages(self):
        class FooWithError(CCIModel):
            bar: int = None

        class DocumentWithError(CCIModel):
            __root__: FooWithError

        s = StringIO("{bar: 'blah'}")
        s.name = "some_filename"
        with pytest.raises(ValidationError) as e:
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
        with pytest.raises(ValidationError) as e:
            Document.parse_from_yaml(s)
        assert "some_filename" in str(e.value)

    def test_fields_no_alias(self):
        class Foo(CCIDictModel):
            bar: str = None

        x = Foo.parse_obj({})
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

        x = Foo.parse_obj({})
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

        x = Foo.parse_obj({"bar": "q"})
        assert x.get("bar") == x.bar == x["bar"] == "q"
        assert x.get("xyzzy", 0) == 0
        assert x.get("xyzzy") is None
        assert x.get("fields") == []

    def test_del(self):
        class Foo(CCIDictModel):
            bar: str = None
            fields_ = Field([], alias="fields")

        x = Foo.parse_obj({"bar": "q"})
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
