from glob import glob
from pathlib import Path
from tempfile import TemporaryDirectory
from io import StringIO

from lxml import etree
import pytest

from cumulusci.utils.xml.salesforce_encoding import serialize_xml_for_salesforce


class TestSalesforceEncoding:
    def test_xml_declaration(self):
        xml = etree.parse(StringIO("<foo/>"))
        print("xml", xml)
        out = serialize_xml_for_salesforce(xml, xml_declaration=True)
        assert out.startswith("<?xml")

        out = serialize_xml_for_salesforce(xml, xml_declaration=False)
        assert not out.startswith("<?xml")

        out = serialize_xml_for_salesforce(xml)
        assert out.startswith("<?xml")

    def test_roundtripping(self):
        from cumulusci.tasks.metadata import tests

        print("Q", Path(tests.__file__).parent / "sample_package.xml")

        print("r", Path(tests.__file__).parent / "sample_package.xml")

        files = glob(str(Path(tests.__file__).parent / "sample_package.xml"))

        #   If you fiddle with the salesforce encoder, the code below may be
        #   useful to ensure that it faithfully round-trips, but it only works
        #   if run in a directory with a parent-directory which contains a few
        #   CCI projects which contain translations in them. At the time of
        #   writing it roundtripped 421 files without a byte of difference.
        #
        # files = glob("../*/*/*ranslations/**ranslation", recursive=True)

        assert files

        for file in files:
            orig = open(file).read()
            tree = etree.parse(file)
            out = serialize_xml_for_salesforce(tree)
            print(f"[{orig}]")
            print(f"[{out}]")
            assert orig == out, f"Filename did not roundtrip cleanly {file}"
            print("PASSED", file)

    def tests_filename_bad_xml(self):
        with TemporaryDirectory() as d:
            filename = d + "/foobar.notxml"
            with open(filename, "w") as f:
                f.write("<<<<")
            with pytest.raises(SyntaxError) as e:
                etree.parse(filename)
            assert "foobar.notxml" in str(e.value)

    def test_comment(self):
        tree = etree.parse(
            StringIO(
                "<Foo><!-- Salesforce files should not have comments, but just in case! --> </Foo>"
            )
        )
        assert "just in case! -->" in serialize_xml_for_salesforce(tree)

    def test_namespaces(self):
        tree = etree.parse(StringIO("<Foo xmlns:foo='https://html5zombo.com/'></Foo>"))
        with pytest.raises(AssertionError):
            serialize_xml_for_salesforce(tree)
