import os
import shutil
import tempfile

from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.salesforce import Deploy
from cumulusci.utils import CUMULUSCI_PATH
from cumulusci.utils import findReplace
from cumulusci.utils import findReplaceRegex

rt_visibility_template = """
<recordTypeVisibilities>
    <default>{default}</default>
    <recordType>{record_type}</recordType>
    <visible>{visible}</visible>
    <personAccountDefault>{person_account_default}</personAccountDefault>
</recordTypeVisibilities>
"""


class UpdateAdminProfile(Deploy):
    name = "UpdateAdminProfile"

    task_options = {
        "package_xml": {
            "description": "Override the default package.xml file for retrieving the Admin.profile and all objects and classes that need to be included by providing a path to your custom package.xml",
        },
        "record_types": {
            "description": "A list of dictionaries containing the required key `record_type` with a value specifying the record type in format <object>.<developer_name>.  Record type names can use the token strings {managed} and {namespaced_org} for namespace prefix injection as needed.  By default, all listed record types will be set to visible and not default.  Use the additional keys `visible`, `default`, and `person_account_default` set to true/false to override.  NOTE: Setting record_types is only supported in cumulusci.yml, command line override is not supported.",
        },
        "managed": {
            "description": "If True, uses the namespace prefix where appropriate.  Use if running against an org with the managed package installed.  Defaults to False",
        },
        "namespaced_org": {
            "description": "If True, attempts to prefix all unmanaged metadata references with the namespace prefix for deployment to the packaging org or a namespaced scratch org.  Defaults to False",
        },
    }

    def _init_options(self, kwargs):
        super(UpdateAdminProfile, self)._init_options(kwargs)

        if "package_xml" not in self.options:
            self.options["package_xml"] = os.path.join(
                CUMULUSCI_PATH, "cumulusci", "files", "admin_profile.xml"
            )

        self.options['managed'] = process_bool_arg(
            self.options.get('managed', False)
        )

        self.options['namespaced_org'] = process_bool_arg(
            self.options.get('namespaced_org', False)
        )

        # For namespaced orgs, managed should always be True
        if self.options['namespaced_org']:
            self.options['managed'] = True

        # Set up namespace prefix strings
        namespace_prefix = '{}__'.format(self.project_config.project__package__namespace)
        self.namespace_prefixes = {
            'managed': namespace_prefix if self.options['managed'] else '',
            'namespaced_org': namespace_prefix if self.options['namespaced_org'] else '',
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
        self._set_apps_visible()
        self._set_fields_editable()
        self._set_fields_readable()
        self._set_tabs_visibility()
        self._set_record_types()

    def _set_apps_visible(self):
        findReplace(
            "<visible>false</visible>",
            "<visible>true</visible>",
            os.path.join(self.tempdir, "profiles"),
            "Admin.profile",
        )

    def _set_fields_editable(self):
        findReplace(
            "<editable>false</editable>",
            "<editable>true</editable>",
            os.path.join(self.tempdir, "profiles"),
            "Admin.profile",
        )

    def _set_fields_readable(self):
        findReplace(
            "<readable>false</readable>",
            "<readable>true</readable>",
            os.path.join(self.tempdir, "profiles"),
            "Admin.profile",
        )

    def _set_record_types(self):
        record_types = self.options.get('record_types')
        if not record_types:
            return

        # Strip recordTypeVisibilities
        findReplaceRegex(
            '<recordTypeVisibilities>([^\$]+)</recordTypeVisibilities>',
            '',
            os.path.join(self.tempdir, 'profiles'),
            'Admin.profile'
        )

        # Set recordTypeVisibilities
        for rt in record_types:
            rt_prefixed = rt['record_type'].format(**self.namespace_prefixes)
            rt_xml = rt_visibility_template.format(**{
                "default": rt.get("default", "false"),
                "record_type": rt_prefixed,
                "visible": rt.get("visible", "true"),
                "person_account_default": rt.get("personAccountDefault", "false"),
            })
            findReplace(
                "<tabVisibilities>",
                "{}<tabVisibilities>".format(rt_xml),
                os.path.join(self.tempdir, "profiles"),
                "Admin.profile",
                max=1,
            )

    def _set_tabs_visibility(self):
        findReplace(
            "<visibility>Hidden</visibility>",
            "<visibility>DefaultOn</visibility>",
            os.path.join(self.tempdir, "profiles"),
            "Admin.profile",
        )

    def _deploy_metadata(self):
        self.logger.info("Deploying updated Admin.profile from {}".format(self.tempdir))
        api = self._get_api(path=self.tempdir)
        return api()
