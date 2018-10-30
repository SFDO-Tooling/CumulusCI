from collections import defaultdict
import os

from cumulusci.core.utils import process_list_arg
from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.tasks.salesforce import BaseRetrieveMetadata
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.tasks.metadata.package import PackageXmlGenerator
from cumulusci.tasks.metadata.package import __location__


class ListChanges(BaseSalesforceApiTask):

    task_options = {
        "include": {
            "description": "Include changed components matching this string.",
            "required": True,
        }
    }

    def _init_options(self, kwargs):
        super(ListChanges, self)._init_options(kwargs)
        self.options["include"] = process_list_arg(self.options["include"])

    def _run_task(self):
        changes = self.tooling.query(
            "SELECT MemberName, MemberType FROM SourceMember WHERE IsNameObsolete=false"
        )
        if changes["totalSize"]:
            self.logger.info(
                "Found {} changed components in the scratch org:".format(
                    changes["totalSize"]
                )
            )
            for change in changes["records"]:
                mdtype = change["MemberType"]
                name = change["MemberName"]
                if not any(s in mdtype or s in name for s in self.options["include"]):
                    continue
                self.logger.info("  {}: {}".format(mdtype, name))
        else:
            self.logger.info("Found no changes.")


class RetrieveChanges(BaseRetrieveMetadata, BaseSalesforceApiTask):
    api_class = ApiRetrieveUnpackaged

    task_options = {
        "path": {
            "description": "The path to write the retrieved metadata",
            "required": True,
        },
        "include": {
            "description": "Include changed components matching this string.",
            "required": True,
        },
        "api_version": {
            "description": (
                "Override the default api version for the retrieve."
                + " Defaults to project__package__api_version"
            )
        },
    }

    def _init_options(self, kwargs):
        super(RetrieveChanges, self)._init_options(kwargs)

        if "api_version" not in self.options:
            self.options[
                "api_version"
            ] = self.project_config.project__package__api_version

        self.options["include"] = process_list_arg(self.options["include"])

    def _get_api(self):
        self.logger.info("Querying Salesforce for changed source members")
        changes = self.tooling.query(
            "SELECT MemberName, MemberType FROM SourceMember WHERE IsNameObsolete=false"
        )

        type_members = defaultdict(list)
        for change in changes["records"]:
            mdtype = change["MemberType"]
            name = change["MemberName"]
            if any(s in mdtype or s in name for s in self.options["include"]):
                self.logger.info("Including {} ({})".format(name, mdtype))
                type_members[mdtype].append(name)

        types = []
        for name, members in type_members.items():
            types.append(MetadataType(name, members))
        package_xml = PackageXmlGenerator(self.options["api_version"], types=types)()

        return self.api_class(self, package_xml, self.options.get("api_version"))

    def _run_task(self):
        super(RetrieveChanges, self)._run_task()

        # update package.xml
        package_xml = PackageXmlGenerator(
            directory=self.options["path"],
            api_version=self.options["api_version"],
            package_name=self.project_config.project__package__name,
        )()
        with open(os.path.join(self.options["path"], "package.xml"), "w") as f:
            f.write(package_xml)


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
