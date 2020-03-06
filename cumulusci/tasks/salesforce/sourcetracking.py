from collections import defaultdict
import contextlib
import functools
import json
import os
import re
import time

from cumulusci.core.sfdx import sfdx
from cumulusci.core.utils import process_bool_arg
from cumulusci.core.utils import process_list_arg
from cumulusci.tasks.salesforce import BaseRetrieveMetadata
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.tasks.metadata.package import PackageXmlGenerator
from cumulusci.utils import temporary_dir
from cumulusci.utils import touch
from cumulusci.utils import inject_namespace
from cumulusci.utils import process_text_in_directory
from cumulusci.utils import tokenize_namespace


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
        super(ListChanges, self)._init_options(kwargs)
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
            "SELECT MemberName, MemberType, RevisionNum FROM SourceMember "
            "WHERE IsNameObsolete=false"
        )
        changes = []
        for sourcemember in sourcemembers["records"]:
            mdtype = sourcemember["MemberType"]
            name = sourcemember["MemberName"]
            current_revnum = self._snapshot.get(mdtype, {}).get(name)
            new_revnum = sourcemember["RevisionNum"] or -1
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
            revnum = change["RevisionNum"] or -1
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


retrieve_changes_task_options = ListChanges.task_options.copy()
retrieve_changes_task_options["path"] = {
    "description": "The path to write the retrieved metadata",
    "required": False,
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


def _write_manifest(changes, path, api_version):
    """Write a package.xml for the specified changes and API version."""
    type_members = defaultdict(list)
    for change in changes:
        type_members[change["MemberType"]].append(change["MemberName"])

    generator = PackageXmlGenerator(
        ".",
        api_version,
        types=[MetadataType(name, members) for name, members in type_members.items()],
    )
    package_xml = generator()
    with open(os.path.join(path, "package.xml"), "w") as f:
        f.write(package_xml)


def retrieve_components(
    components,
    org_config,
    target: str,
    md_format: bool,
    extra_package_xml_opts: dict,
    namespace_tokenize: str,
    api_version: str,
):
    """Retrieve specified components from an org into a target folder.

    Retrieval is done using the sfdx force:source:retrieve command.

    Set `md_format` to True if retrieving into a folder with a package
    in metadata format. In this case the folder will be temporarily
    converted to dx format for the retrieval and then converted back.
    Retrievals to metadata format can also set `namespace_tokenize`
    to a namespace prefix to replace it with a `%%%NAMESPACE%%%` token.
    """

    target = os.path.realpath(target)
    with contextlib.ExitStack() as stack:
        if md_format:
            # Create target if it doesn't exist
            if not os.path.exists(target):
                os.mkdir(target)
                touch(os.path.join(target, "package.xml"))

            # Inject namespace
            if namespace_tokenize:
                process_text_in_directory(
                    target,
                    functools.partial(
                        inject_namespace, namespace=namespace_tokenize, managed=True
                    ),
                )

            # Temporarily convert metadata format to DX format
            stack.enter_context(temporary_dir())
            os.mkdir("target")
            # We need to create sfdx-project.json
            # so that sfdx will recognize force-app as a package directory.
            with open("sfdx-project.json", "w") as f:
                json.dump(
                    {"packageDirectories": [{"path": "force-app", "default": True}]}, f
                )
            sfdx(
                "force:mdapi:convert",
                log_note="Converting to DX format",
                args=["-r", target, "-d", "force-app"],
                check_return=True,
            )

        # Construct package.xml with components to retrieve, in its own tempdir
        package_xml_path = stack.enter_context(temporary_dir(chdir=False))
        _write_manifest(components, package_xml_path, api_version)

        # Retrieve specified components in DX format
        sfdx(
            "force:source:retrieve",
            access_token=org_config.access_token,
            log_note="Retrieving components",
            args=[
                "-a",
                str(api_version),
                "-x",
                os.path.join(package_xml_path, "package.xml"),
                "-w",
                "5",
            ],
            capture_output=False,
            check_return=True,
            env={"SFDX_INSTANCE_URL": org_config.instance_url},
        )

        if md_format:
            # Convert back to metadata format
            sfdx(
                "force:source:convert",
                log_note="Converting back to metadata format",
                args=["-r", "force-app", "-d", target],
                capture_output=False,
                check_return=True,
            )

            # Reinject namespace tokens
            if namespace_tokenize:
                process_text_in_directory(
                    target,
                    functools.partial(tokenize_namespace, namespace=namespace_tokenize),
                )

            # Regenerate package.xml,
            # to avoid reformatting or losing package name/scripts
            package_xml_opts = {
                "directory": target,
                "api_version": api_version,
                **extra_package_xml_opts,
            }
            package_xml = PackageXmlGenerator(**package_xml_opts)()
            with open(os.path.join(target, "package.xml"), "w") as f:
                f.write(package_xml)


class RetrieveChanges(ListChanges, BaseSalesforceApiTask):
    task_options = retrieve_changes_task_options

    def _init_options(self, kwargs):
        super(RetrieveChanges, self)._init_options(kwargs)
        self.options["snapshot"] = process_bool_arg(kwargs.get("snapshot", True))

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

        if "api_version" not in self.options:
            self.options[
                "api_version"
            ] = self.project_config.project__package__api_version

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

        target = os.path.realpath(self.options["path"])
        package_xml_opts = {}
        if self.options["path"] == "src":
            package_xml_opts.update(
                {
                    "package_name": self.project_config.project__package__name,
                    "install_class": self.project_config.project__package__install_class,
                    "uninstall_class": self.project_config.project__package__uninstall_class,
                }
            )

        retrieve_components(
            filtered,
            self.org_config,
            target,
            md_format=self.md_format,
            namespace_tokenize=self.options.get("namespace_tokenize"),
            api_version=self.options["api_version"],
            extra_package_xml_opts=package_xml_opts,
        )

        if self.options["snapshot"]:
            self.logger.info("Storing snapshot of changes")
            self._store_snapshot(filtered)
            if not ignored:
                # If all changed components were retrieved,
                # we can update the sfdx maxrevision too
                current_maxrevision = self._load_maxrevision()
                new_maxrevision = max(
                    change["RevisionNum"] or -1 for change in filtered
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
                maxrevision = max(change["RevisionNum"] or -1 for change in changes)
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
