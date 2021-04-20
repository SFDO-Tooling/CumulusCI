import functools
import io

from github3.repos.repo import Repository
from github3.exceptions import NotFoundError

from cumulusci.core.config import BaseConfig
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.exceptions import DependencyResolutionError
from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load


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
def get_remote_project_config(repo: Repository, ref: str) -> BaseConfig:
    contents = repo.file_contents("cumulusci.yml", ref=ref)
    contents_io = io.StringIO(contents.decoded.decode("utf-8"))
    contents_io.url = f"cumulusci.yml from {repo.owner}/{repo.name}"  # for logging
    return BaseConfig(cci_safe_load(contents_io))


def get_package_data(config: BaseConfig):
    namespace = config.project__package__namespace
    package_name = (
        config.project__package__name_managed
        or config.project__package__name
        or "Package"
    )

    return package_name, namespace
