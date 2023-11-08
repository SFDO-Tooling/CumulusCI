import io
import zipfile
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, Union

from lxml import etree as ET
from simple_salesforce.api import Salesforce

from cumulusci.core.dependencies.utils import TaskContext
from cumulusci.core.exceptions import CumulusCIUsageError
from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection


# Class for folder name and extension of the entities needed to be cleaned
class FileName:
    folder_name: str
    extension: str

    def __init__(self, folder_name, extension):
        self.folder_name = folder_name
        self.extension = extension


# Add here any other entity that you want cleaned in a similar fashion
PROFILE_FILE = FileName("profiles/", ".profile")
PERMISSIONSET_FILE = FileName("permissionsets/", ".permissionset")
FILES_TO_BE_CLEANED = [PROFILE_FILE, PERMISSIONSET_FILE]


# Class for defining the xpath of different entities
class PermissionElementXPath:
    permission_xpath: str
    name_xpath: str

    def __init__(self, permission_xpath, name_xpath):
        self.permission_xpath = permission_xpath
        self.name_xpath = name_xpath

    def return_parent(self, element: ET.Element):
        return element.find(self.name_xpath).text.split(".")[0]

    def return_name(self, element: ET.Element):
        return element.find(self.name_xpath).text


# The entities and their xpath
OBJECT_PERMISSION = PermissionElementXPath(".//objectPermissions", "object")
RECORDTYPE_PERMISSION = PermissionElementXPath(
    ".//recordTypeVisibilities", "recordType"
)
FIELD_PERMISSION = PermissionElementXPath(".//fieldPermissions", "field")
USER_PERMISSION = PermissionElementXPath(".//userPermissions", "name")
TAB_PERMISSION = PermissionElementXPath(".//tabVisibilities", "tab")
APP_PERMISSION = PermissionElementXPath(".//applicationVisibilities", "application")
APEXCLASS_PERMISSION = PermissionElementXPath(".//classAccesses", "apexClass")
APEXPAGE_PERMISSION = PermissionElementXPath(".//pageAccesses", "apexPage")
FLOW_PERMISSION = PermissionElementXPath(".//flowAccesses", "flow")
CUSTOMPERM_PERMISSION = PermissionElementXPath(".//customPermissions", "name")
CUSTOMSETTING_PERMISSION = PermissionElementXPath(".//customSettingAccesses", "name")
CUSTOMMETADATA_PERMISSION = PermissionElementXPath(
    ".//customMetadataTypeAccesses", "name"
)

# Contains the relation between the <name> field (key) inside a package.xml file
# And the <member> field entities and their xpath (value)
PACKAGEXML_DICT = {
    # PERMISSION : is_child
    "CustomObject": {
        OBJECT_PERMISSION: False,
        CUSTOMSETTING_PERMISSION: False,
        CUSTOMMETADATA_PERMISSION: False,
        RECORDTYPE_PERMISSION: True,
        FIELD_PERMISSION: True,
    },
    "ApexClass": APEXCLASS_PERMISSION,
    "ApexPage": APEXPAGE_PERMISSION,
    "Flow": FLOW_PERMISSION,
    "CustomTab": TAB_PERMISSION,
    "CustomApplication": APP_PERMISSION,
    "CustomPermission": CUSTOMPERM_PERMISSION,
}

# Contains the relation between the folder names (key) present inside the zip file from
# ApiRetrievedUnpackaged and the entities and their xpath (value) which are present inside
# those folders
FOLDER_PERM_DICT = {
    "objects": [OBJECT_PERMISSION, CUSTOMSETTING_PERMISSION, CUSTOMMETADATA_PERMISSION],
    "fields": [FIELD_PERMISSION],
    "tabs": [TAB_PERMISSION],
    "applications": [APP_PERMISSION],
    "customPermissions": [CUSTOMPERM_PERMISSION],
    "pages": [APEXPAGE_PERMISSION],
    "classes": [APEXCLASS_PERMISSION],
    "flows": [FLOW_PERMISSION],
    "recordTypes": [RECORDTYPE_PERMISSION],
    "userPermissions": [USER_PERMISSION],
}


def run_calls_in_parallel(
    queries: Dict[str, str], run_call: Callable[[str], dict], num_threads: int = 4
):
    """Accepts a set of calls structured as {'call_name': 'call'}
    and a run_call function that runs a particular call. Runs calls in parallel and returns the resuts"""
    results_dict = {}

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {
            call_name: executor.submit(run_call, call)
            for call_name, call in queries.items()
        }

    for call_name, future in futures.items():
        try:
            call_result = future.result()
            results_dict[call_name] = call_result
        except Exception as e:
            raise Exception(f"Error executing call '{call_name}': {type(e)}: {e}")

    return results_dict


def entities_from_api_calls(sf: Salesforce):
    """Retrieves the set of UserPermissions, Fields, Objects and Tabs from the target org
    by using API calls and returns them"""
    # Define the run_call method
    def run_call(path: str):
        urlpath = sf.base_url + path
        method = "GET"
        return sf._call_salesforce(method, urlpath).json()

    # Queries
    api_calls = {}
    api_calls["userPermissions"] = "tooling/sobjects/PermissionSet/describe"
    api_calls[
        "permissionDependency"
    ] = "tooling/query/?q=SELECT+Permission,+RequiredPermission+FROM+PermissionDependency+WHERE+PermissionType+=+'User Permission'+AND+RequiredPermissionType+=+'User Permission'"
    api_calls["fields"] = "sobjects/FieldPermissions/describe"
    api_calls["objects"] = "sobjects/ObjectPermissions/describe"
    api_calls[
        "tabs"
    ] = "query/?q=SELECT+Name+FROM+PermissionSetTabSetting+GROUP+BY+Name"

    # Run all api_calls
    result = run_calls_in_parallel(api_calls, run_call)

    # Process the results
    user_permissions = process_user_permissions(
        result["userPermissions"], result["permissionDependency"]
    )
    fields = process_fields(result["fields"])
    tabs = process_tabs(result["tabs"])
    objects = process_objects(result["objects"])

    return user_permissions, fields, tabs, objects


def process_user_permissions(
    result_dict_user_permission: dict, result_dict_permission_dependency: dict
) -> dict:
    """Process the result of the API Call and return UserPermissions"""
    user_permissions = {}
    for field in result_dict_user_permission["fields"]:
        if field["name"].startswith("Permissions") and field["type"] == "boolean":
            user_permissions.setdefault(field["name"][len("Permissions") :], set())

    for record in result_dict_permission_dependency["records"]:
        user_permissions.setdefault(record["Permission"], set()).update(
            [record["RequiredPermission"]]
        )

    return user_permissions


def process_fields(result_dict: dict) -> set:
    """Process the result of the API Call and return Fields"""
    field_entities = []
    for field in result_dict["fields"]:
        if field.get("name") == "Field":
            field_entities.extend(
                picklistValue["value"]
                for picklistValue in field.get("picklistValues", [])
            )
    return set(field_entities)


def process_tabs(result_dict: dict) -> set:
    """Process the result of the API Call and return Tabs"""
    return {tab["Name"] for tab in result_dict["records"]}


def process_objects(result_dict: dict) -> set:
    """Process the result of the API Call and return Objects"""
    objects = []
    for obj in result_dict["fields"]:
        if obj.get("name") == "SobjectType":
            objects.extend(
                picklistValue["value"]
                for picklistValue in obj.get("picklistValues", [])
            )
    return set(objects)


def return_package_xml_from_zip(zip_src: zipfile.ZipFile, api_version: str):
    """Iterates through the zip file, searches for profile/permissionset files,
    extracts all permissionable entities, creates a package.xml file containing them,
    and returns the resulting package.xml file"""
    package_xml_input = {}
    for name in zip_src.namelist():
        if any(
            item.extension in name and name.startswith(item.folder_name)
            for item in FILES_TO_BE_CLEANED
        ):
            file = zip_src.open(name)
            root = ET.parse(file).getroot()
            root = strip_namespace(root)
            for key, value in PACKAGEXML_DICT.items():
                if isinstance(value, dict):
                    for perm, parent in value.items():
                        package_xml_input.setdefault(key, set()).update(
                            fetch_permissionable_entity_names(root, perm, parent)
                        )
                else:
                    package_xml_input.setdefault(key, set()).update(
                        fetch_permissionable_entity_names(root, value)
                    )
    # Remove any entities with no entries
    package_xml_input = {
        key: value for key, value in package_xml_input.items() if value
    }
    package_xml = create_package_xml(
        input_dict=package_xml_input, api_version=api_version
    )
    return package_xml


def create_package_xml(input_dict: dict, api_version: str):
    """Given the entities, create the package.xml"""
    package_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    package_xml += '<Package xmlns="http://soap.sforce.com/2006/04/metadata">\n'

    for name, members in input_dict.items():
        package_xml += "    <types>\n"
        for member in members:
            package_xml += f"        <members>{member}</members>\n"
        package_xml += f"        <name>{name}</name>\n"
        package_xml += "    </types>\n"

    package_xml += f"    <version>{api_version}</version>\n"
    package_xml += "</Package>\n"
    return package_xml


def get_fields_and_recordtypes(root: ET.Element, objectName):
    """Get the fields and record types that are present inside the .object file"""
    fields = set()
    recordTypes = set()

    for field in root.findall("fields"):
        fields.update([objectName + "." + field.find("fullName").text])

    for recordType in root.findall("recordTypes"):
        recordTypes.update([objectName + "." + recordType.find("fullName").text])

    return fields, recordTypes


def get_target_entities_from_zip(zip_src: zipfile.ZipFile):
    """Accepts the resulting zip file from ApiRetrievedUnpackaged
    and returns all the entities which are present in the target org"""
    target_entities = {key: set() for key in FOLDER_PERM_DICT.keys()}
    for name in zip_src.namelist():
        if name == "package.xml":
            continue
        metadataType = name.split("/")[0]
        metadataName = name.split("/")[1].split(".")[0]
        target_entities[metadataType].update([metadataName])

        # If object, fetch all the fields and record types present inside the file
        if name.endswith(".object"):
            file = zip_src.open(name)
            root = ET.parse(file).getroot()
            root = strip_namespace(root)
            fields, recordTypes = get_fields_and_recordtypes(root, metadataName)
            target_entities["fields"].update(fields)
            target_entities["recordTypes"].update(recordTypes)

    return target_entities


def clean_zip_file(
    zip_src: zipfile.ZipFile, target_entities: Dict[str, Union[set, dict]]
):
    """Parses through the zip file and removes any of the permissionable entities
    which are not present in the target_entities"""
    zip_dest = zipfile.ZipFile(io.BytesIO(), "w", zipfile.ZIP_DEFLATED)
    for name in zip_src.namelist():
        file = zip_src.open(name)
        if any(
            item.extension in name and name.startswith(item.folder_name)
            for item in FILES_TO_BE_CLEANED
        ):
            root = ET.parse(file).getroot()
            cleaned_root = clean_xml(root, target_entities)
            tree = ET.ElementTree(cleaned_root)
            cleaned_content = io.BytesIO()
            tree.write(
                cleaned_content,
                pretty_print=True,
                xml_declaration=True,
                encoding="utf-8",
            )
            zip_dest.writestr(name, cleaned_content.getvalue())
        else:
            zip_dest.writestr(name, file.read())

    return zip_dest


def strip_namespace(element: ET.Element):
    """Remove the namespace in the xml tree"""
    for elem in element.iter():
        if "}" in elem.tag:
            elem.tag = elem.tag.split("}", 1)[1]
    return element


def fetch_permissionable_entity_names(
    root: ET.Element, perm_entity: PermissionElementXPath, parent: bool = False
):
    """Return the name of the entity given the xpath.
    If parent is set to True, the entity's parent name is fetched"""
    entity_names = set()
    for element in root.findall(perm_entity.permission_xpath):
        entity_names.add(
            perm_entity.return_parent(element)
            if parent
            else perm_entity.return_name(element)
        )
    return entity_names


def clean_xml(root: ET.Element, target_entities: Dict[str, Union[set, dict]]):
    """Given the xml tree, remove entities not present in target_entities"""
    root = strip_namespace(root)
    user_permissions_source_org = {}
    for key, perm_entities in FOLDER_PERM_DICT.items():
        for perm_entity in perm_entities:
            for element in root.findall(perm_entity.permission_xpath):
                entity_name = perm_entity.return_name(element)
                # If entity is a user permission, store it
                if key == "userPermissions":
                    user_permissions_source_org[entity_name] = element
                if entity_name not in target_entities.get(key, []):
                    root.remove(element)

    # Remove those UserPermissions which dont have required dependencies
    # Find elements that should be removed based on dependencies
    elements_to_remove = set()
    for permission, dependencies_list in target_entities["userPermissions"].items():
        if permission in user_permissions_source_org and not all(
            dependency in user_permissions_source_org
            for dependency in dependencies_list
        ):
            elements_to_remove.add(user_permissions_source_org[permission])
    # Remove elements
    for element in elements_to_remove:
        root.remove(element)
    return root


def entities_from_package(zf: zipfile.ZipFile, context: TaskContext, api_version: str):
    """Creates package.xml with all permissionable entities from the profiles and permissionsets.
    Uses ApiRetrieveUnpackaged to retieve all these entities from the target org and generate a
    list of entities present in the target org"""
    package_xml = return_package_xml_from_zip(zf, api_version)
    api = ApiRetrieveUnpackaged(
        context, package_xml=package_xml, api_version=api_version
    )
    context.logger.info("Retrieving entities from package.xml")
    retrieved_zf = api()
    return get_target_entities_from_zip(retrieved_zf)


def ret_sf(context: TaskContext, api_version: str):
    sf = get_simple_salesforce_connection(
        context.project_config,
        context.org_config,
        api_version=api_version,
        base_url=None,
    )
    return sf


def ret_api_version(zf: zipfile.ZipFile):
    with zf.open("package.xml") as package_xml_file:
        package_xml_contents = package_xml_file.read()
        root = ET.fromstring(package_xml_contents)
        root = strip_namespace(root)
        version_element = root.find(".//version")
        if version_element is not None:
            api_version = version_element.text
            return api_version
        else:
            raise CumulusCIUsageError("API version not found in the package.xml file.")


def zip_clean_invalid_references(zf: zipfile.ZipFile, context: TaskContext):
    """Cleans the profiles and permissionset files in the zip file of any invalid references"""
    # Set API version
    api_version = ret_api_version(zf)
    # Query and get entities
    sf = ret_sf(context, api_version)
    user_permissions, fields, tabs, objects = entities_from_api_calls(sf)

    # Update the target entites
    target_entities = {}
    target_entities.update(entities_from_package(zf, context, api_version))
    target_entities.setdefault("tabs", set()).update(tabs)
    target_entities.setdefault("fields", set()).update(fields)
    target_entities.setdefault("objects", set()).update(objects)
    target_entities["userPermissions"] = user_permissions

    # Clean the zip file
    return clean_zip_file(zf, target_entities)
