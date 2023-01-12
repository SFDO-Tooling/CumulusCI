import functools
import io
import re
from typing import Optional, Tuple

from github3.exceptions import NotFoundError
from github3.git import Tag
from github3.repos.repo import Repository

from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.exceptions import DependencyResolutionError
from cumulusci.core.versions import PackageType
from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load

PACKAGE_TYPE_RE = re.compile(r"^package_type: (.*)$", re.MULTILINE)
VERSION_ID_RE = re.compile(r"^version_id: (04t[a-zA-Z0-9]{12,15})$", re.MULTILINE)


def get_repo(github: str, context: BaseProjectConfig) -> Repository:
    try:
        repo = context.get_repo_from_url(github)
    except NotFoundError:
        repo = None

    if repo is None:
        raise DependencyResolutionError(
            f"We are unable to find the repository at {github}. Please make sure the URL is correct, that your GitHub user has read access to the repository, and that your GitHub personal access token includes the “repo” scope."
        )
    return repo


@functools.lru_cache(50)
def get_remote_project_config(repo: Repository, ref: str) -> BaseProjectConfig:
    contents = repo.file_contents("cumulusci.yml", ref=ref)
    contents_io = io.StringIO(contents.decoded.decode("utf-8"))
    contents_io.url = f"cumulusci.yml from {repo.owner}/{repo.name}"  # for logging
    return BaseProjectConfig(None, cci_safe_load(contents_io))


def get_package_data(config: BaseProjectConfig):
    namespace = config.project__package__namespace
    package_name = (
        config.project__package__name_managed
        or config.project__package__name
        or "Package"
    )

    return package_name, namespace


def get_package_details_from_tag(
    tag: Tag,
) -> Tuple[Optional[str], Optional[PackageType]]:
    message = tag.message
    version_id = VERSION_ID_RE.search(message)
    if version_id:
        version_id = version_id.group(1)
    package_type = PACKAGE_TYPE_RE.search(message)
    if package_type:
        package_type = PackageType(package_type.group(1))

    return version_id, package_type
