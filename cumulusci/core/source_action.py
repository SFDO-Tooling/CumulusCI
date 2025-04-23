from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.source_control import SourceControlProvider
from cumulusci.core.source_interface.reference import ReferenceInterface
from cumulusci.core.source_interface.repository import RepositoryInterface
from cumulusci.core.source_interface.tag import TagInterface
from cumulusci.core.utils import import_global


# This action is basically to identify the SourceControlProvider. Not an source action in itself.
def get_provider(config) -> SourceControlProvider:
    """Returns the SourceControlProvider for the given config"""
    service_type = config.lookup("project__service_type")

    if service_type is None:
        service_type = "github"

    provider_path = config.services[service_type].get("class_path", None)
    if provider_path is not None:
        provider_klass = import_global(provider_path)
        return provider_klass

    raise CumulusCIException(f"Provider class for {service_type} not found in config")


def get_repository(self) -> RepositoryInterface:
    return self.provider.get_repository()


def get_ref_for_tag(repo: RepositoryInterface, tag_name: str) -> ReferenceInterface:
    """Gets a Reference object for the tag with the given name"""
    return repo.get_ref_for_tag(tag_name)


def get_tag_by_name(repo: RepositoryInterface, tag_name: str) -> TagInterface:
    """Fetches a tag by name from the given repository"""
    ref: ReferenceInterface = get_ref_for_tag(repo, tag_name)
    return repo.get_tag_by_ref(ref, tag_name)
