import os
from collections import defaultdict

import pkg_resources

from cumulusci.core.exceptions import CumulusCIException, TaskOptionsError
from cumulusci.core.utils import process_bool_arg, process_list_arg
from cumulusci.tasks.metadata_etl import (
    MetadataOperation,
    MetadataSingleEntityTransformTask,
)
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.utils import CUMULUSCI_PATH
from cumulusci.utils.xml import metadata_tree


class ProfileGrantAllAccess(MetadataSingleEntityTransformTask, BaseSalesforceApiTask):
    name = "ProfileGrantAllAccess"
    entity = "Profile"

    task_options = {
        "package_xml": {
            "description": "Override the default package.xml file for retrieving the Admin.profile and all objects and classes "
            "that need to be included by providing a path to your custom package.xml"
        },
        "record_types": {
            "description": "A list of dictionaries containing the required key `record_type` with a value specifying "
            "the record type in format <object>.<developer_name>.  Record type names can use the token strings {managed} "
            "and {namespaced_org} for namespace prefix injection as needed.  By default, all listed record types will be set "
            "to visible and not default.  Use the additional keys `visible`, `default`, and `person_account_default` set to "
            "true/false to override.  "
            "Page Layout Support: If you are using the Page Layouts feature, you can specify the `page_layout` key with the "
            "layout name to use for the record type.  If not specified, the default page layout will be used.  "
            "NOTE: Setting record_types is only supported in cumulusci.yml, command line override is not supported."
        },
        "managed": {
            "description": "If True, uses the namespace prefix where appropriate.  Use if running against an org with the managed package "
            "installed.  Defaults to False"
        },
        "namespaced_org": {
            "description": "If True, attempts to prefix all unmanaged metadata references with the namespace prefix for deployment to the "
            "packaging org or a namespaced scratch org.  Defaults to False"
        },
        "namespace_inject": {
            "description": "If set, the namespace tokens in files and filenames are replaced with the namespace's prefix. "
            "Defaults to project__package__namespace"
        },
        "profile_name": {
            "description": "Name of the Profile to target for updates (deprecated; use api_names to target multiple profiles).",
            "default": "Admin",
        },
        "include_packaged_objects": {
            "description": "Automatically include objects from all installed managed packages. "
            "Defaults to True in projects that require CumulusCI 3.9.0 and greater that don't use a custom package.xml, otherwise False."
        },
        "api_names": {"description": "List of API names of Profiles to affect"},
    }

    def _init_options(self, kwargs):
        super(ProfileGrantAllAccess, self)._init_options(kwargs)

        self.options["namespace_inject"] = self.options.get(
            "namespace_inject", self.project_config.project__package__namespace
        )

        # We enable new functionality to extend the package.xml to packaged objects
        # by default only if we meet specific requirements: the project has to require
        # CumulusCI >= 3.9.0 (i.e., creation date or opt-in after release), and it must
        # not be using a custom `package.xml`
        min_cci_version = self.project_config.minimum_cumulusci_version
        if min_cci_version and "package_xml" not in self.options:
            parsed_version = pkg_resources.parse_version(min_cci_version)
            default_packages_arg = parsed_version >= pkg_resources.parse_version(
                "3.9.0"
            )
        else:
            default_packages_arg = False

        self.options["include_packaged_objects"] = process_bool_arg(
            self.options.get("include_packaged_objects", default_packages_arg)
        )

        # Build the api_names list, taking into account legacy behavior.
        # If we're using a custom package.xml, we will union the api_names list with
        # any Profiles specified there.
        self.api_names = set(process_list_arg(self.options.get("api_names") or []))
        if "profile_name" in self.options:
            self.api_names.add(self.options["profile_name"])
        if not self.api_names and "package_xml" not in self.options:
            self.api_names.add(
                "Admin"
            )  # Don't add a default if using custom package.xml

        if "package_xml" in self.options:
            self.package_xml_path = self.options["package_xml"]
        else:
            self.package_xml_path = os.path.join(
                CUMULUSCI_PATH, "cumulusci", "files", "admin_profile.xml"
            )

        if self.org_config is not None:
            # Set up namespace prefix strings.
            # We can only do this if we actually have an org_config;
            # i.e. not while freezing steps for metadeploy
            namespace = self.options["namespace_inject"]
            namespace_prefix = f"{namespace}__" if namespace else ""
            self.namespace_prefixes = {
                "managed": namespace_prefix if self.options["managed"] else "",
                "namespaced_org": namespace_prefix
                if self.options["namespaced_org"]
                else "",
            }
            self.api_names = {self._inject_namespace(x) for x in self.api_names}

    def freeze(self, step):
        # Preserve behavior from when we subclassed Deploy.

        steps = super().freeze(step)
        for step in steps:
            if step["kind"] == "other":
                step["kind"] = "metadata"
        return steps

    def _generate_package_xml(self, operation):
        if operation is MetadataOperation.RETRIEVE:
            with open(self.package_xml_path, "r", encoding="utf-8") as f:
                package_xml_content = f.read()

            package_xml_content = package_xml_content.format(**self.namespace_prefixes)

            # We need to rewrite the package.xml for one or two reasons.
            # Either we are using packaged-object expansion, or we're using
            # a package.xml and need to substitute in profile API names.

            # Convert to bytes because stored `package.xml`s typically have an encoding declaration,
            # which `fromstring()` doesn't like.
            package_xml = metadata_tree.fromstring(package_xml_content.encode("utf-8"))

            if self.options["include_packaged_objects"]:
                self._expand_package_xml(package_xml)

            self._expand_profile_members(package_xml)

            package_xml_content = package_xml.tostring(xml_declaration=True)

            return package_xml_content
        else:
            return super()._generate_package_xml(operation)

    def _expand_profile_members(self, package_xml):
        profile_names = package_xml.find("types", name="Profile")
        if not profile_names:
            profile_names = package_xml.append("types")
            profile_names.append("name", "Profile")

        listed_api_names = {p.text for p in profile_names.findall("members")}

        for profile in self.api_names:
            if profile not in listed_api_names:
                profile_names.append("members", text=profile)

        self.api_names.update(listed_api_names)

    def _expand_package_xml(self, package_xml):
        # Query the target org for all namespaced objects
        # Add these entities to the package.xml

        results = self.tooling.query_all(
            "SELECT DeveloperName, NamespacePrefix FROM CustomObject WHERE ManageableState != 'unmanaged'"
        )

        custom_objects = package_xml.find("types", name="CustomObject")
        if not custom_objects:
            raise CumulusCIException(
                "Unable to add packaged objects to package.xml because it does not contain a <types> tag of type CustomObject."
            )

        for record in results.get("records", []):
            custom_objects.append(
                "members",
                text=f"{record['NamespacePrefix']}__{record['DeveloperName']}__c",
            )

        self._expand_package_xml_objects(package_xml)

    def _expand_package_xml_objects(self, package_xml):
        # Check for any record types specified in the options, but missing from the package.xml
        # Add these entities to the package.xml

        custom_objects = package_xml.find("types", name="CustomObject")

        # Append custom objects if record types are present but missing from package.xml
        record_types = self.options.get("record_types") or []
        rt_objects = {rt["record_type"].split(".")[0] for rt in record_types}
        listed_custom_objects = {c.text for c in custom_objects.findall("members")}

        for rt in rt_objects:
            if rt not in listed_custom_objects:
                self.logger.info('Adding "{}" to package.xml'.format(rt))
                custom_objects.append(
                    "members",
                    text=rt,
                )

    def _transform_entity(self, tree, api_name):
        # Custom applications
        self._set_elements_visible(tree, "applicationVisibilities", "visible")
        # Apex classes
        self._set_elements_visible(tree, "classAccesses", "enabled")
        # Fields
        self._set_elements_visible(tree, "fieldPermissions", "editable")
        self._set_elements_visible(tree, "fieldPermissions", "readable")
        # Visualforce pages
        self._set_elements_visible(tree, "pageAccesses", "enabled")
        # Custom tabs
        self._set_elements_visible(
            tree,
            "tabVisibilities",
            "visibility",
            false_value="Hidden",
            true_value="DefaultOn",
        )
        # Record Types
        self._set_record_types(tree, api_name)

        return tree

    def _set_elements_visible(
        self, tree, outer_tag, inner_tag, false_value="false", true_value="true"
    ):
        for elem in tree.findall(outer_tag, **{inner_tag: false_value}):
            elem.find(inner_tag).text = true_value

    def _set_record_types(self, tree, api_name):
        # Do namespace injection
        record_types = self.options.get("record_types") or []
        for rt in record_types:
            rt["record_type"] = rt["record_type"].format(**self.namespace_prefixes)

        # If defaults are specified, clear any pre-existing defaults
        # that apply to the same object
        defaults = {
            "default": "default",
            "person_account_default": "personAccountDefault",
        }
        objects_with_defaults = defaultdict(set)

        for option, default_element in defaults.items():
            for rt in record_types:
                if option in rt:
                    objects_with_defaults[option].add(rt["record_type"].split(".")[0])

            for elem in tree.findall("recordTypeVisibilities"):
                if (
                    elem.find(default_element)
                    and elem.recordType.text.split(".")[0]
                    in objects_with_defaults[option]
                ):
                    elem.find(default_element).text = "false"

        # Set recordTypeVisibilities
        for rt in record_types:
            # Look for the recordTypeVisibilities element
            elem = tree.find("recordTypeVisibilities", recordType=rt["record_type"])
            if elem is None:
                raise TaskOptionsError(
                    f"Record Type {rt['record_type']} not found in retrieved {api_name}.profile"
                )

            # Set visible
            elem.visible.text = str(rt.get("visible", "true")).lower()

            # Set default
            elem.default.text = str(rt.get("default", "false")).lower()

            # Set person account default if element exists
            pa_default = elem.find("personAccountDefault")
            if pa_default is not None:
                pa_default.text = str(rt.get("person_account_default", "false")).lower()

        # Set page layout defaults for record types
        for rt in record_types:
            # We need it to look like this:
            # <layoutAssignments>
            #   <layout>{page_layout}</layout>
            #   <recordType>{record_type}</recordType>
            # </layoutAssignments>
            layout_option = rt.get("page_layout", None)
            if layout_option:
                # Look for page layout definitions in the record type
                found_layout = False
                for elem in tree.findall("layoutAssignments"):
                    if elem.find("recordType").text == rt["record_type"]:
                        elem.layout.text = layout_option
                        found_layout = True

                if not found_layout:
                    assignment = tree.append(tag="layoutAssignments")
                    assignment.append(tag="recordType", text=rt["record_type"])
                    assignment.append(tag="layout", text=layout_option)


UpdateAdminProfile = UpdateProfile = ProfileGrantAllAccess
