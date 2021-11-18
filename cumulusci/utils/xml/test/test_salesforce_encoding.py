from glob import glob
from pathlib import Path
from shutil import rmtree
from tempfile import TemporaryDirectory, mkdtemp

import pytest
from lxml import etree

from cumulusci.utils.xml import lxml_parse_file, lxml_parse_string
from cumulusci.utils.xml.salesforce_encoding import serialize_xml_for_salesforce


class TestSalesforceEncoding:
    def test_xml_declaration(self):
        xml = lxml_parse_string("<foo/>")
        out = serialize_xml_for_salesforce(xml, xml_declaration=True)
        assert out.startswith("<?xml")

        out = serialize_xml_for_salesforce(xml, xml_declaration=False)
        assert not out.startswith("<?xml")

        out = serialize_xml_for_salesforce(xml)
        assert out.startswith("<?xml")

    def test_roundtripping(self):
        from cumulusci.tasks.metadata import tests

        files = glob(str(Path(tests.__file__).parent / "sample_package.xml"))

        #   If you fiddle with the salesforce encoder, the code below may be
        #   useful to ensure that it faithfully round-trips, but it only works
        #   if run in a directory with a parent-directory which contains a few
        #   CCI projects which contain translations in them. At the time of
        #   writing it roundtripped 421 files without a byte of difference.
        #
        # files += glob("../**/*ranslations/**ranslation", recursive=True)
        # files += glob("../**/*-meta.xml", recursive=True)
        # files += glob("../**/package.xml", recursive=True)
        # files += glob("../**/*.object.xml", recursive=True)

        assert files

        problems = []

        temp_directory = mkdtemp(prefix="xmltests")
        for file in files:
            with open(file) as f:
                orig = f.read().strip()

            tree = lxml_parse_file(file)
            out = serialize_xml_for_salesforce(tree).strip()
            try:
                orig = etree.canonicalize(orig)
                out = etree.canonicalize(out)
                c19n_succeeded = True
            except Exception:  # pragma: no cover
                c19n_succeeded = False
            try:
                assert orig == out, file
            except Exception as e:  # pragma: no cover
                details = self._save_exception_for_inspection(
                    file, temp_directory, orig, out, c19n_succeeded, e
                )
                problems.append(details)

        assert not problems, (temp_directory, len(problems))
        rmtree(temp_directory)  # clean up if there was no assertion failure

    def _save_exception_for_inspection(
        self, file, temp_directory, orig, out, c19n_succeeded, exception
    ):  # pragma: no cover
        filename = Path(file).name
        infile_copy = str(Path(temp_directory) / filename)
        with open(infile_copy, "w") as f:
            f.write(orig)
        outfile_copy = infile_copy + ".out.xml"
        with open(outfile_copy, "w") as f:
            f.write(out)
        outfile_exception = infile_copy + ".err"
        with open(outfile_exception, "w") as f:
            f.write(file)
            f.write(f"C19 Status: {c19n_succeeded}")
            f.write("\n")
            f.write(str(exception))
        return (infile_copy, outfile_copy, outfile_exception, file)

    def tests_filename_bad_xml(self):
        with TemporaryDirectory() as d:
            filename = d + "/foobar.notxml"
            with open(filename, "w") as f:
                f.write("<<<<")
            with pytest.raises(SyntaxError) as e:
                lxml_parse_file(filename)
            assert "foobar.notxml" in str(e.value)

    def test_comment(self):
        tree = lxml_parse_string(
            "<Foo><!-- Salesforce files should not have comments, but just in case! --> </Foo>"
        )
        assert "just in case! -->" in serialize_xml_for_salesforce(tree)

    def test_empty_elements(self):
        xml_in = """
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <layoutSections>
        <layoutColumns/>
        <layoutColumns/>
        <layoutColumns/>
        <style>CustomLinks</style>
    </layoutSections>
</Layout>""".strip()

        tree = lxml_parse_string(xml_in)

        xml_out = serialize_xml_for_salesforce(tree, xml_declaration=False)
        assert xml_in == xml_out.strip()

    def test_namespaces(self):
        xml_in = '<Foo xmlns:foo="https://html5zombo.com/" xmlns:dad="http://niceonedad.com/"/>\n'
        tree = lxml_parse_string(xml_in)

        xml_out = serialize_xml_for_salesforce(tree, xml_declaration=False)
        assert xml_in == xml_out

    def test_simple_attributes_roundtrip(self):
        xml_in = """
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <layoutSections>
        <layoutColumns foo="bar"/>
    </layoutSections>
</Layout>""".strip()

        tree = lxml_parse_string(xml_in)

        xml_out = serialize_xml_for_salesforce(tree, xml_declaration=False)
        assert xml_in == xml_out.strip()

    def test_namespaced_attributes_roundtrip(self):
        xml_in = """
<CustomMetadata xmlns="http://soap.sforce.com/2006/04/metadata" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <label>Account MD Isolation Rollup</label>
    <protected>false</protected>
    <values>
        <field>dlrs__Active__c</field>
        <value xsi:type="xsd:boolean">true</value>
    </values>
</CustomMetadata>""".strip()

        tree = lxml_parse_string(xml_in)

        xml_out = serialize_xml_for_salesforce(tree, xml_declaration=False)
        assert xml_in == xml_out.strip()

    def test_with_element_rather_than_doc(self):
        xml_in = """
<CustomMetadata xmlns="http://soap.sforce.com/2006/04/metadata" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <label>Account MD Isolation Rollup</label>
    <protected>false</protected>
    <values>
        <field>dlrs__Active__c</field>
        <value xsi:type="xsd:boolean">true</value>
    </values>
</CustomMetadata>""".strip()

        tree = lxml_parse_string(xml_in)

        xml_out = serialize_xml_for_salesforce(tree.getroot(), xml_declaration=False)
        assert xml_in == xml_out.strip()

        xml_out = serialize_xml_for_salesforce(
            tree.getroot()[-1][0], xml_declaration=False
        )
        assert xml_out.strip() == "<field>dlrs__Active__c</field>"
