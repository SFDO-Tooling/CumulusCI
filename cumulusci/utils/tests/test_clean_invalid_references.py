import io
import zipfile
from unittest.mock import Mock, patch

import pytest
from lxml import etree as ET
from simple_salesforce.api import Salesforce

from cumulusci.core.exceptions import CumulusCIUsageError
from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.utils.clean_invalid_references import (
    PermissionElementXPath,
    clean_xml,
    clean_zip_file,
    create_package_xml,
    entities_from_api_calls,
    entities_from_package,
    fetch_permissionable_entity_names,
    get_fields_and_recordtypes,
    get_target_entities_from_zip,
    process_fields,
    process_objects,
    process_tabs,
    process_user_permissions,
    ret_api_version,
    ret_sf,
    return_package_xml_from_zip,
    run_calls_in_parallel,
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
    "    <userPermissions>\n"
    "        <name>View</name>\n"
    "    </userPermissions>\n"
    "    <userPermissions>\n"
    "        <name>EditSetup</name>\n"
    "    </userPermissions>\n"
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


@pytest.mark.parametrize("sample_xml", [SAMPLE_XML])
def test_clean_xml(sample_root):
    target_entities = {
        "fields": {"Field1", "Field2"},
        "recordTypes": {"RecordType1", "RecordType2"},
        "tabs": {"Tab1", "Tab2"},
        "objects": {"Account"},
        "customPermissions": {"CustomPermission1"},
        "userPermissions": {
            "View": set(),
            "Edit": set(),
            "EditSetup": {"View", "Edit"},
        },
    }

    cleaned_root = clean_xml(sample_root, target_entities)
    for element in cleaned_root.findall(".//objectPermissions"):
        assert element.find("object").text in target_entities["objects"]
    for element in cleaned_root.findall(".//customPermissions"):
        assert element.find("name").text in target_entities["customPermissions"]

    for element in cleaned_root.findall(".//objectPermissions"):
        assert "Contact" not in element.find("object").text
    for element in cleaned_root.findall(".//fieldPermissions"):
        assert "SomeField" not in element.find("field").text
    for element in cleaned_root.findall(".//userPermissions"):
        assert "EditSetup" not in element.find("name").text


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
    ) as mock_fields:
        mock_fields.return_value = (
            {"sample.Field1", "sample.Field2"},
            {"sample.RecordType1", "sample.RecordType2"},
        )

        target_entities = get_target_entities_from_zip(sample_zip)

        expected_target_entities = {
            "objects": {"sample"},
            "fields": {"sample.Field1", "sample.Field2"},
            "recordTypes": {"sample.RecordType1", "sample.RecordType2"},
            "applications": {"sample"},
            "tabs": set(),
            "classes": set(),
            "customPermissions": set(),
            "flows": set(),
            "pages": set(),
            "userPermissions": set(),
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


@patch("cumulusci.utils.clean_invalid_references.clean_xml")
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
def test_clean_zip_file(mock_clean_xml, sample_zip):
    # Mock clean_xml
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
    zip_dest = clean_zip_file(sample_zip, target_entities)

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


up_result_dict = {
    "fields": [
        {"name": "PermissionsEdit", "type": "boolean"},
        {"name": "PermissionsView", "type": "boolean"},
        {"name": "PermissionsViewPackage", "type": "boolean"},
    ]
}
pd_result_dict = {
    "records": [
        {"Permission": "ViewSetup", "RequiredPermission": "View"},
        {"Permission": "EditSetup", "RequiredPermission": "Edit"},
        {"Permission": "EditSetup", "RequiredPermission": "View"},
        {"Permission": "ManageSetup", "RequiredPermission": "Manage"},
        {"Permission": "ViewPackage", "RequiredPermission": "View"},
    ]
}
field_result_dict = {
    "fields": [
        {
            "name": "Field",
            "picklistValues": [{"value": "Option1"}, {"value": "Option2"}],
        }
    ],
}
tabs_result_dict = {
    "records": [
        {"Name": "Tab1"},
        {"Name": "Tab2"},
    ],
}
objects_result_dict = {
    "fields": [
        {
            "name": "SobjectType",
            "picklistValues": [{"value": "Object1"}, {"value": "Object2"}],
        },
    ],
}


def test_process_user_permissions():
    result = process_user_permissions(up_result_dict, pd_result_dict)
    expected = {
        "Edit": set(),
        "View": set(),
        "ViewSetup": {"View"},
        "EditSetup": {"Edit", "View"},
        "ViewPackage": {"View"},
        "ManageSetup": {"Manage"},
    }
    assert result == expected


def test_process_fields():
    result = process_fields(field_result_dict)
    expected = {"Option1", "Option2"}
    assert result == expected


def test_process_tabs():
    result = process_tabs(tabs_result_dict)
    expected = {"Tab1", "Tab2"}
    assert result == expected


def test_process_objects():
    result = process_objects(objects_result_dict)
    expected = {"Object1", "Object2"}
    assert result == expected


def sample_run_query(query):
    if query == "query1":
        return ["Query 1 result"]
    elif query == "query2":
        return ["Query 2 result"]
    elif query == "query_data_error":
        raise ValueError("Some error occurred.")


def test_run_calls_in_parallel():
    queries = {
        "query1": "query1",
        "query2": "query2",
    }

    results = run_calls_in_parallel(queries, sample_run_query, num_threads=2)

    assert "query1" in results
    assert "query2" in results
    assert results["query1"] == ["Query 1 result"]
    assert results["query2"] == ["Query 2 result"]


def test_run_calls_in_parallel_exception_handling():
    queries = {
        "query_that_raises": "query_data_error",
    }

    with pytest.raises(Exception) as exc_info:
        run_calls_in_parallel(queries, sample_run_query)
    assert "Error executing call 'query_that_raises':" in str(exc_info.value)


class SampleResponse:
    def __init__(self, result_list):
        self.result_list = result_list

    def json(self):
        return self.result_list


def call_salesforce(method, urlpath):
    result = {
        "123"
        + "tooling/sobjects/PermissionSet/describe": SampleResponse(up_result_dict),
        "123"
        + "tooling/query/?q=SELECT+Permission,+RequiredPermission+FROM+PermissionDependency+WHERE+PermissionType+=+'User Permission'+AND+RequiredPermissionType+=+'User Permission'": SampleResponse(
            pd_result_dict
        ),
        "123" + "sobjects/FieldPermissions/describe": SampleResponse(field_result_dict),
        "123"
        + "sobjects/ObjectPermissions/describe": SampleResponse(objects_result_dict),
        "123"
        + "query/?q=SELECT+Name+FROM+PermissionSetTabSetting+GROUP+BY+Name": SampleResponse(
            tabs_result_dict
        ),
    }
    return result[urlpath]


def test_entities_from_api_calls(task_context):
    sf = Mock()
    sf.base_url = "123"
    sf._call_salesforce = call_salesforce

    result_userpermissions = {
        "Edit": set(),
        "View": set(),
        "ViewSetup": {"View"},
        "EditSetup": {"Edit", "View"},
        "ViewPackage": {"View"},
        "ManageSetup": {"Manage"},
    }
    result_fields = {"Option1", "Option2"}
    result_tabs = {"Tab1", "Tab2"}
    result_objects = {"Object1", "Object2"}

    with patch(
        "cumulusci.utils.clean_invalid_references.process_user_permissions",
        return_value=result_userpermissions,
    ) as mock_process_user_permissions, patch(
        "cumulusci.utils.clean_invalid_references.process_fields",
        return_value=result_fields,
    ) as mock_process_fields, patch(
        "cumulusci.utils.clean_invalid_references.process_tabs",
        return_value=result_tabs,
    ) as mock_process_tabs, patch(
        "cumulusci.utils.clean_invalid_references.process_objects",
        return_value=result_objects,
    ) as mock_process_objects:
        userpermissions, fields, tabs, objects = entities_from_api_calls(sf)
        assert userpermissions == result_userpermissions
        assert fields == result_fields
        assert tabs == result_tabs
        assert objects == result_objects

        mock_process_user_permissions.assert_called_with(up_result_dict, pd_result_dict)
        mock_process_fields.assert_called_with(field_result_dict)
        mock_process_tabs.assert_called_with(tabs_result_dict)
        mock_process_objects.assert_called_with(objects_result_dict)


def test_ret_sf(task_context):
    sf = ret_sf(task_context, "58.0")
    assert isinstance(sf, Salesforce)


@pytest.mark.parametrize(
    "elements",
    [
        [
            ("sample", "sample", ".sample", SAMPLE_XML),
        ]
    ],
)
def test_entities_from_package(task_context, sample_zip):
    zf = Mock()
    with patch(
        "cumulusci.utils.clean_invalid_references.return_package_xml_from_zip",
        return_value="package_xml",
    ), patch.object(ApiRetrieveUnpackaged, "__call__", return_value=sample_zip), patch(
        "cumulusci.utils.clean_invalid_references.get_target_entities_from_zip"
    ) as mock_get_target:
        entities_from_package(zf, task_context, "58.0")
        mock_get_target.assert_called_once_with(sample_zip)


def test_zip_clean_invalid_references(task_context):
    userPermissions = {"UserPermissions": {"UP"}}
    fields = {"fields"}
    tabs = {"tabs"}
    objects = {"objects"}
    entities = {"applications": {"applications"}}

    expected_target_entites = {}
    expected_target_entites.setdefault("tabs", set()).update(tabs)
    expected_target_entites.setdefault("fields", set()).update(fields)
    expected_target_entites.setdefault("objects", set()).update(objects)
    expected_target_entites["userPermissions"] = userPermissions
    expected_target_entites.update(entities)

    zf = Mock()

    with patch("cumulusci.utils.clean_invalid_references.ret_sf"), patch(
        "cumulusci.utils.clean_invalid_references.entities_from_api_calls",
        return_value=(userPermissions, fields, tabs, objects),
    ), patch(
        "cumulusci.utils.clean_invalid_references.entities_from_package",
        return_value=entities,
    ), patch(
        "cumulusci.utils.clean_invalid_references.clean_zip_file"
    ) as mock_clean_zip_file, patch(
        "cumulusci.utils.clean_invalid_references.ret_api_version", return_value="58.0"
    ):
        zip_clean_invalid_references(zf, task_context)
        mock_clean_zip_file.assert_called_once_with(zf, expected_target_entites)


def test_ret_api_version_success():
    zf = zipfile.ZipFile(io.BytesIO(), "w")
    package_xml_contents = (
        b"<?xml version='1.0' encoding='UTF-8'?>"
        b"<Package>"
        b"  <version>52.0</version>"
        b"</Package>"
    )
    zf.writestr("package.xml", package_xml_contents)

    api_version = ret_api_version(zf)
    assert api_version == "52.0"


def test_ret_api_version_failure():
    zf = zipfile.ZipFile(io.BytesIO(), "w")
    package_xml_contents = (
        b"<?xml version='1.0' encoding='UTF-8'?>" b"<Package>" b"</Package>"
    )
    zf.writestr("package.xml", package_xml_contents)

    error_response = "API version not found in the package.xml file."
    with pytest.raises(CumulusCIUsageError) as exc_info:
        ret_api_version(zf)
        assert error_response == str(exc_info.value)


if __name__ == "__main":
    pytest.main()
