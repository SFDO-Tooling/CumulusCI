from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.utils import process_list_arg
from cumulusci.tasks.metadata_etl import MetadataSingleEntityTransformTask
from cumulusci.utils.xml.metadata_tree import MetadataElement

OBJ_SETTINGS = [
    "Activities",
    "BulkApi",
    "Feeds",
    "History",
    "Licensing",
    "Reports",
    "Search",
    "Sharing",
    "StreamingApi",
]
OBJ_SETTINGS_STR = ", ".join(OBJ_SETTINGS)


class SetObjectSettings(MetadataSingleEntityTransformTask):
    entity = "CustomObject"
    task_options = {
        "enable": {
            "description": f"Array of object settings to enable. Uses the setting name.  Available values: {OBJ_SETTINGS_STR}"
        },
        "disable": {
            "description": f"Array of object settings to disable. Uses the setting name.  Available values: {OBJ_SETTINGS_STR}"
        },
        # Only include api_names option since namespace injection isn't supported
        **{"api_names": MetadataSingleEntityTransformTask.task_options["api_names"]},
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        if not self.options.get("enable") and not self.options.get("disable"):
            raise TaskOptionsError(
                "You must provide values for either 'enable' or 'disable'"
            )
        self.options["enable"] = self._process_settings(self.options.get("enable"))
        self.options["disable"] = self._process_settings(self.options.get("disable"))

    def _process_settings(self, settings):
        settings = process_list_arg(settings)
        if settings is None:
            settings = []
        invalid = []
        for setting in settings:
            if setting not in OBJ_SETTINGS:
                invalid.append(setting)
        if invalid:
            raise TaskOptionsError(
                "Invalid settings: {}.  Valid settings are: ".format(
                    ", ".join(invalid), OBJ_SETTINGS_STR
                )
            )
        return settings

    def _transform_entity(self, metadata: MetadataElement, api_name: str):
        for setting in self.options["enable"]:
            elem = metadata.find("enable" + setting)
            elem.text = "true"
        for setting in self.options["disable"]:
            elem = metadata.find("enable" + setting)
            elem.text = "false"
        return metadata
