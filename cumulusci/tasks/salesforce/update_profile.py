import os

import pkg_resources

from cumulusci.tasks.metadata_etl import (
    MetadataOperation,
    MetadataSingleEntityTransformTask,
)

from cumulusci.core.exceptions import TaskOptionsError, CumulusCIException
from cumulusci.core.utils import process_bool_arg, process_list_arg
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
            "true/false to override.  NOTE: Setting record_types is only supported in cumulusci.yml, command line override is not supported."
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

        self.options["managed"] = process_bool_arg(self.options.get("managed", False))

        self.options["namespaced_org"] = process_bool_arg(
            self.options.get("namespaced_org", False)
        )

        # For namespaced orgs, managed should always be True
        if self.options["namespaced_org"]:
            self.options["managed"] = True

        self.options["namespace_inject"] = self.options.get(
            "namespace_inject", self.project_config.project__package__namespace
        )

        # Set up namespace prefix strings
        namespace_prefix = "{}__".format(self.options["namespace_inject"])
        self.namespace_prefixes = {
            "managed": namespace_prefix if self.options["managed"] else "",
            "namespaced_org": namespace_prefix
            if self.options["namespaced_org"]
            else "",
        }

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
        # If we're using a custom package.xml, Profiles to alter should be
        # specified there.
        self.api_names = set(process_list_arg(self.options.get("api_names", [])))
        if "package_xml" in self.options:
            if self.api_names or "profile_name" in self.options:
                raise TaskOptionsError(
                    "The package_xml option is not compatible with the profile_name or api_names options. "
                    "Specify desired profiles in the custom package.xml"
                )

            # Infer items to affect from what is retrieved.
            self.api_names = {"*"}
            self.package_xml_path = self.options["package_xml"]
        else:
            if "profile_name" in self.options:
                self.api_names.add(self.options["profile_name"])

            if not self.api_names:
                self.api_names.add("Admin")

            if self.options["namespaced_org"]:
                # Namespaced orgs don't use the explicit namespace references in `package.xml`.
                # Preserving historic behavior but guarding here
                self.options["managed"] = False

            self.api_names = {self._inject_namespace(x) for x in self.api_names}

            if self.options["namespaced_org"]:
                self.options["managed"] = True

            self.package_xml_path = os.path.join(
                CUMULUSCI_PATH, "cumulusci", "files", "admin_profile.xml"
            )

    def freeze(self, step):
        # Preserve behavior from when we subclassed Deploy.

        steps = super().freeze(step)
        for step in steps:
            if step["kind"] == "other":
                step["kind"] = "metadata"
        return steps

    def _generate_package_xml(self, operation):
        if operation is MetadataOperation.RETRIEVE:
            with open(self.package_xml_path, "r") as f:
                package_xml_content = f.read()

            package_xml_content = package_xml_content.format(**self.namespace_prefixes)

            if (
                self.options["include_packaged_objects"]
                or "package_xml" not in self.options
            ):
                # We need to rewrite the package.xml for one or two reasons.
                # Either we are using packaged-object expansion, or we're using
                # the built-in admin_profile.xml and need to substitute in
                # profile API names.

                # Convert to bytes because stored `package.xml`s typically have an encoding declaration,
                # which `fromstring()` doesn't like.
                package_xml = metadata_tree.fromstring(
                    package_xml_content.encode("utf-8")
                )

                if self.options["include_packaged_objects"]:
                    self._expand_package_xml(package_xml)
                if "package_xml" not in self.options:
                    self._expand_profile_members(package_xml)

                package_xml_content = package_xml.tostring(xml_declaration=True)

            return package_xml_content
        else:
            return super()._generate_package_xml(operation)

    def _expand_profile_members(self, package_xml):
        profile_names = package_xml.find("types", name="Profile")
        if not profile_names:
            raise CumulusCIException(
                "The package.xml does not contain a Profiles member."
            )
        for profile in self.api_names:
            profile_names.append("members", text=profile)

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
        record_types = self.options.get("record_types") or []

        # If defaults are specified,
        # clear any pre-existing defaults
        if any("default" in rt for rt in record_types):
            for default in ("default", "personAccountDefault"):
                for elem in tree.findall("recordTypeVisibilities"):
                    if elem.find(default):
                        elem.find(default).text = "false"

        # Set recordTypeVisibilities
        for rt in record_types:
            # Replace namespace prefix tokens in rt name
            rt_prefixed = rt["record_type"].format(**self.namespace_prefixes)

            # Look for the recordTypeVisiblities element
            elem = tree.find("recordTypeVisibilities", recordType=rt_prefixed)
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


UpdateAdminProfile = UpdateProfile = ProfileGrantAllAccess
