import json
import os
import pathlib
import re
import sys
import types
from configparser import ConfigParser
from contextlib import contextmanager
from io import StringIO
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Union

from cumulusci.core.config.base_config import BaseConfig
from cumulusci.core.debug import get_debug_mode
from cumulusci.core.versions import PackageVersionNumber
from cumulusci.plugins.plugin_loader import load_plugins
from cumulusci.utils.version_strings import LooseVersion

API_VERSION_RE = re.compile(r"^\d\d+\.0$")

from pydantic import ValidationError

from cumulusci.core.config import FlowConfig, TaskConfig
from cumulusci.core.config.base_task_flow_config import BaseTaskFlowConfig
from cumulusci.core.exceptions import (
    ConfigError,
    CumulusCIException,
    KeychainNotFound,
    NamespaceNotFoundError,
    NotInProject,
    ProjectConfigNotFound,
    VcsException,
)
from cumulusci.core.source import LocalFolderSource, NullSource
from cumulusci.core.utils import merge_config
from cumulusci.utils.fileutils import FSResource, open_fs_resource
from cumulusci.utils.git import current_branch, generic_parse_repo_url, git_path
from cumulusci.utils.yaml.cumulusci_yml import (
    LocalFolderSourceModel,
    VCSSourceModel,
    cci_safe_load,
)
from cumulusci.vcs.models import AbstractRepo
from cumulusci.vcs.vcs_source import VCSSource

sys.modules.setdefault(
    "tasks", types.ModuleType("tasks", "Synthetic package for all repo tasks")
)
import tasks

tasks.__path__ = []

if TYPE_CHECKING:
    from cumulusci.core.config.universal_config import UniversalConfig
    from cumulusci.core.keychain.base_project_keychain import BaseProjectKeychain
    from cumulusci.vcs.base import VCSService


class ProjectConfigPropertiesMixin(BaseConfig):
    """Mixin for shared properties used by ProjectConfigs and UniversalConfigs"""

    cli: dict
    services: dict
    project: dict
    cumulusci: dict
    orgs: dict
    minimum_cumulusci_version: str
    sources: dict
    flows: dict
    plans: dict
    tasks: dict
    plugins: dict
    dev_config: dict  # this is not documented and should be deprecated


class BaseProjectConfig(BaseTaskFlowConfig, ProjectConfigPropertiesMixin):
    """Base class for a project's configuration which extends the global config"""

    config_filename = "cumulusci.yml"
    universal_config_obj: "UniversalConfig"
    keychain: Optional["BaseProjectKeychain"]
    _repo_info: Dict[str, Any]
    config_project: dict
    config_project_local: dict
    config_additional_yaml: dict
    config_plugins_yaml: dict
    additional_yaml: Optional[str]
    source: Union[NullSource, VCSSource, LocalFolderSource]
    _cache_dir: Optional[Path]
    included_sources: Dict[
        Union[VCSSourceModel, LocalFolderSourceModel],
        "BaseProjectConfig",
    ]

    def __init__(
        self,
        universal_config_obj: "UniversalConfig",
        config: Optional[dict] = None,
        cache_dir: Optional[Path] = None,
        *args,
        **kwargs,
    ):
        self.universal_config_obj = universal_config_obj
        self.keychain = None

        # optionally pass in a repo_info dict
        self._repo_info = kwargs.pop("repo_info", None)

        if not config:
            config = {}

        # Initialize the dictionaries for the individual configs
        self.config_project = {}
        self.config_project_local = {}
        self.config_additional_yaml = {}
        self.config_plugins_yaml = {}

        # optionally pass in a kwarg named 'additional_yaml' that will
        # be added to the YAML merge stack.
        # Called from MetaCI in metaci/cumulusci/config.py
        # https://github.com/SFDO-Tooling/MetaCI/blob/36a0f4654/metaci/cumulusci/config.py#L8-L11
        self.additional_yaml = None
        if "additional_yaml" in kwargs:
            self.additional_yaml = kwargs.pop("additional_yaml")

        # initialize map of project configs referenced from an external source
        self.source = NullSource()
        self.included_sources = kwargs.pop("included_sources", {})

        # Store requested cache directory, which may be our parent's if we are a subproject
        self._cache_dir = cache_dir

        super().__init__(config=config)

    @property
    def config_project_local_path(self) -> Optional[str]:
        path = Path(self.project_local_dir) / self.config_filename
        if path.is_file():
            return str(path)

    def _load_config(self):
        """Loads the configuration from YAML, if no override config was passed in initially."""

        if (
            self.config
        ):  # any config being pre-set at init will short circuit out, but not a plain {}
            return

        # Verify that we're in a project
        repo_root = self.repo_root
        if not repo_root:
            raise NotInProject(
                "No git repository was found in the current path. You must be in a git repository to set up and use CCI for a project."
            )

        # Verify that the project's root has a config file
        if not self.config_project_path:
            raise ProjectConfigNotFound(
                f"The file {self.config_filename} was not found in the repo root: {repo_root}. Are you in a CumulusCI Project directory?"
            )

        # Load the project's yaml config file
        project_config = cci_safe_load(self.config_project_path, logger=self.logger)

        if project_config:
            self.config_project.update(project_config)

        # Load the local project yaml config file if it exists
        if self.config_project_local_path:
            local_config = cci_safe_load(
                self.config_project_local_path, logger=self.logger
            )
            if local_config:
                self.config_project_local.update(local_config)

        # merge in any additional yaml that was passed along
        if self.additional_yaml:
            additional_yaml_config = cci_safe_load(
                StringIO(self.additional_yaml),
                self.config_project_path,
                logger=self.logger,
            )
            if additional_yaml_config:
                self.config_additional_yaml.update(additional_yaml_config)

        # Loading plugins as classes are loaded and available.
        plugins = load_plugins(self.logger)

        # Load the plugin yaml config file if it exists
        for plugin in plugins:
            if plugin.plugin_project_config:
                self.config_plugins_yaml.update(plugin.plugin_project_config)
                self.logger.info(
                    f"Loaded plugin: {plugin.name} ({plugin.api_name}) v{plugin.version}"
                )

            plugin.teardown()  # clean up the plugin

        self.config = merge_config(
            {
                "universal_config": self.config_universal,
                "global_config": self.config_global,
                "project_config": self.config_project,
                "project_local_config": self.config_project_local,
                "additional_yaml": self.config_additional_yaml,
                "plugins_config": self.config_plugins_yaml,
            }
        )

        self._validate_config()

    def _validate_config(self):
        """Performs validation checks on the configuration"""
        self._validate_package_api_format()

    def _validate_package_api_format(self):
        api_version = str(self.project__package__api_version)

        if not API_VERSION_RE.match(api_version):
            message = (
                f"Package API Version must be in the form 'XX.0', found: {api_version}"
            )
            raise ConfigError(message)

    @property
    def config_global(self) -> dict:
        return self.universal_config_obj.config_global

    @property
    def config_universal(self) -> dict:
        return self.universal_config_obj.config_universal

    @property
    def repo_info(self) -> Dict[str, Any]:
        if self._repo_info is not None:
            return self._repo_info

        # Detect if we are running in a CI environment and get repo info
        # from env vars for the environment instead of .git files
        info = {"ci": None}

        # Make sure that the CUMULUSCI_AUTO_DETECT environment variable is
        # set before trying to auto-detect anything from the environment
        if not os.environ.get("CUMULUSCI_AUTO_DETECT"):
            self._repo_info = info
            return self._repo_info

        # Heroku CI
        heroku_ci = os.environ.get("HEROKU_TEST_RUN_ID")
        if heroku_ci:
            info = {
                "branch": os.environ.get("HEROKU_TEST_RUN_BRANCH"),
                "commit": os.environ.get("HEROKU_TEST_RUN_COMMIT_VERSION"),
                "ci": "heroku",
                "root": "/app",
            }

        # Other CI environment implementations can be implemented here...

        self._apply_repo_env_var_overrides(info)

        if info["ci"]:
            self._validate_required_git_info(info)

        if len(info) > 1:
            self._log_detected_overrides_as_warning(info)

        self._repo_info = info
        return self._repo_info

    def _apply_repo_env_var_overrides(self, info: Dict[str, Any]):
        """Apply CUMULUSCI_REPO_* environment variables last so they can
        override and fill in missing values from the CI environment"""
        self._override_repo_env_var("CUMULUSCI_REPO_BRANCH", "branch", info)
        self._override_repo_env_var("CUMULUSCI_REPO_COMMIT", "commit", info)
        self._override_repo_env_var("CUMULUSCI_REPO_ROOT", "root", info)

        repo_url = os.environ.get("CUMULUSCI_REPO_URL")
        if repo_url:
            if repo_url != info.get("url"):
                self.logger.info(
                    "CUMULUSCI_REPO_URL found, using its value as the repo url, owner, and name"
                )

            url_info = {}
            (
                url_info["owner"],
                url_info["name"],
                url_info["domain"],
            ) = generic_parse_repo_url(repo_url)
            url_info["url"] = repo_url
            info.update(url_info)

    def get_repo_owner_host_from_url(self, repo_url) -> List[str]:
        """Returns the owner, repo_name, and host from the repository URL.
        The method should return a list containing the owner, repo_name and host."""
        try:
            vcs_service = self.get_service_type_for_repo(repo_url)
            parsed_url = vcs_service.parse_repo_url()
        except Exception:
            # Fallback to generic parsing if the service does not support it
            parsed_url = generic_parse_repo_url(repo_url)

        if len(parsed_url) < 3:
            raise CumulusCIException("Parsed repository URL is not in expected format.")

        return [parsed_url[0], parsed_url[1], parsed_url[2]]

    def _override_repo_env_var(
        self, repo_env_var: str, local_var: str, info: Dict[str, Any]
    ):
        env_value: Optional[str] = os.environ.get(repo_env_var)
        if env_value:
            if env_value != info.get(local_var):
                self.logger.info(
                    f"{repo_env_var} found, using its value for configuration."
                )
            info[local_var] = env_value

    def _validate_required_git_info(self, info: Dict[str, Any]):
        """Ensures that we have the required git info or throw a ConfigError"""
        validate = {
            # <key>: <env var to manually override>
            "branch": "CUMULUSCI_REPO_BRANCH",
            "commit": "CUMULUSCI_REPO_COMMIT",
            "name": "CUMULUSCI_REPO_URL",
            "owner": "CUMULUSCI_REPO_URL",
            "root": "CUMULUSCI_REPO_ROOT",
            "url": "CUMULUSCI_REPO_URL",
        }
        for key, env_var in list(validate.items()):
            if key not in info or not info[key]:
                message = f"Detected CI on {info['ci']} but could not determine the repo {key}"
                if env_var:
                    message += f". You can manually pass in the {key} "
                    message += f" with the {env_var} environment variable."
                raise ConfigError(message)

    def _log_detected_overrides_as_warning(self, info: Dict[str, Any]):
        self.logger.info("")
        self.logger.warning("Using environment variables to override repo info:")
        keys = list(info.keys())
        keys.sort()
        for key in keys:
            self.logger.warning(f"  {key}: {info[key]}")
        self.logger.info("")

    def git_config_remote_origin_url(self) -> Optional[str]:
        """Returns the url under the [remote origin]
        section of the .git/config file. Returns None
        if .git/config file not present or no matching
        line is found."""
        config = ConfigParser(strict=False)
        try:
            config.read(git_path(self.repo_root, "config"))
            url = config['remote "origin"']["url"]
        except (KeyError, TypeError):
            url = None
        return url

    @property
    def repo_root(self) -> Optional[str]:
        path = self.repo_info.get("root")
        if path:
            return path

        path = Path.cwd().resolve()
        paths = chain((path,), path.parents)
        for path in paths:
            if (path / ".git").is_dir():
                return str(path)

    @property
    def server_domain(self) -> Optional[str]:
        domain = self.repo_info.get("domain")

        if domain:
            return domain

        if not self.repo_root:
            return

        url_line = self.git_config_remote_origin_url()
        if url_line:
            return self.get_repo_owner_host_from_url(url_line)[2]

    @property
    def repo_name(self) -> Optional[str]:
        name = self.repo_info.get("name")
        if name:
            return name

        if not self.repo_root:
            return

        url_line = self.git_config_remote_origin_url()
        if url_line:
            return self.get_repo_owner_host_from_url(url_line)[1]

    @property
    def repo_url(self) -> Optional[str]:
        url = self.repo_info.get("url")
        if url:
            return url

        if not self.repo_root:
            return

        url = self.git_config_remote_origin_url()
        return url

    @property
    def repo_owner(self) -> Optional[str]:
        owner = self.repo_info.get("owner")
        if owner:
            return owner

        if not self.repo_root:
            return

        url_line = self.git_config_remote_origin_url()

        if url_line:
            return self.get_repo_owner_host_from_url(url_line)[0]

    @property
    def repo_branch(self) -> Optional[str]:
        branch = self.repo_info.get("branch")
        if branch:
            return branch

        if not self.repo_root:
            return

        return current_branch(self.repo_root)

    @property
    def repo_commit(self) -> Optional[str]:
        commit = self.repo_info.get("commit")
        if commit:
            return commit

        if not self.repo_root:
            return

        branch = self.repo_branch
        if branch:
            commit_file_path = pathlib.Path(self.repo_root) / ".git" / "refs" / "heads"
            commit_file_path = commit_file_path.joinpath(*branch.split("/"))
        else:
            # We're in detached HEAD mode; .git/HEAD contains the SHA
            commit_file_path = pathlib.Path(self.repo_root) / ".git" / "HEAD"

        if commit_file_path.exists() and commit_file_path.is_file():
            return commit_file_path.read_text().strip()
        else:
            if branch:
                packed_refs_path = os.path.join(self.repo_root, ".git", "packed-refs")
                with open(packed_refs_path, "r") as f:
                    for line in f:
                        parts = line.split(" ")
                        if len(parts) == 1:
                            # Skip lines showing the commit sha of a tag on the
                            # preceeding line
                            continue
                        if (
                            parts[1].replace("refs/remotes/origin/", "").strip()
                            == branch
                        ):
                            return parts[0]

    def get_repo(self) -> AbstractRepo:
        repo = self.repo_service.get_repository()
        if repo is None:
            raise VcsException(
                f"VCS repository not found or not authorized. ({self.repo_url})"
            )
        return repo

    def get_latest_tag(self, beta: bool = False) -> str:
        """Query Github Releases to find the latest production or beta tag"""
        from cumulusci.vcs.bootstrap import get_latest_tag

        repo = self.get_repo()
        return get_latest_tag(repo, beta)

    def get_latest_version(self, beta: bool = False) -> Optional[LooseVersion]:
        """Query Github Releases to find the latest production or beta release"""
        tag = self.get_latest_tag(beta)
        version = self.get_version_for_tag(tag)
        if version is not None:
            return LooseVersion(version)

    def get_previous_version(self) -> Optional[LooseVersion]:
        """Query GitHub releases to find the previous production release"""
        from cumulusci.vcs.bootstrap import find_previous_release

        repo = self.get_repo()
        release = find_previous_release(repo, self.project__git__prefix_release)
        if release is not None:
            return LooseVersion(self.get_version_for_tag(release.tag_name))

    @property
    def config_project_path(self) -> Optional[str]:
        if not self.repo_root:
            return
        path = Path(self.repo_root) / self.config_filename
        if path.is_file():
            return str(path)

    @property
    def project_local_dir(self) -> str:
        """location of the user local directory for the project
        e.g., ~/.cumulusci/NPSP-Extension-Test/"""

        # depending on where we are in bootstrapping the UniversalConfig
        # the canonical projectname could be located in one of two places
        if self.project__name:
            name = self.project__name
        else:
            name = self.config_project.get("project", {}).get("name", "")

        path = str(self.universal_config_obj.cumulusci_config_dir / name)
        if not os.path.isdir(path):
            os.makedirs(path)
        return path

    @property
    def default_package_path(self) -> Path:
        if self.project__source_format == "sfdx":
            relpath = "force-app"
            for pkg in self.sfdx_project_config.get("packageDirectories", []):
                if pkg.get("default"):
                    relpath = pkg["path"]
        else:
            relpath = "src"
        return Path(self.repo_root, relpath).resolve()

    @property
    def sfdx_project_config(self) -> Dict[str, Any]:
        with open(
            Path(self.repo_root) / "sfdx-project.json", "r", encoding="utf-8"
        ) as f:
            config = json.load(f)
        return config

    @property
    def allow_remote_code(self) -> bool:
        return self.source.allow_remote_code

    @property
    def repo_service(self):
        vcs_service = self.repo_info.get("vcs_service", None)
        if vcs_service:
            return vcs_service

        vcs_service = self.get_service_type_for_repo(self.repo_url)

        if vcs_service is None:
            raise VcsException("Provider class for not found in config")

        if self._repo_info:
            self._repo_info["vcs_service"] = vcs_service

        return vcs_service

    @repo_service.setter
    def repo_service(self, vcs_service: "VCSService"):
        """Set the VCS service for this project config."""
        from cumulusci.vcs.base import VCSService

        if not isinstance(vcs_service, VCSService):
            raise TypeError("repo_service must be an instance of VCSService")

        self._repo_info["vcs_service"] = vcs_service

    def get_service_type_for_repo(
        self, url: str, service_alias: Optional[str] = None
    ) -> "VCSService":
        from cumulusci.vcs.bootstrap import get_service_for_repo_url

        vcs_service = get_service_for_repo_url(self, url, service_alias=service_alias)
        vcs_service.logger = self.logger
        return vcs_service

    def get_tag_for_version(self, prefix: str, version: str) -> str:
        """Given a prefix and version, returns the appropriate tag name to use."""
        try:
            return PackageVersionNumber.parse(version).format_tag(prefix)
        except ValueError:
            return f"{prefix}{version}"

    def get_version_for_tag(
        self,
        tag: str,
        prefix_beta: Optional[str] = None,
        prefix_release: Optional[str] = None,
    ) -> Optional[str]:
        try:
            return PackageVersionNumber.parse_tag(
                tag,
                prefix_beta or self.project__git__prefix_beta,
                prefix_release or self.project__git__prefix_release,
            ).format()
        except ValueError:
            pass

    def set_keychain(self, keychain: "BaseProjectKeychain"):
        self.keychain = keychain

    def _check_keychain(self):
        if not self.keychain:
            raise KeychainNotFound(
                "Could not find config.keychain. You must call "
                + "config.set_keychain(keychain) before accessing orgs"
            )

    def get_repo_from_url(self, url: str) -> Optional[AbstractRepo]:
        from cumulusci.vcs.bootstrap import get_repo_from_url

        repo = get_repo_from_url(self, url)
        repo.logger = self.logger
        return repo

    def get_task(self, name: str) -> TaskConfig:
        """Get a TaskConfig by task name

        If the name has a colon, look for it in a different project config.
        """
        if ":" in name:
            ns, name = name.split(":")
            other_config = self.get_namespace(ns)
            task_config = other_config.get_task(name)
            task_config.project_config = other_config
        else:
            task_config = super().get_task(name)
            task_config.project_config = self
        return task_config

    def get_flow(self, name) -> FlowConfig:
        """Get a FlowConfig by flow name

        If the name has a colon, look for it in a different project config.
        """
        if ":" in name:
            ns, name = name.split(":")
            other_config = self.get_namespace(ns)
            flow_config = other_config.get_flow(name)
            flow_config.name = name
            flow_config.project_config = other_config
        else:
            flow_config = super().get_flow(name)
            flow_config.name = name
            flow_config.project_config = self
        return flow_config

    def get_namespace(self, ns: str) -> "BaseProjectConfig":
        """Look up another project config by its name in the `sources` config.

        Also makes sure the project has been fetched, if it's from an external source.
        """
        spec = self.lookup(f"sources__{ns}")
        if spec is None:
            raise NamespaceNotFoundError(f"Namespace not found: {ns}")

        return self.include_source(spec)

    def include_source(
        self,
        spec: Union[VCSSourceModel, LocalFolderSourceModel, dict],
    ) -> "BaseProjectConfig":
        """Make sure a project has been fetched from its source.

        This either fetches the project code and constructs its project config,
        or returns a project config that was previously loaded with the same spec.
        """

        if isinstance(spec, dict):
            parsed_spec = None
            source_models = VCSSource.registered_source_models()
            source_models.append(LocalFolderSourceModel)

            for model_class in source_models:
                try:
                    parsed_spec = model_class(**spec)
                except ValidationError:
                    pass
                except TypeError:
                    pass
                else:
                    break

            if not parsed_spec:
                raise ValueError(f"Invalid source spec: {spec}")

            spec = parsed_spec

        if spec in self.included_sources:
            project_config = self.included_sources[spec]
        else:
            if isinstance(spec, VCSSourceModel):
                source = VCSSource.create(self, spec)
            elif isinstance(spec, LocalFolderSourceModel):
                source = LocalFolderSource(self, spec)

            self.logger.info(f"Fetching from {source}")
            project_config = source.fetch()
            project_config.set_keychain(self.keychain)
            project_config.source = source
            self.included_sources[spec] = project_config

            # If I can't load remote code, make sure that my
            # included repos can't either.
            if not self.allow_remote_code:
                spec.allow_remote_code = False
            else:
                project_config._add_tasks_directory_to_python_path()

        return project_config

    def _add_tasks_directory_to_python_path(self):
        # https://stackoverflow.com/a/2700924/113477
        if not self.allow_remote_code:
            return False

        directory = str(Path(self.repo_root) / "tasks")
        if directory not in tasks.__path__:
            self.logger.debug(f"Adding {directory} to tasks.__path__")
            tasks.__path__.append(directory)
        if get_debug_mode():
            spec = getattr(self.source, "spec", ".")
            self.logger.debug(
                f"After importing {spec}:  tasks.__path__ {tasks.__path__}"
            )

    def construct_subproject_config(self, **kwargs) -> "BaseProjectConfig":
        """Construct another project config for an external source"""
        return self.__class__(
            self.universal_config_obj,
            included_sources=self.included_sources,
            cache_dir=self.cache_dir,
            **kwargs,
        )

    def relpath(self, path: str) -> str:
        """Convert path to be relative to the project repo root."""
        return os.path.relpath(os.path.join(self.repo_root, path))

    @property
    def cache_dir(self) -> Path:
        "A project cache which is on the local filesystem. Prefer open_cache where possible."
        if self._cache_dir:
            return self._cache_dir

        assert self.repo_root
        cache_dir = Path(self.repo_root, ".cci")
        cache_dir.mkdir(exist_ok=True)

        return cache_dir

    @contextmanager
    def open_cache(self, cache_name: str) -> Iterable[FSResource]:
        "A context managed PyFilesystem-based cache which could theoretically be on any filesystem."
        with open_fs_resource(self.cache_dir / cache_name) as cache_dir:
            cache_dir.mkdir(exist_ok=True, parents=True)
            yield cache_dir

    @classmethod
    def get_package_data(cls, config: "BaseProjectConfig"):
        namespace = config.project__package__namespace
        package_name = (
            config.project__package__name_managed
            or config.project__package__name
            or "Package"
        )

        return package_name, namespace


class RemoteProjectConfig(ProjectConfigPropertiesMixin):
    pass
