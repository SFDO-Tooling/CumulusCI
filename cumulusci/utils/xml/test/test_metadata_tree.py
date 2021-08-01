from io import BytesIO
from pathlib import Path

import pytest

from cumulusci.utils.xml.metadata_tree import METADATA_NAMESPACE, fromstring, parse

standard_xml = f"""<Data xmlns='{METADATA_NAMESPACE}'>
                <foo>Foo</foo>
                <foo>Foo2</foo>
                <bar><name>Bar1</name><label>Label1</label></bar>
                <bar><name>Bar2</name><label>Label2</label></bar>
                <text>Baz</text>
            </Data>"""


class TestMetadataTree:
    def test_insertions(self):
        Data = fromstring(
            f"""<Data xmlns='{METADATA_NAMESPACE}'><Foo>foo1</Foo><Foo>foo2</Foo></Data>"""
        )

        assert Data.Foo[0].text == "foo1"
        assert Data.Foo[1].text == "foo2"

        foo4 = Data.append("Foo", "foo4")
        assert Data.Foo[2].text == "foo4"
        assert Data.find(tag="Foo", text="foo4") == foo4

        Data.insert_before(foo4, tag="Foo", text="foo3")
        assert Data.Foo[2].text == "foo3"
        Data.insert_after(foo4, tag="Foo", text="foo5")
        assert Data.Foo[4].text == "foo5"

    def test_text(self):
        Data = fromstring(
            f"""<Data xmlns='{METADATA_NAMESPACE}'>
                <foo>Foo</foo>
                <text>Bar</text>
                <text>
                    <bar>Bar2</bar>
                </text>
            </Data>"""
        )
        assert isinstance(Data.foo.text, str)
        assert Data.foo.text == "Foo"
        assert isinstance(Data.text.text, str)
        assert Data.text.text.lower() == "bar"
        assert Data.text[1].bar.text.lower() == "bar2"

    def test_append_goes_in_the_middle(self):
        Data = fromstring(
            f"""<Data xmlns='{METADATA_NAMESPACE}'>
                <foo>Foo</foo>
                <bar>Bar</bar>
            </Data>"""
        )
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
        x = Package.tostring(xml_declaration=True).strip()
        assert x == raw

    def test_pretty_printing(self):
        Data = fromstring(f"<Data xmlns='{METADATA_NAMESPACE}'/>")
        Data.append("A", "AA")
        B = Data.append("B")
        B.append("C", "CC")
        Data.append("A", "AB")

        assert (
            Data.tostring(xml_declaration=True)
            == """<?xml version="1.0" encoding="UTF-8"?>
<Data xmlns="http://soap.sforce.com/2006/04/metadata">
    <A>AA</A>
    <A>AB</A>
    <B>
        <C>CC</C>
    </B>
</Data>
"""
        )

    def test_remove(self):
        Data = fromstring(f"<Data xmlns='{METADATA_NAMESPACE}'/>")
        Data.append("A", "AA")
        B = Data.append("B")
        B.append("C", "CC")
        Data.append("A", "AB")

        assert Data.A[0].text == "AA"
        assert Data.B.C.text == "CC"
        assert Data.A[1].text == "AB"

        Data.remove(Data.A[0])
        Data.remove(Data.B)
        Data.remove(Data.A)
        assert Data.tostring() == f'<Data xmlns="{METADATA_NAMESPACE}"/>\n'

    def test_error_handling(self):
        Data = fromstring(f"<Data xmlns='{METADATA_NAMESPACE}'><Foo/></Data>\n")
        Data.Foo
        with pytest.raises(AttributeError) as e:
            assert Data.Bar
        assert "not found in" in str(e.value)

    def test_getattr_getitem(self):
        Data = fromstring(f"<Data xmlns='{METADATA_NAMESPACE}'><Foo/></Data>")
        assert Data.Foo == Data["Foo"]

    def test_missing_text(self):
        Data = fromstring(f"<Data xmlns='{METADATA_NAMESPACE}'><Foo/></Data>")
        with pytest.raises(AttributeError) as e:
            Data.text
        assert "not found in" in str(e.value)

    def test_pathlib_support(self):
        from cumulusci.tasks.metadata import tests

        path = (
            Path(tests.__file__).parent
            / "package_metadata/namespaced_report_folder/package.xml"
        )
        tree = parse(path)
        assert tree

    def test_getitem_error(self):
        Data = fromstring(f"<Data xmlns='{METADATA_NAMESPACE}'><Foo/></Data>")
        with pytest.raises(TypeError):
            Data[None]

    def test_matching(self):
        Data = fromstring(standard_xml)
        assert Data.find("foo").text == Data.findall("foo")[0].text == "Foo"
        assert Data.find("foo", text="Foo2").text == "Foo2"

        assert Data.findall("foo", text="Foo2") == [Data.find("foo", text="Foo2")]

        assert Data.find("foo", name="xyzzy") is None
        assert Data.findall("foo", name="xyzzy") == []
        assert Data.find("foo", text="xyzzy") is None
        assert Data.findall("foo", text="xyzzy") == []
        assert Data.find("bar", name="Bar1").label.text == "Label1"
        assert Data.findall("bar", name="Bar1") == [Data.find("bar", name="Bar1")]
        assert Data.find("bar", name="Bar2").label.text == "Label2"
        assert Data.findall("bar", name="Bar2") == [Data.find("bar", name="Bar2")]
        assert Data.find("bar", name="xyzzy") is None
        assert Data.find("text").text == "Baz"
        assert Data.find("text", text="Baz").text == "Baz"

    def test_equality(self):
        Data = fromstring(standard_xml)
        assert Data.foo == Data.foo[0]

    def test_iteration(self):
        Data = fromstring(standard_xml)

        for foo in Data.foo:
            assert foo.tag == "foo"

        for bar in Data.bar:
            assert bar.tag == "bar"

        # this one might be slightly non-intutive but its a
        # consequence of how the system works
        for child in Data.bar[0]:
            assert child.tag == "bar"

    def test_repr(self):
        Data = fromstring(standard_xml)
        for foo in Data.foo:
            assert repr(foo)

        for bar in Data.bar:
            assert repr(bar)

        Data = fromstring(f"<Data xmlns='{METADATA_NAMESPACE}'></Data>")
        assert repr(Data) == "<Data></Data> element"

    # you'll need to temporarily disable Typeguard to test this properly
    def test_getitem_type_checking(self):
        Data = fromstring(standard_xml)
        with pytest.raises(TypeError):
            Data.foo[None]

    def test_multiple_namespaces(self):
        xml = """
<CustomMetadata xmlns="http://soap.sforce.com/2006/04/metadata" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <label>Account MD Isolation Rollup</label>
    <protected>false</protected>
    <values>
        <field>dlrs__Active__c</field>
        <value xsi:type="xsd:boolean">true</value>
    </values>
</CustomMetadata>""".strip()
        CustomMetadata = fromstring(xml)
        assert xml.strip() == CustomMetadata.tostring().strip()

    def test_namespaced_to_string__do_not_output_namespaces(self):
        CustomMetadata = fromstring(standard_xml)

        xml_out = CustomMetadata.find("bar").find("name").tostring()
        assert xml_out.strip() == "<name>Bar1</name>", xml_out.strip()

    def test_namespaced_to_string__output_namespaces(self):
        CustomMetadata = fromstring(standard_xml)
        xml_out = (
            CustomMetadata.find("bar")
            .find("name")
            .tostring(xml_declaration=True, include_parent_namespaces=True)
        )
        expected_out = """<?xml version="1.0" encoding="UTF-8"?> <name xmlns="http://soap.sforce.com/2006/04/metadata">Bar1</name>"""
        assert (
            " ".join(xml_out.split()).strip() == " ".join(expected_out.split()).strip()
        ), xml_out.strip()
