from io import StringIO, BytesIO
from pathlib import Path
from cumulusci.util.xml.metadata_tree import METADATA_NAMESPACE, parse


class TestMetadataTree:
    def test_insertions(self):
        data = StringIO(
            f"""<Data xmlns='{METADATA_NAMESPACE}'><Foo>foo1</Foo><Foo>foo2</Foo></Data>"""
        )
        Data = parse(data)

        assert Data.Foo[0].text == "foo1"
        assert Data.Foo[1].text == "foo2"

        foo4 = Data.append("Foo", "foo4")
        assert Data.Foo[2].text == "foo4"
        assert Data.find(tag="Foo", text="foo4") == foo4

        Data.insertBefore(foo4, tag="Foo", text="foo3")
        assert Data.Foo[2].text == "foo3"
        Data.insertAfter(foo4, tag="Foo", text="foo5")
        assert Data.Foo[4].text == "foo5"

    def test_text(self):
        data = StringIO(
            f"""<Data xmlns='{METADATA_NAMESPACE}'>
                <foo>Foo</foo>
                <text>Bar</text>
                <text>
                    <bar>Bar2</bar>
                </text>
            </Data>"""
        )
        Data = parse(data)
        assert isinstance(Data.foo.text, str)
        assert Data.foo.text == "Foo"
        assert isinstance(Data.text.text, str)
        assert Data.text.text.lower() == "bar"
        assert Data.text[1].bar.text.lower() == "bar2"

    def test_append_goes_in_the_middle(self):
        data = StringIO(
            f"""<Data xmlns='{METADATA_NAMESPACE}'>
                <foo>Foo</foo>
                <bar>Bar</bar>
            </Data>"""
        )
        Data = parse(data)
        Data.append(tag="foo", text="Foo2")
        assert Data.foo[1].text == "Foo2"
        Data.append(tag="foo", text="Foo3")
        assert Data.foo[2].text == "Foo3"
        Data.append(tag="bar", text="Bar2")
        assert Data.bar[1].text == "Bar2"

    def test_whitespace(self):
        from cumulusci.tasks.metadata import tests

        path = (
            Path(tests.__file__).parent
            / "package_metadata/namespaced_report_folder/package.xml"
        )
        with open(path) as f:
            raw = f.read()

        # get rid of whitespace to see if we can replace it faithfully
        raw_flattened = raw.replace("    ", "").replace("\n", "")
        Package = parse(BytesIO(raw_flattened.encode("utf-8")))
        x = Package.tostring().strip()
        assert x == raw

    def test_pretty_printing(self):
        Data = parse(StringIO(f"<Data xmlns='{METADATA_NAMESPACE}'/>"))
        Data.append("A", "AA")
        B = Data.append("B")
        B.append("C", "CC")
        Data.append("A", "AB")
        print(Data.tostring())

        assert (
            Data.tostring()
            == """<?xml version="1.0" encoding="UTF-8"?>
<Data xmlns="http://soap.sforce.com/2006/04/metadata">
    <A>AA</A>
    <B>
        <C>CC</C>
    </B>
    <A>AB</A>
</Data>
"""
        )
