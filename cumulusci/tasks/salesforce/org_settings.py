import contextlib
import json
import os

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
        with open(self.options["definition_file"], "r") as f:
            scratch_org_definition = json.load(f)

        settings = scratch_org_definition.get("settings", {})
        if not settings:
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
                values = "\n    ".join(
                    line
                    for line in "\n".join(
                        ORGPREF.format(name=capitalize(k), value=v)
                        for k, v in section_settings.items()
                    ).splitlines()
                )
            else:
                values = "\n    ".join(
                    f"<{k}>{v}</{k}>" for k, v in section_settings.items()
                )
            # e.g. AccountSettings -> settings/Account.settings
            settings_file = os.path.join(
                "settings", settings_name[: -len("Settings")] + ".settings"
            )
            with open(settings_file, "w") as f:
                f.write(SETTINGS_XML.format(settingsName=settings_name, values=values))
        with open("package.xml", "w") as f:
            f.write(PACKAGE_XML.format(api_version=api_version))

        yield path
