import tempfile

from pathlib import Path

from cumulusci.core.exceptions import CumulusCIException
from cumulusci.tasks.salesforce import BaseSalesforceApiTask, Deploy
from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.tasks.metadata.package import PackageXmlGenerator
from cumulusci.core.utils import process_bool_arg, process_list_arg
from cumulusci.utils import elementtree_parse_file, inject_namespace
from cumulusci.core.config import TaskConfig


class BaseMetadataETLTask(BaseSalesforceApiTask):
    deploy = False
    retrieve = False

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

    @property
    def _namespace_injector(self):
        return lambda text: inject_namespace(
            "",
            text,
            self.options.get("namespace_inject"),
            not self.options["unmanaged"],
        )[1]

    def _get_package_xml_content(self):
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <version>{self.api_version}</version>
</Package>
"""

    def _generate_package_xml(self):
        return self._namespace_injector(self._get_package_xml_content())

    def _create_directories(self, tempdir):
        if self.retrieve:
            self.retrieve_dir = Path(tempdir, "retrieve")
            self.retrieve_dir.mkdir()
        if self.deploy:
            self.deploy_dir = Path(tempdir, "deploy")
            self.deploy_dir.mkdir()

    def _retrieve(self):
        api_retrieve = ApiRetrieveUnpackaged(
            self, self._generate_package_xml(), self.api_version
        )
        unpackaged = api_retrieve()
        unpackaged.extractall(self.retrieve_dir)

    def _transform(self):
        pass

    def _deploy(self):
        generator = PackageXmlGenerator(str(self.deploy_dir), self.api_version)

        target_profile_xml = Path(self.deploy_dir, "package.xml")
        target_profile_xml.write_text(generator())

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
        return api()

    def _run_task(self):
        with tempfile.TemporaryDirectory() as tempdir:
            self._create_directories(tempdir)
            if self.retrieve:
                self._retrieve()
            self._transform()
            if self.deploy:
                self._deploy()


class BaseMetadataSynthesisTask(BaseMetadataETLTask):
    """Base class for Metadata ETL tasks that generate new metadata
    and deploy it into the org."""

    deploy = True

    def _transform(self):
        self._synthesize()

    def _synthesize(self):
        # Create metadata in self.deploy_dir
        pass


class BaseMetadataTransformTask(BaseMetadataETLTask):
    """Base class for Metadata ETL tasks that extract metadata,
    transform it, and deploy it back into the org."""

    retrieve = True
    deploy = True

    def _get_entities(self):
        return {}

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

    def _get_package_xml_content(self):
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
{self._get_types_package_xml()}
    <version>{self.api_version}</version>
</Package>
"""

    def _transform(self):
        pass


class MetadataSingleEntityTransformTask(BaseMetadataTransformTask):
    """Base class for a Metadata ETL task that affects one or more
    instances of a specific metadata entity."""

    entity = None

    task_options = {
        "api_names": {"description": "List of API names of entities to affect"},
        **BaseMetadataETLTask.task_options,
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        self.api_names = list(
            map(
                self._namespace_injector,
                process_list_arg(self.options.get("api_names", [])),
            )
        )

    def _get_entities(self):
        return {self.entity: self.api_names or ["*"]}

    def _transform_entity(self, metadata, api_name):
        return metadata

    def _transform(self):
        # call _transform_entity once per retrieved entity
        # if the entity is an XML file, provide a parsed version
        # and write the returned metadata into the deploy directory

        parser = PackageXmlGenerator(
            None, self.api_version
        )  # We'll use it for its metadata_map
        entity_configurations = list(
            filter(
                lambda entry: any(
                    [
                        subentry["type"] == self.entity
                        for subentry in parser.metadata_map[entry]
                    ]
                ),
                parser.metadata_map,
            )
        )
        if not entity_configurations:
            raise CumulusCIException(
                f"Unable to locate configuration for entity {self.entity}"
            )

        configuration = parser.metadata_map[entity_configurations[0]][0]
        if configuration["class"] != "MetadataFilenameParser":
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
                parent_dir.mkdir()
                destination_path = parent_dir / f"{api_name}.{extension}"
                transformed_xml.write(
                    destination_path,
                    "utf-8",
                    xml_declaration=True,
                    default_namespace=self.namespaces["sf"],
                )
