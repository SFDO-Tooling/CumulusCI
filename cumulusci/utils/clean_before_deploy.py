import io
import zipfile

from lxml import etree as ET


class FileName:
    folder_name: str
    extension: str

    def __init__(self, folder_name, extension):
        self.folder_name = folder_name
        self.extension = extension


PROFILE_FILE = FileName("profiles/", ".profile-meta.xml")
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


def return_package_xml_from_zip(zip_src, api_version: str = "58.0"):
    # Iterate through the zip file to generate the package.xml
    package_xml_input = {}
    for name in zip_src.namelist():
        if any(
            name.endswith(item.extension) and name.startswith(item.folder_name)
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


def get_fields_and_recordtypes(root, objectName):
    fields = set()
    recordTypes = set()

    for field in root.findall("fields"):
        fields.update([objectName + "." + field.find("fullName").text])

    for recordType in root.findall("recordTypes"):
        recordTypes.update([objectName + "." + recordType.find("fullName").text])

    return fields, recordTypes


def get_tabs_from_app(root):
    tabs = set()
    for tab in root.findall("tabs"):
        tabs.update([tab.text])
    return tabs


def get_target_entities_from_zip(zip_src):
    zip_src.extractall("./unpackaged")
    target_entities = {}
    for name in zip_src.namelist():
        if name == "package.xml":
            continue
        metadataType = name.split("/")[0]
        metadataName = name.split("/")[1].split(".")[0]
        target_entities.setdefault(metadataType, set()).update([metadataName])

        # If object, fetch all the fields and record types present inside the file
        if name.endswith(".object"):
            file = zip_src.open(name)
            root = ET.parse(file).getroot()
            root = strip_namespace(root)
            fields, recordTypes = get_fields_and_recordtypes(root, metadataName)
            target_entities.setdefault("fields", set()).update(fields)
            target_entities.setdefault("recordTypes", set()).update(recordTypes)

        # To handle tabs which are not part of TabDefinition Table
        if name.endswith(".app"):
            file = zip_src.open(name)
            root = ET.parse(file).getroot()
            root = strip_namespace(root)
            target_entities.setdefault("tabs", set()).update(get_tabs_from_app(root))

    return target_entities


def zip_clean_invalid_references(zip_src, target_entities):
    zip_dest = zipfile.ZipFile(io.BytesIO(), "w", zipfile.ZIP_DEFLATED)
    for name in zip_src.namelist():
        file = zip_src.open(name)
        if any(
            name.endswith(item.extension) and name.startswith(item.folder_name)
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


def strip_namespace(element):
    for elem in element.iter():
        if "}" in elem.tag:
            elem.tag = elem.tag.split("}", 1)[1]
    return element


def fetch_permissionable_entity_names(
    root, perm_entity: PermissionElementXPath, parent: bool = False
):
    entity_names = set()
    for element in root.findall(perm_entity.permission_xpath):
        entity_names.add(
            perm_entity.return_parent(element)
            if parent
            else perm_entity.return_name(element)
        )
    return entity_names


def CleanXML(root, target_entities):
    root = strip_namespace(root)
    for key, perm_entities in FOLDER_PERM_DICT.items():
        for perm_entity in perm_entities:
            for element in root.findall(perm_entity.permission_xpath):
                if perm_entity.return_name(element) not in target_entities[key]:
                    print(f"{key}: {perm_entity.return_name(element)}")
                    root.remove(element)
    return root
