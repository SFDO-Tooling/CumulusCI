import io
import zipfile
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict

from lxml import etree as ET
from simple_salesforce.api import Salesforce

from cumulusci.core.dependencies.utils import TaskContext
from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection


class FileName:
    folder_name: str
    extension: str

    def __init__(self, folder_name, extension):
        self.folder_name = folder_name
        self.extension = extension


PROFILE_FILE = FileName("profiles/", ".profile")
PERMISSIONSET_FILE = FileName("permissionsets/", ".permissionset")
FILES_TO_BE_CLEANED = [PROFILE_FILE, PERMISSIONSET_FILE]


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


def run_queries_in_parallel(
    queries: Dict[str, str], run_query: Callable[[str], dict], num_threads: int = 4
):
    """Accepts a set of queries structured as {'query_name': 'query'}
    and a run_query function that runs a particular query. Runs queries in parallel and returns the queries"""
    results_dict = {}

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {
            query_name: executor.submit(run_query, query)
            for query_name, query in queries.items()
        }

    for query_name, future in futures.items():
        try:
            query_result = future.result()
            results_dict[query_name] = query_result
        except Exception as e:
            raise Exception(f"Error executing query '{query_name}': {type(e)}: {e}")
        else:
            queries.pop(query_name, None)

    return results_dict


def entities_from_query(sf: Salesforce):
    # Define the query
    def run_query(path: str):
        urlpath = sf.base_url + path
        method = "GET"
        return sf._call_salesforce(method, urlpath).json()

    # Queries
    queries = {}
    queries["userPermissions"] = "sobjects/PermissionSet/describe"
    queries["fields"] = "sobjects/FieldPermissions/describe"
    queries["objects"] = "sobjects/ObjectPermissions/describe"
    queries["tabs"] = "query/?q=SELECT+Name+FROM+PermissionSetTabSetting+GROUP+BY+Name"

    # Run all queries
    result = run_queries_in_parallel(queries, run_query)

    # Process the results
    user_permissions = process_user_permissions(result["userPermissions"])
    fields = process_fields(result["fields"])
    tabs = process_tabs(result["tabs"])
    objects = process_objects(result["objects"])

    return user_permissions, fields, tabs, objects


def process_user_permissions(result_dict: dict) -> set:
    permissions = [
        f["name"][len("Permissions") :]
        for f in result_dict["fields"]
        if f["name"].startswith("Permissions") and f["type"] == "boolean"
    ]
    return set(permissions)


def process_fields(result_dict: dict) -> set:
    field_entities = []
    for field in result_dict["fields"]:
        if field.get("name") == "Field":
            field_entities.extend(
                picklistValue["value"]
                for picklistValue in field.get("picklistValues", [])
            )
    return set(field_entities)


def process_tabs(result_dict: dict) -> set:
    tabs = [tab["Name"] for tab in result_dict["records"]]
    return set(tabs)


def process_objects(result_dict: dict) -> set:
    objects = []
    for obj in result_dict["fields"]:
        if obj.get("name") == "SobjectType":
            objects.extend(
                picklistValue["value"]
                for picklistValue in obj.get("picklistValues", [])
            )
    return set(objects)


def return_package_xml_from_zip(zip_src: zipfile.ZipFile, api_version: str):
    # Iterate through the zip file to generate the package.xml
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
    fields = set()
    recordTypes = set()

    for field in root.findall("fields"):
        fields.update([objectName + "." + field.find("fullName").text])

    for recordType in root.findall("recordTypes"):
        recordTypes.update([objectName + "." + recordType.find("fullName").text])

    return fields, recordTypes


def get_tabs_from_app(root: ET.Element):
    tabs = set()
    for tab in root.findall("tabs"):
        tabs.update([tab.text])
    return tabs


def get_target_entities_from_zip(zip_src: zipfile.ZipFile):
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

        # To handle tabs which are not part of TabDefinition Table
        if name.endswith(".app"):
            file = zip_src.open(name)
            root = ET.parse(file).getroot()
            root = strip_namespace(root)
            target_entities["tabs"].update(get_tabs_from_app(root))

    return target_entities


def clean_zip_file(zip_src: zipfile.ZipFile, target_entities: Dict[str, set]):
    zip_dest = zipfile.ZipFile(io.BytesIO(), "w", zipfile.ZIP_DEFLATED)
    for name in zip_src.namelist():
        file = zip_src.open(name)
        if any(
            item.extension in name and name.startswith(item.folder_name)
            for item in FILES_TO_BE_CLEANED
        ):
            root = ET.parse(file).getroot()
            cleaned_root = CleanXML(root, target_entities)
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
    for elem in element.iter():
        if "}" in elem.tag:
            elem.tag = elem.tag.split("}", 1)[1]
    return element


def fetch_permissionable_entity_names(
    root: ET.Element, perm_entity: PermissionElementXPath, parent: bool = False
):
    entity_names = set()
    for element in root.findall(perm_entity.permission_xpath):
        entity_names.add(
            perm_entity.return_parent(element)
            if parent
            else perm_entity.return_name(element)
        )
    return entity_names


def CleanXML(root: ET.Element, target_entities: Dict[str, set]):
    root = strip_namespace(root)
    for key, perm_entities in FOLDER_PERM_DICT.items():
        for perm_entity in perm_entities:
            for element in root.findall(perm_entity.permission_xpath):
                if perm_entity.return_name(element) not in target_entities.get(key, []):
                    root.remove(element)
    return root


def entities_from_package(zf: zipfile.ZipFile, context: TaskContext, api_version: str):
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


def zip_clean_invalid_references(zf: zipfile.ZipFile, context: TaskContext):
    # Set API version
    api_version = context.org_config.latest_api_version

    # Query and get entities
    sf = ret_sf(context, api_version)
    userPermissions, fields, tabs, objects = entities_from_query(sf)

    # Update the target entites
    target_entites = {}
    target_entites.update(entities_from_package(zf, context, api_version))
    target_entites.setdefault("userPermissions", set()).update(userPermissions)
    target_entites.setdefault("tabs", set()).update(tabs)
    target_entites.setdefault("fields", set()).update(fields)
    target_entites.setdefault("objects", set()).update(objects)

    # Clean the zip file
    return clean_zip_file(zf, target_entites)
