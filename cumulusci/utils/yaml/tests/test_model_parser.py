from io import StringIO

import pytest
from cumulusci.utils.yaml.model_parser import (
    CCIDictModel,
    CCIModel,
    ValidationError,
    Field,
)


class TestCCIModel:
    def test_fields_property(self):
        class Foo(CCIModel):
            bar: str = None
            fields_ = Field([], alias="fields")

        class Document(CCIModel):
            __root__: Foo

        # JSON is YAML. Strange but true.
        foo = Document.parse_from_yaml(StringIO("{bar: 'blah'}"))
        assert type(foo) == Foo
        assert foo.fields_ == []
        assert foo.fields == []

        foo = Document.parse_from_yaml(StringIO("{bar: 'blah', fields: [1,2]}"))
        assert foo.fields == [1, 2]

        foo.fields = ["a", "b"]
        assert foo.fields == ["a", "b"]

    def test_error_messages(self):
        class Foo(CCIModel):
            bar: int = None

        class Document(CCIModel):
            __root__: Foo

        s = StringIO("{bar: 'blah'}")
        s.name = "some_filename"
        with pytest.raises(ValidationError) as e:
            Document.parse_from_yaml(s)
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
        print(foo)
        assert foo["fields"] == []

        foo = Document.parse_from_yaml(StringIO("{bar: 'blah', fields: [1,2]}"))
        assert foo["fields"] == [1, 2]

        foo["fields"] = ["a", "b"]
        assert foo["fields"] == ["a", "b"]
