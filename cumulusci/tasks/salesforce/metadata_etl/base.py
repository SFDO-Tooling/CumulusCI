import abc
import enum
import tempfile

from pathlib import Path

from cumulusci.core.exceptions import CumulusCIException
from cumulusci.tasks.salesforce import BaseSalesforceApiTask, Deploy
from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.tasks.metadata.package import PackageXmlGenerator
from cumulusci.core.utils import process_bool_arg, process_list_arg
from cumulusci.utils import elementtree_parse_file, inject_namespace
from cumulusci.core.config import TaskConfig


class MetadataOperation(enum.Enum):
    DEPLOY = "deploy"
    RETRIEVE = "retrieve"


class BaseMetadataETLTask(BaseSalesforceApiTask):
    deploy = False
    retrieve = False

    __metaclass__ = abc.ABCMeta

    namespaces = {"sf": "http://soap.sforce.com/2006/04/metadata"}

    task_options = {
        "unmanaged": {
            "description": "If True, changes namespace_inject to replace tokens with a blank string"
        },
        "namespace_inject": {
            "description": "If set, the namespace tokens in files and filenames are replaced with the namespace's prefix"
        },
        "api_version": {
            "description": "Metadata API version to use, if not project__package__api_version."
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        self.options["unmanaged"] = process_bool_arg(
            self.options.get("unmanaged", False)
        )
        self.api_version = (
            self.options.get("api_version")
            or self.project_config.project__package__api_version
        )

    def _inject_namespace(self, text):
        return inject_namespace(
            "",
            text,
            self.options.get("namespace_inject"),
            not self.options["unmanaged"],
        )[1]

    @abc.abstractmethod
    def _get_package_xml_content(self, operation):
        pass

    def _generate_package_xml(self, operation):
        return self._inject_namespace(self._get_package_xml_content(operation))

    def _create_directories(self, tempdir):
        if self.retrieve:
            self.retrieve_dir = Path(tempdir, "retrieve")
            self.retrieve_dir.mkdir()
        if self.deploy:
            self.deploy_dir = Path(tempdir, "deploy")
            self.deploy_dir.mkdir()

    def _retrieve(self):
        api_retrieve = ApiRetrieveUnpackaged(
            self,
            self._generate_package_xml(MetadataOperation.RETRIEVE),
            self.api_version,
        )
        unpackaged = api_retrieve()
        unpackaged.extractall(self.retrieve_dir)

    @abc.abstractmethod
    def _transform(self):
        pass

    def _deploy(self):
        target_profile_xml = Path(self.deploy_dir, "package.xml")
        target_profile_xml.write_text(
            self._generate_package_xml(MetadataOperation.DEPLOY)
        )

        api = Deploy(
            self.project_config,
            TaskConfig(
                {
                    "options": {
                        "path": self.deploy_dir,
                        "namespace_inject": self.options.get("namespace_inject"),
                        "unmanaged": self.options.get("unmanaged"),
                    }
                }
            ),
            self.org_config,
        )
        result = api()

        return result

    @abc.abstractmethod
    def _post_deploy(self, result):
        pass

    def _run_task(self):
        with tempfile.TemporaryDirectory() as tempdir:
            self._create_directories(tempdir)
            if self.retrieve:
                self._retrieve()
            self._transform()
            if self.deploy:
                result = self._deploy()
                self._post_deploy(result)


class BaseMetadataSynthesisTask(BaseMetadataETLTask):
    """Base class for Metadata ETL tasks that generate new metadata
    and deploy it into the org."""

    deploy = True

    __metaclass__ = abc.ABCMeta

    def _generate_package_xml(self, deploy):
        generator = PackageXmlGenerator(str(self.deploy_dir), self.api_version)
        return generator()

    def _transform(self):
        self._synthesize()

    @abc.abstractmethod
    def _synthesize(self):
        # Create metadata in self.deploy_dir
        pass


class BaseMetadataTransformTask(BaseMetadataETLTask):
    """Base class for Metadata ETL tasks that extract metadata,
    transform it, and deploy it back into the org."""

    retrieve = True
    deploy = True

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def _get_entities(self):
        pass

    def _get_types_package_xml(self):
        base = """    <types>
{members}
        <name>{name}</name>
    </types>
"""
        types = ""
        for entity, api_names in self._get_entities().items():
            members = "\n".join(
                f"        <members>{api_name}</members>" for api_name in api_names
            )
            types += base.format(members=members, name=entity)

        return types

    def _get_package_xml_content(self, operation):
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
{self._get_types_package_xml()}
    <version>{self.api_version}</version>
</Package>
"""

    @abc.abstractmethod
    def _transform(self):
        pass


class MetadataSingleEntityTransformTask(BaseMetadataTransformTask):
    """Base class for a Metadata ETL task that affects one or more
    instances of a specific metadata entity."""

    entity = None

    __metaclass__ = abc.ABCMeta

    task_options = {
        "api_names": {"description": "List of API names of entities to affect"},
        **BaseMetadataETLTask.task_options,
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        self.api_names = list(
            map(
                self._inject_namespace,
                process_list_arg(self.options.get("api_names", [])),
            )
        )

    def _get_entities(self):
        return {self.entity: self.api_names or ["*"]}

    @abc.abstractmethod
    def _transform_entity(self, metadata, api_name):
        pass

    def _transform(self):
        # call _transform_entity once per retrieved entity
        # if the entity is an XML file, provide a parsed version
        # and write the returned metadata into the deploy directory

        parser = PackageXmlGenerator(
            None, self.api_version
        )  # We'll use it for its metadata_map
        entity_configurations = [
            entry
            for entry in parser.metadata_map
            if any(
                [
                    subentry["type"] == self.entity
                    for subentry in parser.metadata_map[entry]
                ]
            )
        ]
        if not entity_configurations:
            raise CumulusCIException(
                f"Unable to locate configuration for entity {self.entity}"
            )

        configuration = parser.metadata_map[entity_configurations[0]][0]
        if configuration["class"] not in [
            "MetadataFilenameParser",
            "CustomObjectParser",
        ]:
            raise CumulusCIException(
                f"MetadataSingleEntityTransformTask only supports manipulating complete, file-based XML entities (not {self.entity})"
            )

        extension = configuration["extension"]
        directory = entity_configurations[0]

        for api_name in self.api_names:
            path = self.retrieve_dir / directory / f"{api_name}.{extension}"
            if not path.exists():
                raise CumulusCIException(f"Cannot find metadata file {path}")

            transformed_xml = self._transform_entity(
                elementtree_parse_file(path), api_name
            )
            if transformed_xml:
                parent_dir = self.deploy_dir / directory
                if not parent_dir.exists():
                    parent_dir.mkdir()
                destination_path = parent_dir / f"{api_name}.{extension}"
                transformed_xml.write(
                    destination_path,
                    "utf-8",
                    xml_declaration=True,
                    default_namespace=self.namespaces["sf"],
                )


def get_new_tag_index(tree, tag, namespaces):
    # All top-level tags must be grouped together in XML file
    tags = tree.findall(f".//sf:{tag}", namespaces)
    if tags:
        # Insert new tag after the last existing tag of the same type
        return list(tree.getroot()).index(tags[-1]) + 1
    else:
        # There are no existing tags of this type; insert new tag at the top.
        return 0
