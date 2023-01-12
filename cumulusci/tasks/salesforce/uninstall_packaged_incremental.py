from pathlib import Path

import xmltodict

from cumulusci.core.exceptions import CumulusCIException
from cumulusci.tasks.salesforce import UninstallPackaged
from cumulusci.utils import package_xml_from_dict, temporary_dir

DEFAULT_IGNORE_TYPES = ["RecordType", "CustomObjectTranslation"]


class UninstallPackagedIncremental(UninstallPackaged):
    name = "UninstallPackagedIncremental"
    task_options = {
        "path": {
            "description": "The local path to compare to the retrieved packaged metadata from the org.  Defaults to src.",
            "required": True,
        },
        "package": {
            "description": "The package name to uninstall.  All metadata from the package will be retrieved and a custom destructiveChanges.xml package will be constructed and deployed to delete all deleteable metadata from the package.  Defaults to project__package__name.",
            "required": True,
        },
        "purge_on_delete": {
            "description": "Sets the purgeOnDelete option for the deployment.  Defaults to True.",
            "required": True,
        },
        "ignore": {
            "description": "Components to ignore in the org and not try to delete. Mapping of component type to a list of member names."
        },
        "ignore_types": {
            "description": f"List of component types to ignore in the org and not try to delete. Defaults to {DEFAULT_IGNORE_TYPES}."
        },
        "dry_run": {
            "description": "Perform a dry run of the operation without actually deleting any components, and display the components that would be deleted."
        },
    }

    def _init_options(self, kwargs):
        super(UninstallPackagedIncremental, self)._init_options(kwargs)
        if "path" not in self.options:
            self.options["path"] = "src"
        self.options["ignore"] = self.options.get("ignore", {})
        self.options["ignore_types"] = self.options.get(
            "ignore_types", DEFAULT_IGNORE_TYPES
        )

    def _get_destructive_changes(self, path=None):
        path = path or self.options["path"]
        package_path = Path(path).absolute() / "package.xml"
        if not package_path.is_file():
            raise CumulusCIException(
                "Either you are missing your package.xml file or this "
                "is not a Metadata API format project. You will need to "
                "create a package.xml file or convert your source first "
                "before you can run uninstall_packaged_incremental."
            )

        self.logger.info(
            f"Retrieving metadata in package {self.options['package']} from target org"
        )
        packaged = self._retrieve_packaged()
        with temporary_dir() as tempdir:
            packaged.extractall(tempdir)
            destructive_changes = self._package_xml_diff(
                package_path, Path(tempdir) / "package.xml"
            )

        self.logger.info(
            "Deleting metadata in package {} from target org".format(
                self.options["package"]
            )
            if destructive_changes
            else "No metadata found to delete"
        )
        return destructive_changes

    def _package_xml_diff(self, baseline, compare):
        with open(baseline, "rb") as f:
            baseline_xml = xmltodict.parse(f)
        with open(compare, "rb") as f:
            compare_xml = xmltodict.parse(f)

        delete = {}

        ignore = self.options["ignore"]
        baseline_items = {}
        compare_items = {}
        md_types = baseline_xml["Package"].get("types", [])
        md_types = [md_types] if not isinstance(md_types, list) else md_types
        for md_type in md_types:
            baseline_items[md_type["name"]] = []
            if "members" not in md_type:
                continue
            if isinstance(md_type["members"], str):
                baseline_items[md_type["name"]].append(md_type["members"])
            else:
                baseline_items[md_type["name"]].extend(md_type["members"])

        md_types = compare_xml["Package"].get("types", [])
        md_types = [md_types] if not isinstance(md_types, list) else md_types
        for md_type in md_types:
            compare_items[md_type["name"]] = []
            if "members" not in md_type:
                continue
            if isinstance(md_type["members"], str):
                md_type["members"] = [md_type["members"]]
            for item in md_type["members"]:
                if item in ignore.get(md_type["name"], []):
                    continue
                compare_items[md_type["name"]].append(item)

        for md_type, members in compare_items.items():
            if md_type not in baseline_items:
                delete[md_type] = members
                continue

            for member in members:
                if member not in baseline_items[md_type]:
                    if md_type not in delete:
                        delete[md_type] = []
                    delete[md_type].append(member)

        if delete:
            self.logger.info("Deleting metadata:")
            for skip_type in self.options["ignore_types"]:
                delete.pop(skip_type, None)
            for md_type, members in delete.items():
                for member in members:
                    self.logger.info("    {}: {}".format(md_type, member))
            destructive_changes = self._render_xml_from_items_dict(delete)
            return destructive_changes

    def _render_xml_from_items_dict(self, items):
        return package_xml_from_dict(
            items, api_version=self.project_config.project__package__api_version
        )
