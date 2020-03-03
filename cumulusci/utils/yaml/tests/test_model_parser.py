from io import StringIO
from cumulusci.utils.yaml.model_parser import CCIDictModel, CCIModel
from pydantic import Field


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
        print(foo)
        assert foo.fields_ == []
        assert foo.fields == []

        foo = Document.parse_from_yaml(StringIO("{bar: 'blah', fields: [1,2]}"))
        assert foo.fields == [1, 2]

        foo.fields = ["a", "b"]
        assert foo.fields == ["a", "b"]


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
