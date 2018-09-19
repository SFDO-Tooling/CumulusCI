import os
import shutil
import tempfile

from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.salesforce import Deploy
from cumulusci.utils import CUMULUSCI_PATH
from cumulusci.utils import elementtree_parse_file
from cumulusci.utils import findReplace
from cumulusci.utils import findReplaceRegex


class UpdateAdminProfile(Deploy):
    name = "UpdateAdminProfile"

    task_options = {
        "package_xml": {
            "description": "Override the default package.xml file for retrieving the Admin.profile and all objects and classes that need to be included by providing a path to your custom package.xml"
        },
        "record_types": {
            "description": "A list of dictionaries containing the required key `record_type` with a value specifying the record type in format <object>.<developer_name>.  Record type names can use the token strings {managed} and {namespaced_org} for namespace prefix injection as needed.  By default, all listed record types will be set to visible and not default.  Use the additional keys `visible`, `default`, and `person_account_default` set to true/false to override.  NOTE: Setting record_types is only supported in cumulusci.yml, command line override is not supported."
        },
        "managed": {
            "description": "If True, uses the namespace prefix where appropriate.  Use if running against an org with the managed package installed.  Defaults to False"
        },
        "namespaced_org": {
            "description": "If True, attempts to prefix all unmanaged metadata references with the namespace prefix for deployment to the packaging org or a namespaced scratch org.  Defaults to False"
        },
    }

    namespaces = {"sf": "http://soap.sforce.com/2006/04/metadata"}

    def _init_options(self, kwargs):
        super(UpdateAdminProfile, self)._init_options(kwargs)

        if "package_xml" not in self.options:
            self.options["package_xml"] = os.path.join(
                CUMULUSCI_PATH, "cumulusci", "files", "admin_profile.xml"
            )

        self.options["managed"] = process_bool_arg(self.options.get("managed", False))

        self.options["namespaced_org"] = process_bool_arg(
            self.options.get("namespaced_org", False)
        )

        # For namespaced orgs, managed should always be True
        if self.options["namespaced_org"]:
            self.options["managed"] = True

        # Set up namespace prefix strings
        namespace_prefix = "{}__".format(
            self.project_config.project__package__namespace
        )
        self.namespace_prefixes = {
            "managed": namespace_prefix if self.options["managed"] else "",
            "namespaced_org": namespace_prefix
            if self.options["namespaced_org"]
            else "",
        }

        # Read in the package.xml file
        self.options["package_xml_path"] = self.options["package_xml"]
        with open(self.options["package_xml_path"], "r") as f:
            self.options["package_xml"] = f.read()

    def _run_task(self):
        self.tempdir = tempfile.mkdtemp()
        self._retrieve_unpackaged()
        self._process_metadata()
        self._deploy_metadata()
        shutil.rmtree(self.tempdir)

    def _retrieve_unpackaged(self):
        self.logger.info(
            "Retrieving metadata using {}".format(self.options["package_xml_path"])
        )
        api_retrieve = ApiRetrieveUnpackaged(
            self,
            self.options.get("package_xml"),
            self.project_config.project__package__api_version,
        )
        unpackaged = api_retrieve()
        unpackaged.extractall(self.tempdir)

    def _process_metadata(self):
        self.logger.info("Processing retrieved metadata in {}".format(self.tempdir))
        path = os.path.join(self.tempdir, "profiles", "Admin.profile")
        self.tree = elementtree_parse_file(path)

        self._set_apps_visible()
        self._set_classes_enabled()
        self._set_fields_editable()
        self._set_fields_readable()
        self._set_pages_enabled()
        self._set_tabs_visibility()
        self._set_record_types()

        self.tree.write(
            path, "utf-8", xml_declaration=True, default_namespace=self.namespaces["sf"]
        )

    def _set_apps_visible(self):
        xpath = ".//sf:applicationVisibilities[sf:visible='false']"
        for elem in self.tree.findall(xpath, self.namespaces):
            elem.find("sf:visible", self.namespaces).text = "true"

    def _set_classes_enabled(self):
        xpath = ".//sf:classAccess[sf:enabled='false']"
        for elem in self.tree.findall(xpath, self.namespaces):
            elem.find("sf:enabled", self.namespaces).text = "true"

    def _set_fields_editable(self):
        xpath = ".//sf:fieldPermissions[sf:editable='false']"
        for elem in self.tree.findall(xpath, self.namespaces):
            elem.find("sf:editable", self.namespaces).text = "true"

    def _set_fields_readable(self):
        xpath = ".//sf:fieldPermissions[sf:readable='false']"
        for elem in self.tree.findall(xpath, self.namespaces):
            elem.find("sf:readable", self.namespaces).text = "true"

    def _set_pages_enabled(self):
        xpath = ".//sf:pageAccesses[sf:enabled='false']"
        for elem in self.tree.findall(xpath, self.namespaces):
            elem.find("sf:enabled", self.namespaces).text = "true"

    def _set_record_types(self):
        record_types = self.options.get("record_types") or []

        # If defaults are specified,
        # clear any pre-existing defaults
        if any("default" in rt for rt in record_types):
            for default in ("sf:default", "sf:personAccountDefault"):
                xpath = ".//sf:recordTypeVisibilities/{}".format(default)
                for elem in self.tree.findall(xpath, self.namespaces):
                    elem.text = "false"

        # Set recordTypeVisibilities
        for rt in record_types:
            # Replace namespace prefix tokens in rt name
            rt_prefixed = rt["record_type"].format(**self.namespace_prefixes)

            # Look for the recordTypeVisiblities element
            xpath = ".//sf:recordTypeVisibilities[sf:recordType='{}']".format(
                rt_prefixed
            )
            elem = self.tree.find(xpath, self.namespaces)
            if elem is None:
                raise TaskOptionsError(
                    "Record Type {} not found in retrieved Admin.profile".format(
                        rt["record_type"]
                    )
                )

            # Set visibile
            elem.find("sf:visible", self.namespaces).text = str(
                rt.get("visible", "true")
            ).lower()

            # Set default
            elem.find("sf:default", self.namespaces).text = str(
                rt.get("default", "false")
            ).lower()

            # Set person account default if element exists
            pa_default = elem.find("sf:personAccountDefault", self.namespaces)
            if pa_default is not None:
                pa_default.text = str(rt.get("person_account_default", "false")).lower()

    def _set_tabs_visibility(self):
        xpath = ".//sf:tabVisibilities[sf:visibility='Hidden']"
        for elem in self.tree.findall(xpath, self.namespaces):
            elem.find("sf:visibility", self.namespaces).text = "DefaultOn"

    def _deploy_metadata(self):
        self.logger.info("Deploying updated Admin.profile from {}".format(self.tempdir))
        api = self._get_api(path=self.tempdir)
        return api()
