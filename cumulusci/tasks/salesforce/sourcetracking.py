from collections import defaultdict
import contextlib
import json
import os
import re
import time

from cumulusci.core.utils import process_bool_arg
from cumulusci.core.utils import process_list_arg
from cumulusci.tasks.salesforce import BaseRetrieveMetadata
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.tasks.metadata.package import PackageXmlGenerator
from cumulusci.utils import temporary_dir
from cumulusci.core.sfdx import sfdx


class ListChanges(BaseSalesforceApiTask):

    task_options = {
        "include": {"description": "Include changed components matching this string."},
        "exclude": {"description": "Exclude changed components matching this string."},
        "snapshot": {
            "description": "If True, all matching items will be set to be ignored at their current revision number.  This will exclude them from the results unless a new edit is made."
        },
    }

    def _init_options(self, kwargs):
        super(ListChanges, self)._init_options(kwargs)
        self.options["include"] = process_list_arg(self.options.get("include", []))
        self.options["exclude"] = process_list_arg(self.options.get("exclude", []))
        self.options["snapshot"] = process_bool_arg(self.options.get("snapshot", False))
        self._exclude = self.options.get("exclude", [])
        self._exclude.extend(self.project_config.project__source__ignore or [])
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
        changes = self.tooling.query_all(
            "SELECT MemberName, MemberType, RevisionNum FROM SourceMember "
            "WHERE IsNameObsolete=false"
        )
        return changes

    def _store_snapshot(self):
        with open(self._snapshot_path, "w") as f:
            json.dump(self._snapshot, f)

    def _run_task(self):
        changes = self._get_changes()
        if changes["totalSize"]:
            self.logger.info(
                "Found {} changed components in the scratch org.".format(
                    changes["totalSize"]
                )
            )
        else:
            self.logger.info("Found no changes.")

        filtered = self._filter_changes(changes)
        ignored = len(changes["records"]) - len(filtered)
        if ignored:
            self.logger.info(
                "Ignored {} changed components in the scratch org.".format(ignored)
            )
            self.logger.info(
                "{} remaining changes after filtering.".format(len(filtered))
            )

        for change in filtered:
            self.logger.info("{MemberType}: {MemberName}".format(**change))

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
            server_revnum = change["RevisionNum"] or -1
            if revnum and revnum == server_revnum:
                continue
            filtered.append(change)

            self._snapshot.setdefault(mdtype, {})[name] = server_revnum

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


class RetrieveChanges(ListChanges, BaseSalesforceApiTask):
    task_options = retrieve_changes_task_options

    def _init_options(self, kwargs):
        super(RetrieveChanges, self)._init_options(kwargs)
        self.options["snapshot"] = process_bool_arg(kwargs.get("snapshot", True))

        # XXX set default path to src for mdapi format,
        # or the default package directory from sfdx-project.json for dx format

        if "api_version" not in self.options:
            self.options[
                "api_version"
            ] = self.project_config.project__package__api_version

    def _run_task(self):
        self.logger.info("Querying Salesforce for changed source members")
        changes = self._filter_changes(self._get_changes())
        if not changes:
            self.logger.info("No changes to retrieve")
            return

        # Determine whether we're retrieving sfdx format based on
        # whether the directory is in packageDirectories in sfdx-project.json
        md_format = True
        if os.path.exists("sfdx-project.json"):
            with open("sfdx-project.json", "r") as f:
                sfdx_project = json.load(f)
                if "packageDirectories" in sfdx_project and any(
                    d["path"] == self.options["path"]
                    for d in sfdx_project["packageDirectories"]
                ):
                    md_format = False
        target = os.path.realpath(self.options["path"])

        with contextlib.ExitStack() as stack:
            # Temporarily convert metadata format to DX format
            if md_format:
                stack.enter_context(temporary_dir())
                os.mkdir("target")
                # We need to create sfdx-project.json
                # so that sfdx will recognize force-app as a package directory.
                with open("sfdx-project.json", "w") as f:
                    json.dump(
                        {
                            "packageDirectories": [
                                {"path": "force-app", "default": True}
                            ]
                        },
                        f,
                    )
                sfdx(
                    "force:mdapi:convert",
                    log_note="Converting to DX format",
                    args=["-r", target, "-d", "force-app"],
                    capture_output=False,
                    check_return=True,
                )

            # Construct package.xml with components to retrieve, in its own tempdir
            package_xml_path = stack.enter_context(temporary_dir(chdir=False))
            self._write_manifest(changes, path=package_xml_path)

            # Retrieve specified components in DX format
            sfdx(
                "force:source:retrieve",
                access_token=self.org_config.access_token,
                log_note="Retrieving components",
                args=[
                    "-a",
                    str(self.options["api_version"]),
                    "-x",
                    os.path.join(package_xml_path, "package.xml"),
                    "-w",
                    "5",
                ],
                capture_output=False,
                check_return=True,
                env={"SFDX_INSTANCE_URL": self.org_config.instance_url},
            )

            # Convert back to metadata format
            if md_format:
                args = ["-r", "force-app", "-d", target]
                if (
                    self.options["path"] == "src"
                    and self.project_config.project__package__name
                ):
                    args += ["-n", self.project_config.project__package__name]
                sfdx(
                    "force:source:convert",
                    log_note="Converting back to metadata format",
                    args=args,
                    capture_output=False,
                    check_return=True,
                )
                # XXX regenerate package.xml, just to avoid reformatting?

            # XXX namespace tokenization?

        if self.options["snapshot"]:
            self.logger.info("Storing snapshot of changes")
            self._store_snapshot()

    def _write_manifest(self, changes, path):
        type_members = defaultdict(list)
        for change in changes:
            type_members[change["MemberType"]].append(change["MemberName"])
            self.logger.info("{MemberType}: {MemberName}".format(**change))

        generator = PackageXmlGenerator(
            ".",
            self.options["api_version"],
            types=[
                MetadataType(name, members) for name, members in type_members.items()
            ],
        )
        package_xml = generator()
        with open(os.path.join(path, "package.xml"), "w") as f:
            f.write(package_xml)


class SnapshotChanges(ListChanges):

    task_options = {}
    api_version = "45.0"

    def _init_options(self, options):
        pass

    def _run_task(self):
        if self.org_config.scratch:
            self._load_snapshot()

            changes = self._get_changes()
            if not changes["records"]:
                # Try again if source tracking hasn't updated
                time.sleep(5)
                changes = self._get_changes()

            if changes["records"]:
                for change in changes["records"]:
                    mdtype = change["MemberType"]
                    name = change["MemberName"]
                    self._snapshot.setdefault(mdtype, {})[name] = (
                        change["RevisionNum"] or -1
                    )
                self._store_snapshot()

                maxrevision = max(
                    change["RevisionNum"] or -1 for change in changes["records"]
                )
                self.logger.info(
                    "Setting source tracking max revision to {}".format(maxrevision)
                )

                if maxrevision != -1:
                    self._store_maxrevision(maxrevision)

    def _store_maxrevision(self, value):
        with open(self._maxrevision_path, "w") as f:
            json.dump(value, f)

    @property
    def _maxrevision_path(self):
        parent_dir = os.path.join(".sfdx", "orgs", self.org_config.username)
        if not os.path.isdir(parent_dir):
            os.makedirs(parent_dir)
        return os.path.join(parent_dir, "maxrevision.json")

    def freeze(self, step):
        return []


class MetadataType(object):
    def __init__(self, name, members):
        self.metadata_type = name
        self.members = members

    def __call__(self):
        return (
            ["    <types>"]
            + [
                "        <members>{}</members>".format(member)
                for member in self.members
            ]
            + ["        <name>{}</name>".format(self.metadata_type), "    </types>"]
        )
