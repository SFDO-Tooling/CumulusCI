import pathlib
from typing import List, Optional

from defusedxml.minidom import parseString
from pydantic import ValidationError

from cumulusci.core.dependencies.utils import TaskContext
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.sfdx import convert_sfdx_source
from cumulusci.core.source_transforms.transforms import (
    SourceTransform,
    SourceTransformList,
)
from cumulusci.core.utils import process_bool_arg, process_list_arg
from cumulusci.salesforce_api.metadata import ApiDeploy, ApiRetrieveUnpackaged
from cumulusci.salesforce_api.package_zip import MetadataPackageZipBuilder
from cumulusci.tasks.salesforce.BaseSalesforceMetadataApiTask import (
    BaseSalesforceMetadataApiTask,
)
from cumulusci.utils.xml import metadata_tree


class Deploy(BaseSalesforceMetadataApiTask):
    api_class = ApiDeploy
    api_retrieve_unpackaged = ApiRetrieveUnpackaged
    task_options = {
        "path": {
            "description": "The path to the metadata source to be deployed",
            "required": True,
        },
        "unmanaged": {
            "description": "If True, changes namespace_inject to replace tokens with a blank string"
        },
        "namespace_inject": {
            "description": "If set, the namespace tokens in files and filenames are replaced with the namespace's prefix"
        },
        "namespace_strip": {
            "description": "If set, all namespace prefixes for the namespace specified are stripped from files and filenames"
        },
        "check_only": {
            "description": "If True, performs a test deployment (validation) of components without saving the components in the target org"
        },
        "collision_check": {
            "description": "If True, performs a collision check with metadata already present in the target org"
        },
        "test_level": {
            "description": "Specifies which tests are run as part of a deployment. Valid values: NoTestRun, RunLocalTests, RunAllTestsInOrg, RunSpecifiedTests."
        },
        "specified_tests": {
            "description": "Comma-separated list of test classes to run upon deployment. Applies only with test_level set to RunSpecifiedTests."
        },
        "static_resource_path": {
            "description": "The path where decompressed static resources are stored.  Any subdirectories found will be zipped and added to the staticresources directory of the build."
        },
        "namespaced_org": {
            "description": "If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org."
        },
        "clean_meta_xml": {
            "description": "Defaults to True which strips the <packageVersions/> element from all meta.xml files.  The packageVersion element gets added automatically by the target org and is set to whatever version is installed in the org.  To disable this, set this option to False"
        },
        "transforms": {
            "description": "Apply source transforms before deploying. See the CumulusCI documentation for details on how to specify transforms."
        },
    }

    namespaces = {"sf": "http://soap.sforce.com/2006/04/metadata"}

    transforms: List[SourceTransform] = []

    def _init_options(self, kwargs):
        super(Deploy, self)._init_options(kwargs)

        self.check_only = process_bool_arg(self.options.get("check_only", False))
        self.test_level = self.options.get("test_level")
        if self.test_level and self.test_level not in [
            "NoTestRun",
            "RunLocalTests",
            "RunAllTestsInOrg",
            "RunSpecifiedTests",
        ]:
            raise TaskOptionsError(
                f"Specified test run level {self.test_level} is not valid."
            )

        self.specified_tests = process_list_arg(self.options.get("specified_tests", []))

        if bool(self.specified_tests) != (self.test_level == "RunSpecifiedTests"):
            raise TaskOptionsError(
                "The specified_tests option and test_level RunSpecifiedTests must be used together."
            )

        self.options["namespace_inject"] = (
            self.options.get("namespace_inject")
            or self.project_config.project__package__namespace
        )
        if "collision_check" not in self.options:
            self.options["collision_check"] = False

        if "transforms" in self.options:
            try:
                self.transforms = SourceTransformList.parse_obj(
                    self.options["transforms"]
                ).as_transforms()
            except ValidationError as e:
                raise TaskOptionsError(
                    "The transform spec is not valid. See CumulusCI documentation for details of how to specify transforms. "
                    f"The validation error was {str(e)}"
                )

    def _get_api(self, path=None):
        if not path:
            path = self.options.get("path")

        package_zip = self._get_package_zip(path)

        if isinstance(package_zip, dict):
            self.logger.warning(f"Below Components are getting overridden{package_zip}")
            return None
        elif package_zip is not None:
            self.logger.info("Payload size: {} bytes".format(len(package_zip)))
        else:
            self.logger.warning("Deployment package is empty; skipping deployment.")
            return

        return self.api_class(
            self,
            package_zip,
            purge_on_delete=False,
            check_only=self.check_only,
            test_level=self.test_level,
            run_tests=self.specified_tests,
        )

    def _has_namespaced_package(self, ns: Optional[str]) -> bool:
        if "unmanaged" in self.options:
            return not process_bool_arg(self.options.get("unmanaged", True))
        return bool(ns) and ns in self.org_config.installed_packages

    def _is_namespaced_org(self, ns: Optional[str]) -> bool:
        if "namespaced_org" in self.options:
            return process_bool_arg(self.options.get("namespaced_org", False))
        return bool(ns) and ns == self.org_config.namespace

    def _collision_check(self, src_path):
        xml_map = {}
        is_collision = False
        package_xml = open(f"{src_path}/package.xml", "r")
        source_xml_tree = metadata_tree.parse(f"{src_path}/package.xml")

        for type in source_xml_tree.types:
            members = []
            try:
                for member in type.members:
                    members.append(member.text)
            except AttributeError:  # Exception if there are no members for a type
                pass
            xml_map[type["name"].text] = members

        api_retrieve_unpackaged_object = self.api_retrieve_unpackaged(
            self, package_xml.read(), source_xml_tree.version.text
        )
        messages = parseString(
            api_retrieve_unpackaged_object._get_response().content
        ).getElementsByTagName("messages")

        for i in range(len(messages)):
            print(messages[i])
            message_list = messages[
                i
            ].firstChild.nextSibling.firstChild.nodeValue.split("'")

            if message_list[3] in xml_map[message_list[1]]:
                xml_map[message_list[1]].remove(message_list[3])

        for type, api_names in xml_map.items():
            if len(api_names) != 0:
                is_collision = True
                break
        print(xml_map)
        return is_collision, xml_map

    def _get_package_zip(self, path) -> str | None | dict:
        assert path, f"Path should be specified for {self.__class__.name}"
        if not pathlib.Path(path).exists():
            self.logger.warning(f"{path} not found.")
            return
        namespace = self.options["namespace_inject"]
        options = {
            **self.options,
            "clean_meta_xml": process_bool_arg(
                self.options.get("clean_meta_xml", True)
            ),
            "namespace_inject": namespace,
            "unmanaged": not self._has_namespaced_package(namespace),
            "namespaced_org": self._is_namespaced_org(namespace),
        }
        package_zip = None

        with convert_sfdx_source(path, None, self.logger) as src_path:
            ##############
            is_collision = False
            if "collision_check" in options and options["collision_check"]:
                is_collision, xml_map = self._collision_check(src_path)
            #############
            if not is_collision:
                context = TaskContext(self.org_config, self.project_config, self.logger)
                package_zip = MetadataPackageZipBuilder(
                    path=src_path,
                    context=context,
                    options=options,
                    transforms=self.transforms,
                )

                # If the package is empty, do nothing.
                if not package_zip.zf.namelist():
                    return
                return package_zip.as_base64()
            else:
                return xml_map

    def freeze(self, step):
        steps = super().freeze(step)
        for step in steps:
            if step["kind"] == "other":
                step["kind"] = "metadata"
        return steps
