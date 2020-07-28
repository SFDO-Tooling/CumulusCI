from collections import defaultdict
from typing import List, Union, cast
import functools
import json
import os
import pathlib
import re
import time
import zipfile

from cumulusci.core.sfdx import sfdx
from cumulusci.core.utils import process_bool_arg
from cumulusci.core.utils import process_list_arg
from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.tasks.salesforce.BaseRetrieveMetadata import BaseRetrieveMetadata
from cumulusci.tasks.salesforce.BaseSalesforceApiTask import BaseSalesforceApiTask
from cumulusci.tasks.metadata.package import PackageXmlGenerator
from cumulusci.utils import process_text_in_directory, temporary_dir
from cumulusci.utils import tokenize_namespace
from cumulusci.utils.metadata import MetadataPackage


class ListChanges(BaseSalesforceApiTask):
    api_version = "48.0"

    task_options = {
        "include": {
            "description": "A comma-separated list of strings. "
            "Components will be included if one of these strings "
            "is part of either the metadata type or name. "
            "Example: ``-o include CustomField,Admin`` matches both "
            "``CustomField: Favorite_Color__c`` and ``Profile: Admin``"
        },
        "types": {
            "description": "A comma-separated list of metadata types to include."
        },
        "exclude": {"description": "Exclude changed components matching this string."},
        "snapshot": {
            "description": "If True, all matching items will be set to be ignored at their current revision number.  This will exclude them from the results unless a new edit is made."
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.options["include"] = process_list_arg(self.options.get("include", [])) + [
            f"{mdtype}:" for mdtype in process_list_arg(self.options.get("types", []))
        ]
        self.options["exclude"] = process_list_arg(self.options.get("exclude", []))
        self.options["snapshot"] = process_bool_arg(self.options.get("snapshot", False))
        self._include = self.options["include"]
        self._exclude = self.options["exclude"]
        self._exclude.extend(self.project_config.project__source__ignore or [])

    @property
    def _snapshot_path(self):
        parent_dir = os.path.join(".cci", "snapshot")
        if not os.path.isdir(parent_dir):
            os.makedirs(parent_dir)
        return os.path.join(parent_dir, "{}.json".format(self.org_config.name))

    def _load_snapshot(self):
        """Load the snapshot of which component revisions have been retrieved."""
        self._snapshot = {}
        if os.path.isfile(self._snapshot_path):
            with open(self._snapshot_path, "r") as f:
                self._snapshot = json.load(f)

    def _run_task(self):
        self._load_snapshot()
        changes = self._get_changes()
        if changes:
            self.logger.info(
                f"Found {len(changes)} changed components in the scratch org."
            )
        else:
            self.logger.info("Found no changes.")

        filtered, ignored = self._filter_changes(changes)
        if ignored:
            self.logger.info(
                f"Ignored {len(ignored)} changed components in the scratch org."
            )
            self.logger.info(f"{len(filtered)} remaining changes after filtering.")

        for change in filtered:
            self.logger.info("{MemberType}: {MemberName}".format(**change))

        if self.options["snapshot"]:
            self.logger.info("Storing snapshot of changes")
            self._store_snapshot(filtered)

    def _get_changes(self):
        """Get the SourceMember records that have changed since the last snapshot."""
        sourcemembers = self.tooling.query_all(
            "SELECT MemberName, MemberType, RevisionCounter FROM SourceMember "
            "WHERE IsNameObsolete=false"
        )
        changes = []
        for sourcemember in sourcemembers["records"]:
            mdtype = sourcemember["MemberType"]
            name = sourcemember["MemberName"]
            current_revnum = self._snapshot.get(mdtype, {}).get(name)
            new_revnum = sourcemember["RevisionCounter"] or -1
            if current_revnum and current_revnum == new_revnum:
                continue
            changes.append(sourcemember)
        return changes

    def _filter_changes(self, changes):
        """Filter changes using the include/exclude options"""
        filtered = []
        ignored = []
        for change in changes:
            mdtype = change["MemberType"]
            name = change["MemberName"]
            full_name = f"{mdtype}: {name}"
            if (
                self._include
                and not any(re.search(s, full_name) for s in self._include)
            ) or any(re.search(s, full_name) for s in self._exclude):
                ignored.append(change)
            else:
                filtered.append(change)
        return filtered, ignored

    def _store_snapshot(self, changes):
        """Update the snapshot of which component revisions have been retrieved."""
        for change in changes:
            mdtype = change["MemberType"]
            name = change["MemberName"]
            revnum = change["RevisionCounter"] or -1
            self._snapshot.setdefault(mdtype, {})[name] = revnum
        with open(self._snapshot_path, "w") as f:
            json.dump(self._snapshot, f)

    @property
    def _maxrevision_path(self):
        parent_dir = os.path.join(".sfdx", "orgs", self.org_config.username)
        if not os.path.isdir(parent_dir):
            os.makedirs(parent_dir)
        return os.path.join(parent_dir, "maxrevision.json")

    def _load_maxrevision(self):
        """Load sfdx's maxrevision file."""
        if not os.path.exists(self._maxrevision_path):
            return -1
        with open(self._maxrevision_path, "r") as f:
            return json.load(f)

    def _store_maxrevision(self, value):
        """Update sfdx's maxrevision file."""
        if value == -1:
            return
        self.logger.info(f"Setting source tracking max revision to {value}")
        with open(self._maxrevision_path, "w") as f:
            json.dump(value, f)


class BaseRetrieveChanges(BaseSalesforceApiTask):

    task_options = {
        "components": {"description": "Metadata components to retrieve"},
        "path": {
            "description": "The path to write the retrieved metadata",
            "required": False,
        },
        "api_version": {
            "description": (
                "Override the default api version for the retrieve."
                + " Defaults to project__package__api_version"
            )
        },
        "namespace_tokenize": BaseRetrieveMetadata.task_options["namespace_tokenize"],
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        # Check which directories are configured as dx packages
        package_directories = []
        default_package_directory = None
        if os.path.exists("sfdx-project.json"):
            with open("sfdx-project.json", "r") as f:
                sfdx_project = json.load(f)
                for package_directory in sfdx_project.get("packageDirectories", []):
                    package_directories.append(package_directory["path"])
                    if package_directory.get("default"):
                        default_package_directory = package_directory["path"]

        path = self.options.get("path")
        if path is None:
            # set default path to src for mdapi format,
            # or the default package directory from sfdx-project.json for dx format
            if (
                default_package_directory
                and self.project_config.project__source_format == "sfdx"
            ):
                path = default_package_directory
                md_format = False
            else:
                path = "src"
                md_format = True
        else:
            md_format = path not in package_directories
        self.md_format = md_format
        self.options["path"] = path

        self.options["namespace_tokenize"] = self.options.get(
            "namespace_tokenize", False
        )
        self.options["api_version"] = self.options.get(
            "api_version", self.project_config.project__package__api_version
        )

    def _run_task(self):
        self._retrieve_components(self.options["components"])

    def _retrieve_components(self, components):
        """Retrieve specified components from an org into a target folder.

        Retrieval is done using the Metadata API.

        Set `md_format` to True if retrieving into a folder with a package
        in metadata format. Retrievals to metadata format can also set `namespace_tokenize`
        to a namespace prefix to replace it with a `%%%NAMESPACE%%%` token.
        """

        api_version = self.options["api_version"]
        target = pathlib.Path(self.options["path"])
        # Create target if it doesn't exist
        target.mkdir(parents=True, exist_ok=True)

        # Construct package.xml with components to retrieve, in its own tempdir
        with temporary_dir(chdir=False) as manifest_path:
            package_xml_path = pathlib.Path(manifest_path) / "package.xml"
            self._write_manifest(
                components, package_xml_path, self.options["api_version"]
            )

            if self.md_format:
                self._retrieve_mdapi_format(
                    package_xml_path,
                    target,
                    self.options["namespace_tokenize"],
                    api_version,
                )
            else:
                sfdx(
                    "force:source:retrieve",
                    access_token=self.org_config.access_token,
                    log_note="Retrieving components",
                    args=["-a", str(api_version), "-x", package_xml_path, "-w", "5"],
                    capture_output=False,
                    check_return=True,
                    env={"SFDX_INSTANCE_URL": self.org_config.instance_url},
                )

    def _write_manifest(self, changes: List, path: pathlib.Path, api_version: str):
        """Write a package.xml for the specified changes and API version."""
        type_members = defaultdict(list)
        for change in changes:
            type_members[change["MemberType"]].append(change["MemberName"])

        generator = PackageXmlGenerator(
            ".",
            api_version,
            types=[
                MetadataType(name, members) for name, members in type_members.items()
            ],
        )
        package_xml = generator()
        path.write_text(package_xml)

    def _retrieve_mdapi_format(
        self,
        package_xml_path: pathlib.Path,
        target_path: pathlib.Path,
        namespace_tokenize: Union[bool, str],
        api_version: str,
    ):
        # Retrieve metadata
        package_xml = package_xml_path.read_text()
        src_zip = cast(
            zipfile.ZipFile, ApiRetrieveUnpackaged(self, package_xml, api_version)()
        )
        src_zip.extractall(target_path)

        # Merge retrieved metadata into target
        target_package = MetadataPackage(target_path)
        MetadataPackage(package_xml_path.parent).merge_to(target_package)

        if namespace_tokenize:
            process_text_in_directory(
                target_path,
                functools.partial(tokenize_namespace, namespace=namespace_tokenize),
            )

        # Update package.xml
        target_package.write_manifest()


class RetrieveChanges(BaseRetrieveChanges, ListChanges, BaseSalesforceApiTask):

    task_options = {
        **ListChanges.task_options,
        "path": BaseRetrieveChanges.task_options["path"],
        "api_version": BaseRetrieveChanges.task_options["api_version"],
        "namespace_tokenize": BaseRetrieveMetadata.task_options["namespace_tokenize"],
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.options["snapshot"] = process_bool_arg(kwargs.get("snapshot", True))

    def _run_task(self):
        self._load_snapshot()
        self.logger.info("Querying Salesforce for changed source members")
        changes = self._get_changes()
        filtered, ignored = self._filter_changes(changes)
        if not filtered:
            self.logger.info("No changes to retrieve")
            return
        for change in filtered:
            self.logger.info("{MemberType}: {MemberName}".format(**change))

        self._retrieve_components(filtered)

        if self.options["snapshot"]:
            self.logger.info("Storing snapshot of changes")
            self._store_snapshot(filtered)
            if not ignored:
                # If all changed components were retrieved,
                # we can update the sfdx maxrevision too
                current_maxrevision = self._load_maxrevision()
                new_maxrevision = max(
                    change["RevisionCounter"] or -1 for change in filtered
                )
                self._store_maxrevision(max(current_maxrevision, new_maxrevision))


class SnapshotChanges(ListChanges):

    task_options = {}

    def _init_options(self, kwargs):
        # Avoid loading ListChanges options
        pass

    def _run_task(self):
        if self.org_config.scratch:
            self._snapshot = {}

            changes = self._get_changes()
            if not changes:
                # Try again if source tracking hasn't updated
                time.sleep(5)
                changes = self._get_changes()

            if changes:
                self._store_snapshot(changes)
                maxrevision = max(change["RevisionCounter"] or -1 for change in changes)
                self._store_maxrevision(maxrevision)

    def freeze(self, step):
        return []


class MetadataType(object):
    def __init__(self, name, members):
        self.metadata_type = name
        self.members = members

    def __call__(self):
        return (
            ["    <types>"]
            + [f"        <members>{member}</members>" for member in self.members]
            + [f"        <name>{self.metadata_type}</name>", "    </types>"]
        )
