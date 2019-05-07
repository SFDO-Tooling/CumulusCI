from collections import defaultdict
import json
import os
import re
import xmltodict

from cumulusci.core.utils import process_bool_arg
from cumulusci.core.utils import process_list_arg
from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.tasks.salesforce import BaseRetrieveMetadata
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.tasks.metadata.package import PackageXmlGenerator
from cumulusci.tasks.metadata.package import __location__


class ListChanges(BaseSalesforceApiTask):

    task_options = {
        "include": {"description": "Include changed components matching this string."},
        "exclude": {"description": "Exclude changed components matching this string."},
        "exclude_namespace": {"description": "Namespaces that should be excluded."},
        "snapshot": {
            "description": "If True, all matching items will be set to be ignored at their current revision number.  This will exclude them from the results unless a new edit is made."
        },
    }

    def _init_options(self, kwargs):
        super(ListChanges, self)._init_options(kwargs)
        self.options["include"] = process_list_arg(self.options.get("include", []))
        self.options["exclude"] = process_list_arg(self.options.get("exclude", []))
        self.options["reset_status"] = process_bool_arg(
            self.options.get("reset_status", [])
        )
        self.options["snapshot"] = process_bool_arg(self.options.get("snapshot", []))
        self.options["exclude_namespace"] = process_list_arg(
            self.options.get("exclude_namespace", [])
        )
        self._exclude = self.options.get("exclude", [])
        for namespace in self.options["exclude_namespace"]:
            self._exclude.append("CustomField: .*\.{}__.*__c".format(namespace))
            self._exclude.append("CompactLayout: .*\.{}__.*__c".format(namespace))
        if self.project_config.project__source__ignore:
            self._exclude.extend(self.project_config.project__source__ignore)

        self._load_snapshot()

    @property
    def _snapshot_path(self):
        parent_dir = os.path.join(".cci", "snapshot")
        if not os.path.isdir(parent_dir):
            os.makedirs(parent_dir)
        return os.path.join(parent_dir, "{}.json".format(self.org_config.name))

    def _load_snapshot(self):
        self._snapshot = {}
        if os.path.isfile(self._snapshot_path):
            with open(self._snapshot_path, "r") as f:
                self._snapshot = json.load(f)

    def _get_changes(self):
        changes = self.tooling.query(
            "SELECT MemberName, MemberType, RevisionNum FROM SourceMember WHERE IsNameObsolete=false"
        )
        return changes

    def _store_snapshot(self):
        with open(self._snapshot_path, "w") as f:
            f.write(json.dumps(self._snapshot))

    def _run_task(self):
        changes = self._get_changes()
        if changes["totalSize"]:
            self.logger.info(
                "Found {} changed components in the scratch org:".format(
                    changes["totalSize"]
                )
            )

        filtered = self._filter_changes(changes)
        for change in filtered:
            self.logger.info("{MemberType}: {MemberName}".format(**change))
        if not filtered:
            self.logger.info("Found no changes.")

        ignored = len(changes["records"]) - len(filtered)
        if ignored:
            self.logger.info(
                "Ignored {} changed components in the scratch org:".format(ignored)
            )

        if self.options["snapshot"]:
            self.logger.info("Storing snapshot of changes")
            self._store_snapshot()

    def _filter_changes(self, changes):
        filtered = []
        for change in changes["records"]:
            mdtype = change["MemberType"]
            name = change["MemberName"]
            full_name = "{}: {}".format(mdtype, name)
            if self.options["include"] and not any(
                re.search(s, full_name) for s in self.options["include"]
            ):
                continue
            if any(re.search(s, full_name) for s in self._exclude):
                continue
            revnum = self._snapshot.get(mdtype, {}).get(name)
            if revnum and revnum == change["RevisionNum"]:
                continue
            filtered.append(change)

            self._snapshot.setdefault(mdtype, {})[name] = change["RevisionNum"]

        return filtered


retrieve_changes_task_options = ListChanges.task_options.copy()
retrieve_changes_task_options["path"] = {
    "description": "The path to write the retrieved metadata",
    "required": True,
}
retrieve_changes_task_options["api_version"] = {
    "description": (
        "Override the default api version for the retrieve."
        + " Defaults to project__package__api_version"
    )
}
retrieve_changes_task_options["namespace_tokenize"] = BaseRetrieveMetadata.task_options[
    "namespace_tokenize"
]


class RetrieveChanges(BaseRetrieveMetadata, ListChanges, BaseSalesforceApiTask):
    api_class = ApiRetrieveUnpackaged

    task_options = retrieve_changes_task_options

    def _init_options(self, kwargs):
        super(RetrieveChanges, self)._init_options(kwargs)

        if "api_version" not in self.options:
            self.options[
                "api_version"
            ] = self.project_config.project__package__api_version

    def _get_api(self):
        self.logger.info("Querying Salesforce for changed source members")
        changes = self.tooling.query(
            "SELECT MemberName, MemberType, RevisionNum FROM SourceMember WHERE IsNameObsolete=false"
        )

        type_members = defaultdict(list)
        filtered = self._filter_changes(changes)
        if not filtered:
            self.logger.info("No changes to retrieve")
            return

        for change in filtered:
            type_members[change["MemberType"]].append(change["MemberName"])
            self.logger.info("{MemberType}: {MemberName}".format(**change))

        package_xml_path = os.path.join(self.options["path"], "package.xml")
        if os.path.isfile(package_xml_path):
            with open(package_xml_path, "rb") as f:
                current_package_xml = xmltodict.parse(f)
        else:
            current_package_xml = {"Package": {}}
        merged_type_members = {}
        for mdtype in current_package_xml["Package"].get("types", []):

            if "members" not in mdtype:
                continue

            if isinstance(mdtype, str):
                type_name = mdtype
                items = current_package_xml["Package"]["types"][type_name]
            else:
                type_name = mdtype["name"]
                items = mdtype["members"]

            members = []
            if isinstance(items, str):
                members.append(items)
            else:
                for item in items:
                    members.append(item)
            if members:
                merged_type_members[type_name] = members

        types = []
        for name, members in type_members.items():
            if name in merged_type_members:
                merged_type_members[name].extend(members)
            else:
                merged_type_members[name] = members

        for name, members in type_members.items():
            types.append(MetadataType(name, members))
        package_xml = PackageXmlGenerator(self.options["api_version"], types=types)()

        return self.api_class(self, package_xml, self.options.get("api_version"))

    def _run_task(self):
        super(RetrieveChanges, self)._run_task()

        # update package.xml
        package_xml_opts = {
            "directory": self.options["path"],
            "api_version": self.options["api_version"],
        }
        if self.options["path"] == "src":
            package_xml_opts[
                "package_name"
            ] = self.project_config.project__package__name
        package_xml = PackageXmlGenerator(**package_xml_opts)()
        with open(os.path.join(self.options["path"], "package.xml"), "w") as f:
            f.write(package_xml)

        self._store_snapshot()


class MetadataType(object):
    def __init__(self, name, members):
        self.metadata_type = name
        self.members = members

    def __call__(self):
        members = ["<members>{}</members>".format(member) for member in self.members]
        return """<types>
    {}
    <name>{}</name>
</types>""".format(
            members, self.metadata_type
        )
