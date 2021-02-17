import contextlib
import json
import os
import textwrap

from cumulusci.tasks.salesforce import Deploy
from cumulusci.utils import temporary_dir
from cumulusci.core.utils import dictmerge


SETTINGS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<{settingsName} xmlns="http://soap.sforce.com/2006/04/metadata">
{values}
</{settingsName}>"""
ORGPREF = """<preferences>
    <settingName>{name}</settingName>
    <settingValue>{value}</settingValue>
</preferences>"""
PACKAGE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>*</members>
        <name>Settings</name>
    </types>
    <version>{api_version}</version>
</Package>"""


class DeployOrgSettings(Deploy):
    task_doc = """Deploys org settings from an sfdx scratch org definition file."""

    task_options = {
        "definition_file": {"description": "sfdx scratch org definition file"},
        "settings": {"description": "A dict of settings to apply"},
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
        if self.options.get("definition_file"):
            with open(self.options["definition_file"], "r") as f:
                scratch_org_definition = json.load(f)
                settings = scratch_org_definition.get("settings", {})

        dictmerge(settings, self.options.get("settings", {}))

        if not settings:
            self.logger.info("No settings provided to deploy.")
            return

        api_version = (
            self.options.get("api_version") or self.org_config.latest_api_version
        )
        with build_settings_package(settings, api_version) as path:
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
def build_settings_package(settings: dict, api_version: str):
    with temporary_dir() as path:
        os.mkdir("settings")
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
            settings_file = os.path.join(
                "settings", settings_name[: -len("Settings")] + ".settings"
            )
            with open(settings_file, "w") as f:
                f.write(SETTINGS_XML.format(settingsName=settings_name, values=values))
        with open("package.xml", "w") as f:
            f.write(PACKAGE_XML.format(api_version=api_version))

        yield path


def _dict_to_xml(d: dict) -> str:
    items = []
    for k, v in d.items():
        if isinstance(v, dict):
            v = "\n" + textwrap.indent(_dict_to_xml(v), "    ") + "\n"
        elif isinstance(v, str):
            pass
        elif isinstance(v, bool):
            v = str(v).lower()
        else:
            raise TypeError(f"Unexpected type {type(v)} for {k}")
        items.append(f"<{k}>{v}</{k}>")
    return "\n".join(items)
