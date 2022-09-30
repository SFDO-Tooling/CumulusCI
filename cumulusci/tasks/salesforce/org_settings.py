import contextlib
import json
import pathlib
import textwrap
from typing import Optional

from cumulusci.core.utils import dictmerge
from cumulusci.tasks.metadata.package import PackageXmlGenerator
from cumulusci.tasks.salesforce import Deploy
from cumulusci.utils import temporary_dir

SETTINGS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<{settingsName} xmlns="http://soap.sforce.com/2006/04/metadata">
{values}
</{settingsName}>"""
ORGPREF = """<preferences>
    <settingName>{name}</settingName>
    <settingValue>{value}</settingValue>
</preferences>"""


class DeployOrgSettings(Deploy):
    task_doc = """Deploys org settings from an sfdx scratch org definition file."""

    task_options = {
        "definition_file": {"description": "sfdx scratch org definition file"},
        "settings": {"description": "A dict of settings to apply"},
        "object_settings": {"description": "A dict of objectSettings to apply"},
        "api_version": {"description": "API version used to deploy the settings"},
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        # We have no need for namespace injection when deploying settings,
        # so let's explicitly disable it to prevent the Deploy task
        # from making API calls to check if it's needed.
        self.options["managed"] = False
        self.options["namespaced_org"] = False

    def _run_task(self):
        settings = {}
        object_settings = {}
        if self.options.get("definition_file"):
            with open(self.options["definition_file"], "r") as f:
                scratch_org_definition = json.load(f)
                settings = scratch_org_definition.get("settings", {})
                object_settings = scratch_org_definition.get("objectSettings", {})

        dictmerge(settings, self.options.get("settings", {}))
        dictmerge(object_settings, self.options.get("object_settings", {}))

        if not settings and not object_settings:
            self.logger.info("No settings provided to deploy.")
            return

        api_version = (
            self.options.get("api_version") or self.org_config.latest_api_version
        )
        with build_settings_package(settings, object_settings, api_version) as path:
            self.options["path"] = path
            return super()._run_task()


def capitalize(s):
    """
    Just capitalize first letter (different from .title, as it preserves
    the rest of the case).
    e.g. accountSettings -> AccountSettings
    """
    return s[0].upper() + s[1:]


@contextlib.contextmanager
def build_settings_package(
    settings: Optional[dict], object_settings: Optional[dict], api_version: str
):
    with temporary_dir() as path:
        if settings:
            pathlib.Path("settings").mkdir()
            for section, section_settings in settings.items():
                settings_name = capitalize(section)
                if section == "orgPreferenceSettings":
                    values = "    " + "\n    ".join(
                        line
                        for line in "\n".join(
                            ORGPREF.format(name=capitalize(k), value=v)
                            for k, v in section_settings.items()
                        ).splitlines()
                    )
                else:
                    values = textwrap.indent(_dict_to_xml(section_settings), "    ")
                # e.g. AccountSettings -> settings/Account.settings
                settings_file = (
                    pathlib.Path("settings")
                    / f"{settings_name[: -len('Settings')]}.settings"
                )
                with open(settings_file, "w", encoding="utf-8") as f:
                    f.write(
                        SETTINGS_XML.format(settingsName=settings_name, values=values)
                    )

        if object_settings:
            pathlib.Path("objects").mkdir()
            for obj_lower_name, this_obj_settings in object_settings.items():
                object_name = capitalize(obj_lower_name)
                file_content = _get_object_file(object_name, this_obj_settings)
                with open(
                    pathlib.Path("objects") / f"{object_name}.object",
                    "w",
                    encoding="utf-8",
                ) as f:
                    f.write(file_content)

        package_generator = PackageXmlGenerator(path, api_version)
        with open("package.xml", "w") as f:
            f.write(package_generator())

        yield path


def _get_object_file(object_name: str, settings: dict) -> str:
    sharing_model = ""
    if "sharingModel" in settings:
        sharing_model = (
            f"    <sharingModel>{capitalize(settings['sharingModel'])}</sharingModel>"
        )

    record_type = ""
    business_process = ""
    if "defaultRecordType" in settings:
        # Use the same default picklist values as SFDX to generate a Business Process,
        # if this object requires one.
        picklist_value = {
            "Case": "New",
            "Lead": "New - Not Contacted",
            "Opportunity": "Prospecting",
            "Solution": "Draft",
        }.get(object_name, "")
        default_status = (
            "<default>true</default>" if object_name == "Opportunity" else ""
        )

        business_process_reference = ""
        if picklist_value:
            # We need to add a Business Process
            business_process_reference = (
                f"<businessProcess>Default{object_name}</businessProcess>"
            )
            default_status = ""
            business_process = f"""    <businessProcesses>
        <fullName>Default{object_name}</fullName>
        <isActive>true</isActive>
        <values>
            <fullName>{picklist_value}</fullName>
            {default_status}
        </values>
    </businessProcesses>"""
        record_type = f"""    <recordTypes>
        <fullName>{capitalize(settings['defaultRecordType'])}</fullName>
        <label>{capitalize(settings['defaultRecordType'])}</label>
        <active>true</active>
        {business_process_reference}
    </recordTypes>
        """

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Object xmlns="http://soap.sforce.com/2006/04/metadata">
{sharing_model}
{record_type}
{business_process}
</Object>"""


def _dict_to_xml(d: dict) -> str:
    items = []
    for k, v in d.items():
        if isinstance(v, dict):
            v = "\n" + textwrap.indent(_dict_to_xml(v), "    ") + "\n"
        elif isinstance(v, str):
            pass
        elif isinstance(v, bool):
            v = str(v).lower()
        elif isinstance(v, list):
            for li in v:
                if not isinstance(li, dict):
                    raise TypeError(f"Unexpected list item type {type(v)} for {k}")
                li_xml = textwrap.indent(_dict_to_xml(li), "    ") + "\n"
                items.append(f"<{k}>\n{li_xml}</{k}>")
            continue
        else:
            raise TypeError(f"Unexpected type {type(v)} for {k}")
        items.append(f"<{k}>{v}</{k}>")
    return "\n".join(items)
