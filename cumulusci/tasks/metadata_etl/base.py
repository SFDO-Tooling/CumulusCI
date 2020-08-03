from abc import ABCMeta, abstractmethod
import enum
from pathlib import Path
import tempfile
from urllib.parse import quote, unquote

from cumulusci.core.exceptions import CumulusCIException, TaskOptionsError
from cumulusci.core.tasks import BaseSalesforceTask
from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.tasks.metadata.package import PackageXmlGenerator
from cumulusci.core.utils import process_bool_arg, process_list_arg
from cumulusci.utils import inject_namespace
from cumulusci.core.config import TaskConfig
from cumulusci.utils.xml import metadata_tree
from cumulusci.utils.xml.metadata_tree import MetadataElement


class MetadataOperation(enum.Enum):
    DEPLOY = "deploy"
    RETRIEVE = "retrieve"


class BaseMetadataETLTask(BaseSalesforceTask, metaclass=ABCMeta):
    """Abstract base class for all Metadata ETL tasks. Concrete tasks should
    generally subclass BaseMetadataSynthesisTask, BaseMetadataTransformTask,
    or MetadataSingleEntityTransformTask."""

    deploy = False
    retrieve = False

    task_options = {
        "managed": {
            "description": "If False, changes namespace_inject to replace tokens with a blank string"
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

        self.options["managed"] = process_bool_arg(self.options.get("managed", False))
        self.api_version = (
            self.options.get("api_version")
            or self.project_config.project__package__api_version
        )
        try:
            float(self.api_version)
        except ValueError:
            raise TaskOptionsError(f"Invalid API version {self.api_version}")

    def _inject_namespace(self, text):
        """Inject the namespace into the given text if running in managed mode."""
        return inject_namespace(
            "", text, self.options.get("namespace_inject"), self.options["managed"]
        )[1]

    @abstractmethod
    def _get_package_xml_content(self, operation):
        """Return the textual content of a package.xml for the given operation."""
        pass

    def _generate_package_xml(self, operation):
        """Call _get_package_xml_content() and perform namespace injection if needed"""
        return self._inject_namespace(self._get_package_xml_content(operation))

    def _create_directories(self, tempdir):
        """Create self.retrieve_dir and self.deploy_dir, if required"""
        if self.retrieve:
            self.retrieve_dir = Path(tempdir, "retrieve")
            self.retrieve_dir.mkdir()
        if self.deploy:
            self.deploy_dir = Path(tempdir, "deploy")
            self.deploy_dir.mkdir()

    def _retrieve(self):
        """Retrieve metadata into self.retrieve_dir"""
        self.logger.info("Extracting existing metadata...")
        api_retrieve = ApiRetrieveUnpackaged(
            self,
            self._generate_package_xml(MetadataOperation.RETRIEVE),
            self.api_version,
        )
        unpackaged = api_retrieve()
        unpackaged.extractall(self.retrieve_dir)

    @abstractmethod
    def _transform(self):
        """Transform the metadata in self.retrieve_dir into self.deploy_dir."""
        pass

    def _deploy(self):
        """Deploy metadata from self.deploy_dir"""
        self.logger.info("Loading transformed metadata...")
        target_profile_xml = Path(self.deploy_dir, "package.xml")
        target_profile_xml.write_text(
            self._generate_package_xml(MetadataOperation.DEPLOY)
        )

        # import is here to avoid an import cycle
        from cumulusci.tasks.salesforce import Deploy

        api = Deploy(
            self.project_config,
            TaskConfig(
                {
                    "options": {
                        "path": self.deploy_dir,
                        "namespace_inject": self.options.get("namespace_inject"),
                        "unmanaged": not self.options.get("managed"),
                    }
                }
            ),
            self.org_config,
        )
        result = api()

        return result

    def _post_deploy(self, result):
        """Run any post-deploy logic required, such as waiting for asynchronous
        operations to complete in the target org."""
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


class BaseMetadataSynthesisTask(BaseMetadataETLTask, metaclass=ABCMeta):
    """Base class for Metadata ETL tasks that generate new metadata
    and deploy it into the org, but do not retrieve."""

    deploy = True

    def _generate_package_xml(self, deploy):
        """Synthesize a package.xml for generated metadata."""
        generator = PackageXmlGenerator(str(self.deploy_dir), self.api_version)
        return generator()

    def _transform(self):
        self._synthesize()

    @abstractmethod
    def _synthesize(self):
        """Create new metadata in self.deploy_dir."""
        pass


class BaseMetadataTransformTask(BaseMetadataETLTask, metaclass=ABCMeta):
    """Base class for Metadata ETL tasks that extract metadata,
    transform it, and deploy it back into the org."""

    retrieve = True
    deploy = True

    @abstractmethod
    def _get_entities(self):
        """Return a dict of Metadata API entities and API names to be transformed."""
        pass

    def _get_types_package_xml(self):
        """Generate package.xml content based on the return value of _get_entities()."""
        base = """    <types>
{members}
        <name>{name}</name>
    </types>
"""
        types = ""
        for entity, api_names in self._get_entities().items():
            members = "\n".join(
                f"        <members>{api_name}</members>"
                for api_name in sorted(api_names)
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

    @abstractmethod
    def _transform(self):
        pass


class MetadataSingleEntityTransformTask(BaseMetadataTransformTask, metaclass=ABCMeta):
    """Base class for a Metadata ETL task that affects one or more
    instances of a specific metadata entity. Concrete subclasses must set
    `entity` to the Metadata API entity transformed, and implement _transform_entity()."""

    entity = None

    task_options = {
        "api_names": {"description": "List of API names of entities to affect"},
        **BaseMetadataETLTask.task_options,
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        self.api_names = {
            self._inject_namespace(arg)
            for arg in process_list_arg(self.options.get("api_names", ["*"]))
        }
        self.api_names = {
            quote(arg, safe=" ") if arg != "*" else arg for arg in self.api_names
        }

    def _get_entities(self):
        return {self.entity: self.api_names}

    @abstractmethod
    def _transform_entity(self, metadata, api_name):
        """Accept an XML element corresponding to the metadata entity with
        the given api_name. Transform the XML and return the version which
        should be deployed, or None to suppress deployment of this entity."""
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
        source_metadata_dir = self.retrieve_dir / directory

        if "*" in self.api_names:
            # Walk the retrieved directory to get the actual suite
            # of API names retrieved and rebuild our api_names list.
            self.api_names.remove("*")
            self.api_names = self.api_names.union(
                metadata_file.stem
                for metadata_file in source_metadata_dir.iterdir()
                if metadata_file.suffix == f".{extension}"
            )

        removed_api_names = set()

        for api_name in self.api_names:
            # Page Layout names can contain spaces, but parentheses and other
            # characters like ' and < are quoted.
            # We quote user-specified API names so we can locate the corresponding
            # metadata files, but present them un-quoted in messages to the user.
            unquoted_api_name = unquote(api_name)

            path = source_metadata_dir / f"{api_name}.{extension}"
            if not path.exists():
                raise CumulusCIException(f"Cannot find metadata file {path}")

            try:
                tree = metadata_tree.parse(str(path))
            except SyntaxError as err:
                err.filename = path
                raise err
            transformed_xml = self._transform_entity(tree, unquoted_api_name)
            if transformed_xml:
                parent_dir = self.deploy_dir / directory
                if not parent_dir.exists():
                    parent_dir.mkdir()
                destination_path = parent_dir / f"{api_name}.{extension}"

                with destination_path.open(mode="w", encoding="utf-8") as f:
                    f.write(transformed_xml.tostring(xml_declaration=True))
            else:
                # Make sure to remove from our package.xml
                removed_api_names.add(api_name)

        self.api_names = self.api_names - removed_api_names


class UpdateMetadataFirstChildTextTask(MetadataSingleEntityTransformTask):
    task_docs = """
Metadata ETL task to update a single child element's text within metadata XML.

If the child doesn't exist, the child is created and appended to the Metadata.   Furthermore, the ``value`` option is namespaced injected if the task is properly configured.

Example: Assign a Custom Object's Compact Layout
------------------------------------------------

Researching `CustomObject <https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/customobject.htm>`_ in the Metadata API documentation or even retrieving the CustomObject's Metadata for inspection, we see the ``compactLayoutAssignment`` Field.  We want to assign a specific Compact Layout for our Custom Object, so we write the following CumulusCI task in our project's ``cumulusci.yml``.

.. code-block::  yaml

  tasks:
      assign_compact_layout:
          class_path: cumulusci.tasks.metadata_etl.UpdateMetadataFirstChildTextTask
          options:
              managed: False
              namespace_inject: $project_config.project__package__namespace
              entity: CustomObject
              api_names: OurCustomObject__c
              tag: compactLayoutAssignment
              value: "%%%NAMESPACE%%%DifferentCompactLayout"
              # We include a namespace token so it's easy to use this task in a managed context.

Suppose the original CustomObject metadata XML looks like:

.. code-block:: xml

  <?xml version="1.0" encoding="UTF-8"?>
  <CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
      ...
      <label>Our Custom Object</label>
      <compactLayoutAssignment>OriginalCompactLayout</compactLayoutAssignment>
      ...
  </CustomObject>

After running ``cci task run assign_compact_layout``, the CustomObject metadata XML is deployed as:

.. code-block:: xml

  <?xml version="1.0" encoding="UTF-8"?>
  <CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
      ...
      <label>Our Custom Object</label>
      <compactLayoutAssignment>DifferentCompactLayout</compactLayoutAssignment>
      ...
  </CustomObject>
    """

    task_options = {
        "metadata_type": {"description": "Metadata Type", "required": True},
        "tag": {
            "description": "Targeted tag. The text of the first instance of this tag within the metadata entity will be updated.",
            "required": True,
        },
        "value": {
            "description": "Desired value to set for the targeted tag's text. This value is namespace-injected.",
            "required": True,
        },
        **MetadataSingleEntityTransformTask.task_options,
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.entity = self.options.get("metadata_type")
        self.options["value"] = self._inject_namespace(self.options.get("value"))

    def _transform_entity(
        self, metadata: MetadataElement, api_name: str
    ) -> MetadataElement:
        """Finds metadata's first child with tag.  If no child is found, appends
        a new child with tag.  Then updates child's text as the value option."""
        tag = self.options["tag"]

        child = metadata.find(tag)
        if child is None:
            child = metadata.append(tag)

        child.text = self.options["value"]

        self.logger.info(f'Updating {self.entity} "{api_name}":')
        self.logger.info(f'    {tag} as "{child.text}"')

        return metadata
