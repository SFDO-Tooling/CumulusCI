from collections import defaultdict
from typing import List, cast
import contextlib
import functools
import json
import pathlib
import re
import time
import zipfile

from cumulusci.core.config import ScratchOrgConfig
from cumulusci.core.sfdx import sfdx
from cumulusci.core.utils import process_bool_arg
from cumulusci.core.utils import process_list_arg
from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.tasks.salesforce.BaseRetrieveMetadata import BaseRetrieveMetadata
from cumulusci.tasks.salesforce.BaseSalesforceApiTask import BaseSalesforceApiTask
from cumulusci.tasks.metadata.package import PackageXmlGenerator
from cumulusci.utils import temporary_dir
from cumulusci.utils import process_text_in_directory
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
    @contextlib.contextmanager
    def _snapshot_file(self):
        with self.project_config.open_cache("snapshot") as parent_dir:
            yield parent_dir / f"{self.org_config.name}.json"

    def _load_snapshot(self):
        """Load the snapshot of which component revisions have been retrieved."""
        self._snapshot = {}
        with self._snapshot_file as sf:
            if sf.exists():
                with sf.open("r") as f:
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
        with self._snapshot_file as sf:
            with sf.open("w") as f:
                json.dump(self._snapshot, f)

    def _reset_sfdx_snapshot(self):
        # If org is from sfdx, reset sfdx source tracking
        if self.project_config.project__source_format == "sfdx" and isinstance(
            self.org_config, ScratchOrgConfig
        ):
            sfdx(
                "force:source:tracking:reset",
                args=["-p"],
                username=self.org_config.username,
                capture_output=True,
                check_return=True,
            )


class BaseRetrieveChanges(BaseSalesforceApiTask):

    task_options = {
        "components": {"description": "Metadata components to retrieve"},
        "path": {
            "description": "The path to write the retrieved metadata",
        },
        "api_version": {
            "description": "Override the default API version for the retrieve."
        },
        "namespace_tokenize": BaseRetrieveMetadata.task_options["namespace_tokenize"],
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        path = self.options.get("path")
        if path is None:
            path = self.project_config.default_package_directory
        self.path = pathlib.Path(path)

        package_xml_path = self.path / "package.xml"
        self.md_format = package_xml_path.exists()

        self.options["namespace_tokenize"] = self.options.get("namespace_tokenize")
        self.options["api_version"] = self.options.get(
            "api_version", self.project_config.project__package__api_version
        )

    def _run_task(self):
        self._retrieve_components(self.options["components"])

    def _retrieve_components(self, components):
        """Retrieve specified components from an org into a target folder.

        Retrieval is done using the Metadata API.
        """

        api_version = self.options["api_version"]
        target = self.path
        # Create target if it doesn't exist
        target.mkdir(parents=True, exist_ok=True)

        # Construct package.xml with components to retrieve, in its own tempdir
        with temporary_dir(chdir=False) as manifest_path:
            package_xml_path = pathlib.Path(manifest_path) / "package.xml"
            self._write_manifest(components, package_xml_path)

            if self.md_format:
                self._retrieve_mdapi_format(package_xml_path, target)
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

    def _write_manifest(self, changes: List, path: pathlib.Path):
        """Write a package.xml for the specified changes and API version."""
        type_members = defaultdict(list)
        for change in changes:
            type_members[change["MemberType"]].append(change["MemberName"])

        generator = PackageXmlGenerator(
            ".",
            self.options["api_version"],
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
    ):
        # Retrieve metadata
        package_xml = package_xml_path.read_text()
        src_zip = cast(
            zipfile.ZipFile,
            ApiRetrieveUnpackaged(self, package_xml, self.options["api_version"])(),
        )
        src_zip.extractall(target_path)

        # Merge retrieved metadata into target
        target_package = MetadataPackage(target_path)
        MetadataPackage(package_xml_path.parent).merge_to(target_package)

        namespace_tokenize = self.options["namespace_tokenize"]
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
        # default "snapshot" to true instead of false
        self.options["snapshot"] = process_bool_arg(kwargs.get("snapshot") or True)

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
                # we can reset sfdx source tracking too
                self._reset_sfdx_snapshot()


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
            self._reset_sfdx_snapshot()

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
