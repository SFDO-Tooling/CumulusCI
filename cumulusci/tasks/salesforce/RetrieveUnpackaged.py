from collections import defaultdict
import os

import yaml

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.tasks.salesforce import BaseRetrieveMetadata
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.tasks.metadata.package import PackageXmlGenerator
from cumulusci.tasks.metadata.package import __location__


retrieve_unpackaged_options = BaseRetrieveMetadata.task_options.copy()
retrieve_unpackaged_options.update(
    {
        "package_xml": {
            "description": "The path to a package.xml manifest to use for the retrieve."
        },
        "include": {"description": "Retrieve changed components matching this string."},
        "api_version": {
            "description": (
                "Override the default api version for the retrieve."
                + " Defaults to project__package__api_version"
            )
        },
    }
)


class RetrieveUnpackaged(BaseRetrieveMetadata, BaseSalesforceApiTask):
    api_class = ApiRetrieveUnpackaged

    task_options = retrieve_unpackaged_options

    def _init_options(self, kwargs):
        super(RetrieveUnpackaged, self)._init_options(kwargs)

        # @@@ needs to be xor
        if "package_xml" not in self.options and "include" not in self.options:
            raise TaskOptionsError(
                "You must specify the package_xml or include option."
            )

        if "package_xml" in self.options:
            self.options["package_xml_path"] = self.options["package_xml"]
            with open(self.options["package_xml_path"], "r") as f:
                self.options["package_xml"] = f.read()

        if "api_version" not in self.options:
            self.options[
                "api_version"
            ] = self.project_config.project__package__api_version

        if self.options.get("include"):
            self.options["include"] = self.options["include"].split(" ")
        else:
            self.options["include"] = []

    def _get_api(self):
        self.logger.info("Querying Salesforce for changed source members")
        changes = self.tooling.query(
            "SELECT MemberName, MemberType FROM SourceMember WHERE IsNameObsolete=false"
        )

        type_members = defaultdict(list)
        for change in changes["records"]:
            type = change["MemberType"]
            name = change["MemberName"]
            if any(s in type or s in name for s in self.options["include"]):
                self.logger.info("Including {} ({})".format(name, type))
                type_members[type].append(name)

        if type_members:
            types = []
            for name, members in type_members.items():
                types.append(MetadataType(name, members))
            package_xml = PackageXmlGenerator(
                self.options["api_version"], types=types
            )()
        else:
            package_xml = self.options["package_xml"]

        return self.api_class(self, package_xml, self.options.get("api_version"))


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


class ListChanges(BaseSalesforceApiTask):
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
                self.logger.info(
                    "  {}: {}".format(change["MemberType"], change["MemberName"])
                )
        else:
            self.logger.info("Found no changes.")
