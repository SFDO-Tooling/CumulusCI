import io
import zipfile
from unittest.mock import patch

import pytest
from lxml import etree as ET

from cumulusci.utils.clean_invalid_references import (
    CleanXML,
    PermissionElementXPath,
    create_package_xml,
    fetch_permissionable_entity_names,
    get_fields_and_recordtypes,
    get_tabs_from_app,
    get_target_entities_from_zip,
    return_package_xml_from_zip,
    strip_namespace,
    zip_clean_invalid_references,
)

EXPECTED_PACKAGEXML = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Package xmlns="http://soap.sforce.com/2006/04/metadata">\n'
    "    <types>\n"
    "        <members>Account</members>\n"
    "        <members>Contact</members>\n"
    "        <name>CustomObject</name>\n"
    "    </types>\n"
    "    <types>\n"
    "        <members>MyClass</members>\n"
    "        <name>ApexClass</name>\n"
    "    </types>\n"
    "    <version>58.0</version>\n"
    "</Package>"
)

SAMPLE_XML = (
    "<root>\n"
    "    <objectPermissions>\n"
    "        <object>Account</object>\n"
    "    </objectPermissions>\n"
    "    <objectPermissions>\n"
    "        <object>Contact</object>\n"
    "    </objectPermissions>\n"
    "    <fieldPermissions>\n"
    "        <field>Opportunity.SomeField</field>\n"
    "    </fieldPermissions>\n"
    "    <customPermissions>\n"
    "        <name>CustomPermission1</name>\n"
    "    </customPermissions>\n"
    "</root>\n"
)

EXPECTED_XML = (
    "<?xml version='1.0' encoding='UTF-8'?>\n"
    "<root>\n"
    "    <objectPermissions>\n"
    "        <object>Account</object>\n"
    "    </objectPermissions>\n"
    "    <fieldPermissions>\n"
    "        <field>Opportunity.SomeField</field>\n"
    "    </fieldPermissions>\n"
    "</root>\n"
)

SAMPLE_OBJ_XML = (
    "<root>\n"
    "   <fields>\n"
    "       <fullName>Field2</fullName>\n"
    "   </fields>\n"
    "   <fields>\n"
    "       <fullName>Field1</fullName>\n"
    "   </fields>\n"
    "   <recordTypes>\n"
    "       <fullName>RecordType1</fullName>\n"
    "   </recordTypes>\n"
    "   <recordTypes>\n"
    "       <fullName>RecordType2</fullName>\n"
    "   </recordTypes>\n"
    "</root>"
)

SAMPLE_APP_XML = "<root>\n" "   <tabs>Tab1</tabs>\n" "   <tabs>Tab2</tabs>\n" "</root>"

PROFILE = ("Profile", "profiles", ".profile-meta.xml")
PERMISSIONSET = ("PermissionSet", "permissionsets", ".permissionset")


@pytest.fixture
def sample_root(sample_xml):
    xml = sample_xml
    return ET.fromstring(xml)


@pytest.mark.parametrize("sample_xml", [SAMPLE_XML])
def test_fetch_permissionable_entity_names(sample_root):
    permission_element = PermissionElementXPath(".//objectPermissions", "object")
    entity_names = fetch_permissionable_entity_names(sample_root, permission_element)
    expected_result = {"Account", "Contact"}
    assert entity_names == expected_result

    permission_element = PermissionElementXPath(".//fieldPermissions", "field")
    entity_names = fetch_permissionable_entity_names(
        sample_root, permission_element, parent=True
    )
    expected_result = {"Opportunity"}
    assert entity_names == expected_result


@pytest.mark.parametrize("sample_xml", [SAMPLE_OBJ_XML])
def test_get_fields_and_recordtypes(sample_root):
    fields, recordTypes = get_fields_and_recordtypes(sample_root, "SampleObject")
    expected_fields = {"SampleObject.Field1", "SampleObject.Field2"}
    expected_recordTypes = {"SampleObject.RecordType1", "SampleObject.RecordType2"}
    assert fields == expected_fields
    assert recordTypes == expected_recordTypes


@pytest.mark.parametrize("sample_xml", [SAMPLE_APP_XML])
def test_get_tabs_from_app(sample_root):
    tabs = get_tabs_from_app(sample_root)
    expected_tabs = {"Tab1", "Tab2"}
    assert tabs == expected_tabs


@pytest.mark.parametrize("sample_xml", [SAMPLE_XML])
def test_CleanXML(sample_root):
    target_entities = {
        "fields": {"Field1", "Field2"},
        "recordTypes": {"RecordType1", "RecordType2"},
        "tabs": {"Tab1", "Tab2"},
        "objects": {"Account"},
        "customPermissions": {"CustomPermission1"},
    }

    cleaned_root = CleanXML(sample_root, target_entities)
    for element in cleaned_root.findall(".//objectPermissions"):
        assert element.find("object").text in target_entities["objects"]
    for element in cleaned_root.findall(".//customPermissions"):
        assert element.find("name").text in target_entities["customPermissions"]

    for element in cleaned_root.findall(".//objectPermissions"):
        assert "Contact" not in element.find("object").text
    for element in cleaned_root.findall(".//fieldPermissions"):
        assert "SomeField" not in element.find("field").text


@pytest.fixture
def sample_zip(elements):
    zip_file = zipfile.ZipFile(io.BytesIO(), "w", zipfile.ZIP_DEFLATED)
    for folder, name, extension, sample_xml in elements:
        if folder is not None:
            zip_file.writestr(f"{folder}/{name}{extension}", sample_xml)
        else:
            zip_file.writestr(f"{name}{extension}", sample_xml)

    return zip_file


@pytest.mark.parametrize(
    "elements",
    [
        [
            ("objects", "sample", ".object", SAMPLE_OBJ_XML),
            ("applications", "sample", ".app", SAMPLE_APP_XML),
            (None, "package", ".xml", EXPECTED_PACKAGEXML),
        ]
    ],
)
def test_get_target_entities_from_zip(sample_zip):
    with patch(
        "cumulusci.utils.clean_invalid_references.get_fields_and_recordtypes"
    ) as mock_fields, patch(
        "cumulusci.utils.clean_invalid_references.get_tabs_from_app"
    ) as mock_tabs:
        mock_fields.return_value = (
            {"sample.Field1", "sample.Field2"},
            {"sample.RecordType1", "sample.RecordType2"},
        )
        mock_tabs.return_value = {"Tab1", "Tab2"}

        target_entities = get_target_entities_from_zip(sample_zip)

        expected_target_entities = {
            "objects": {"sample"},
            "fields": {"sample.Field1", "sample.Field2"},
            "recordTypes": {"sample.RecordType1", "sample.RecordType2"},
            "applications": {"sample"},
            "tabs": {"Tab1", "Tab2"},
        }
        assert target_entities == expected_target_entities


@patch("cumulusci.utils.clean_invalid_references.fetch_permissionable_entity_names")
@pytest.mark.parametrize(
    "elements",
    [
        [
            ("profiles", "sample", ".profile", SAMPLE_XML),
            ("permissionsets", "sample", ".permissionset", SAMPLE_XML),
        ]
    ],
)
def test_return_package_xml_from_zip(mock_fetch_entities, sample_zip):

    # Mock Fetch Entities
    def fetch_entities(root, perm, parent=False):
        entity_names = set()
        for element in root.findall(perm.permission_xpath):
            if parent:
                entity_names.add(element.find(perm.name_xpath).text.split(".")[0])
            else:
                entity_names.add(element.find(perm.name_xpath).text)
        return entity_names

    mock_fetch_entities.side_effect = fetch_entities

    with patch(
        "cumulusci.utils.clean_invalid_references.create_package_xml"
    ) as mock_create_package_xml:
        return_package_xml_from_zip(sample_zip, "58.0")

        expected_input_dict = {
            "CustomObject": {"Account", "Contact", "Opportunity"},
            "CustomPermission": {"CustomPermission1"},
        }
        mock_create_package_xml.assert_called_with(
            input_dict=expected_input_dict, api_version="58.0"
        )


@patch("cumulusci.utils.clean_invalid_references.CleanXML")
@pytest.mark.parametrize(
    "elements",
    [
        [
            ("profiles", "sample", ".profile", SAMPLE_XML),
            ("permissionsets", "sample", ".permissionset", SAMPLE_XML),
            ("some_folder", "sample", ".some_extension", SAMPLE_XML),
        ]
    ],
)
def test_zip_clean_invalid_references(mock_clean_xml, sample_zip):
    # Mock CleanXML
    def clean_xml(root, target_entities):
        for element in root.findall(".//objectPermissions"):
            if element.find("object").text == "Contact":
                root.remove(element)

        for element in root.findall(".//customPermissions"):
            root.remove(element)
        return root

    mock_clean_xml.side_effect = clean_xml

    # Call the function
    target_entities = {"something": {"something"}}
    zip_dest = zip_clean_invalid_references(sample_zip, target_entities)

    name_list = [
        "profiles/sample.profile",
        "permissionsets/sample.permissionset",
        "some_folder/sample.some_extension",
    ]
    for name in zip_dest.namelist():
        assert name in name_list
        result_root = ET.parse(zip_dest.open(name)).getroot()
        expected_root = ET.fromstring(EXPECTED_XML.encode("utf-8"))
        assert ET.iselement(result_root) == ET.iselement(expected_root)


def test_create_package_xml():
    input_dict = {
        "CustomObject": {"Account", "Contact"},
        "ApexClass": {"MyClass"},
    }
    api_version = "58.0"
    result = create_package_xml(input_dict, api_version)

    result_root = ET.fromstring(result.encode("utf-8"))
    expected_root = ET.fromstring(EXPECTED_PACKAGEXML.encode("utf-8"))
    assert ET.iselement(result_root) == ET.iselement(expected_root)


def test_strip_namespace():
    xml_string = """
    <root xmlns:ns1="http://example.com/ns1">
        <ns1:element1>Value 1</ns1:element1>
        <ns1:element2>Value 2</ns1:element2>
    </root>
    """
    root = ET.fromstring(xml_string)

    root = strip_namespace(root)
    element1 = root.find("element1")
    element2 = root.find("element2")

    assert element1.text == "Value 1"
    assert element2.text == "Value 2"


if __name__ == "__main":
    pytest.main()
