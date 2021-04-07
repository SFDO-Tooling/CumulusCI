import io

from github3.repos.repo import Repository

from cumulusci.core.config import BaseConfig
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.exceptions import DependencyResolutionError
from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load


def get_repo(github: str, context: BaseProjectConfig) -> Repository:
    repo = context.get_repo_from_url(github)
    if repo is None:
        raise DependencyResolutionError(
            f"GitHub repository {github} not found or not authorized."
        )

    return repo


def get_remote_project_config(repo: Repository, ref: str) -> BaseConfig:
    contents = repo.file_contents("cumulusci.yml", ref=ref)
    return BaseConfig(cci_safe_load(io.StringIO(contents.decoded.decode("utf-8"))))


def get_package_data(config: BaseConfig):
    namespace = config.project__package__namespace
    package_name = (
        config.project__package__name_managed
        or config.project__package__name
        or "Package"
    )

    return package_name, namespace
