from distutils.version import LooseVersion
import io
import os
import re
from pathlib import Path
from configparser import ConfigParser

API_VERSION_RE = re.compile(r"^\d\d+\.0$")

import github3
import yaml

from cumulusci.core.utils import merge_config
from cumulusci.core.config import BaseTaskFlowConfig
from cumulusci.core.exceptions import (
    ConfigError,
    DependencyResolutionError,
    GithubException,
    KeychainNotFound,
    NamespaceNotFoundError,
    NotInProject,
    ProjectConfigNotFound,
)
from cumulusci.core.github import get_github_api_for_repo
from cumulusci.core.github import find_latest_release
from cumulusci.core.github import find_previous_release
from cumulusci.core.source import GitHubSource
from cumulusci.core.source import LocalFolderSource
from cumulusci.core.source import NullSource
from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load

from github3.exceptions import NotFoundError


class BaseProjectConfig(BaseTaskFlowConfig):
    """ Base class for a project's configuration which extends the global config """

    config_filename = "cumulusci.yml"

    def __init__(self, global_config_obj, config=None, *args, **kwargs):
        self.global_config_obj = global_config_obj
        self.keychain = None

        # optionally pass in a repo_info dict
        self._repo_info = kwargs.pop("repo_info", None)

        if not config:
            config = {}

        # Initialize the dictionaries for the individual configs
        self.config_project = {}
        self.config_project_local = {}
        self.config_additional_yaml = {}

        # optionally pass in a kwarg named 'additional_yaml' that will
        # be added to the YAML merge stack.
        self.additional_yaml = None
        if "additional_yaml" in kwargs:
            self.additional_yaml = kwargs.pop("additional_yaml")

        # initialize map of project configs referenced from an external source
        self.source = NullSource()
        self.included_sources = kwargs.pop("included_sources", {})

        super(BaseProjectConfig, self).__init__(config=config)

    @property
    def config_project_local_path(self):
        path = Path(self.project_local_dir) / self.config_filename
        if path.is_file():
            return str(path)

    def _load_config(self):
        """ Loads the configuration from YAML, if no override config was passed in initially. """

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
        with open(self.config_project_path, "r") as f_config:
            project_config = cci_safe_load(f_config)

        if project_config:
            self.config_project.update(project_config)

        # Load the local project yaml config file if it exists
        if self.config_project_local_path:
            with open(self.config_project_local_path, "r") as f_local_config:
                local_config = cci_safe_load(f_local_config)
            if local_config:
                self.config_project_local.update(local_config)

        # merge in any additional yaml that was passed along
        if self.additional_yaml:
            additional_yaml_config = yaml.safe_load(self.additional_yaml)
            if additional_yaml_config:
                self.config_additional_yaml.update(additional_yaml_config)

        self.config = merge_config(
            {
                "global_config": self.config_global,
                "global_local": self.config_global_local,
                "project_config": self.config_project,
                "project_local_config": self.config_project_local,
                "additional_yaml": self.config_additional_yaml,
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
    def config_global_local(self):
        return self.global_config_obj.config_global_local

    @property
    def config_global(self):
        return self.global_config_obj.config_global

    @property
    def repo_info(self):
        if self._repo_info is not None:
            return self._repo_info

        # Detect if we are running in a CI environment and get repo info
        # from env vars for the enviornment instead of .git files
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

    def _apply_repo_env_var_overrides(self, info):
        """ Apply CUMULUSCI_REPO_* environment variables last so they can
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
            url_info = self._split_repo_url(repo_url)
            info.update(url_info)

    def _override_repo_env_var(self, repo_env_var, local_var, info):
        repo_env_var = os.environ.get(repo_env_var)
        if repo_env_var:
            if repo_env_var != info.get(local_var):
                self.logger.info("{} found, using its value for configuration.")
            info[local_var] = repo_env_var

    def _validate_required_git_info(self, info):
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

    def _log_detected_overrides_as_warning(self, info):
        self.logger.info("")
        self.logger.warning("Using environment variables to override repo info:")
        keys = list(info.keys())
        keys.sort()
        for key in keys:
            self.logger.warning(f"  {key}: {info[key]}")
        self.logger.info("")

    def _split_repo_url(self, url):
        url_parts = url.rstrip("/").split("/")

        name = url_parts[-1]
        if name.endswith(".git"):
            name = name[:-4]

        owner = url_parts[-2]
        if "git@github.com" in url:  # ssh url
            owner = owner.split(":")[-1]

        return {"url": url, "owner": owner, "name": name}

    def git_path(self, tail=None):
        """Returns a Path to the .git directory in self.repo_root
        with tail appended (if present) or None if self.repo_root
        is not set."""
        path = None
        if self.repo_root:
            path = Path(self.repo_root) / ".git"
            if tail is not None:
                path = path / str(tail)
        return path

    def git_config_remote_origin_url(self):
        """Returns the url under the [remote origin]
        section of the .git/config file. Returns None
        if .git/config file not present or no matching
        line is found. """
        config = ConfigParser(strict=False)
        try:
            config.read(self.git_path("config"))
            url = config['remote "origin"']["url"]
        except (KeyError, TypeError):
            url = None
        return url

    @property
    def repo_root(self):
        path = self.repo_info.get("root")
        if path:
            return path

        path = Path(os.path.splitdrive(Path.cwd())[1])
        while True:
            if (path / ".git").is_dir():
                return str(path)
            head, tail = os.path.split(path)
            if not tail:
                # reached the root
                break
            path = Path(head)

    @property
    def repo_name(self):
        name = self.repo_info.get("name")
        if name:
            return name

        if not self.repo_root:
            return

        url_line = self.git_config_remote_origin_url()
        return self._split_repo_url(url_line)["name"]

    @property
    def repo_url(self):
        url = self.repo_info.get("url")
        if url:
            return url

        if not self.repo_root:
            return

        url = self.git_config_remote_origin_url()
        return url

    @property
    def repo_owner(self):
        owner = self.repo_info.get("owner")
        if owner:
            return owner

        if not self.repo_root:
            return

        url_line = self.git_config_remote_origin_url()
        return self._split_repo_url(url_line)["owner"]

    @property
    def repo_branch(self):
        branch = self.repo_info.get("branch")
        if branch:
            return branch

        if not self.repo_root:
            return

        with open(self.git_path("HEAD"), "r") as f:
            branch_ref = f.read().strip()
        if branch_ref.startswith("ref: "):
            return "/".join(branch_ref[5:].split("/")[2:])

    @property
    def repo_commit(self):
        commit = self.repo_info.get("commit")
        if commit:
            return commit

        if not self.repo_root:
            return

        branch = self.repo_branch
        if not branch:
            return

        join_args = [self.repo_root, ".git", "refs", "heads"]
        join_args.extend(branch.split("/"))
        commit_file = os.path.join(*join_args)

        commit_sha = None
        if os.path.isfile(commit_file):
            with open(commit_file, "r") as f:
                commit_sha = f.read().strip()
        else:
            packed_refs_path = os.path.join(self.repo_root, ".git", "packed-refs")
            with open(packed_refs_path, "r") as f:
                for line in f:
                    parts = line.split(" ")
                    if len(parts) == 1:
                        # Skip lines showing the commit sha of a tag on the
                        # preceeding line
                        continue
                    if parts[1].replace("refs/remotes/origin/", "").strip() == branch:
                        commit_sha = parts[0]
                        break

        return commit_sha

    def get_github_api(self, owner=None, repo=None):
        return get_github_api_for_repo(
            self.keychain, owner or self.repo_owner, repo or self.repo_name
        )

    def _get_repo(self):
        gh = self.get_github_api()
        repo = gh.repository(self.repo_owner, self.repo_name)
        if repo is None:
            raise GithubException(
                f"Github repository not found or not authorized. ({self.repo_url})"
            )
        return repo

    def get_latest_tag(self, beta=False):
        """ Query Github Releases to find the latest production or beta tag """
        repo = self._get_repo()
        if not beta:
            try:
                release = repo.latest_release()
            except github3.exceptions.NotFoundError:
                raise GithubException(f"No release found for repo {self.repo_url}")
            prefix = self.project__git__prefix_release
            if not release.tag_name.startswith(prefix):
                return self._get_latest_tag_for_prefix(repo, prefix)
            return release.tag_name
        else:
            return self._get_latest_tag_for_prefix(repo, self.project__git__prefix_beta)

    def _get_latest_tag_for_prefix(self, repo, prefix):
        for release in repo.releases():
            if not release.tag_name.startswith(prefix):
                continue
            return release.tag_name
        raise GithubException(
            f"No release found for {self.repo_url} with tag prefix {prefix}"
        )

    def get_latest_version(self, beta=False):
        """ Query Github Releases to find the latest production or beta release """
        tag = self.get_latest_tag(beta)
        version = self.get_version_for_tag(tag)
        if version is not None:
            return LooseVersion(version)

    def get_previous_version(self):
        """Query GitHub releases to find the previous production release"""
        repo = self._get_repo()
        release = find_previous_release(repo, self.project__git__prefix_release)
        if release is not None:
            return LooseVersion(self.get_version_for_tag(release.tag_name))

    @property
    def config_project_path(self):
        if not self.repo_root:
            return
        path = Path(self.repo_root) / self.config_filename
        if path.is_file():
            return str(path)

    @property
    def project_local_dir(self):
        """ location of the user local directory for the project
        e.g., ~/.cumulusci/NPSP-Extension-Test/ """

        # depending on where we are in bootstrapping the BaseGlobalConfig
        # the canonical projectname could be located in one of two places
        if self.project__name:
            name = self.project__name
        else:
            name = self.config_project.get("project", {}).get("name", "")

        path = os.path.join(
            os.path.expanduser("~"), self.global_config_obj.config_local_dir, name
        )
        if not os.path.isdir(path):
            os.makedirs(path)
        return path

    def get_tag_for_version(self, version):
        if "(Beta" in version:
            tag_version = version.replace(" (", "-").replace(")", "").replace(" ", "_")
            tag_name = self.project__git__prefix_beta + tag_version
        else:
            tag_name = self.project__git__prefix_release + version
        return tag_name

    def get_version_for_tag(self, tag, prefix_beta=None, prefix_release=None):
        if prefix_beta is None:
            prefix_beta = self.project__git__prefix_beta
        if prefix_release is None:
            prefix_release = self.project__git__prefix_release
        if tag.startswith(prefix_beta):
            version = tag.replace(prefix_beta, "")
            if "-Beta_" in version:
                # Beta tags are expected to be like "beta/1.0-Beta_1"
                # which is returned as "1.0 (Beta 1)"
                return version.replace("-", " (").replace("_", " ") + ")"
            else:
                return
        elif tag.startswith(prefix_release):
            return tag.replace(prefix_release, "")

    def set_keychain(self, keychain):
        self.keychain = keychain

    def _check_keychain(self):
        if not self.keychain:
            raise KeychainNotFound(
                "Could not find config.keychain. You must call "
                + "config.set_keychain(keychain) before accessing orgs"
            )

    def get_repo_from_url(self, url):
        splits = self._split_repo_url(url)
        gh = self.get_github_api(splits["owner"], splits["name"])
        repo = gh.repository(splits["owner"], splits["name"])

        return repo

    def get_ref_for_dependency(self, repo, dependency, include_beta=None):
        release = None
        if "ref" in dependency:
            ref = dependency["ref"]
        else:
            if "tag" in dependency:
                try:
                    # Find the github release corresponding to this tag.
                    release = repo.release_from_tag(dependency["tag"])
                except NotFoundError:
                    raise DependencyResolutionError(
                        f"No release found for tag {dependency['tag']}"
                    )
            else:
                release = find_latest_release(repo, include_beta)
            if release:
                ref = repo.tag(
                    repo.ref("tags/" + release.tag_name).object.sha
                ).object.sha
            else:
                self.logger.info(
                    f"No release found; using the latest commit from the {repo.default_branch} branch."
                )
                ref = repo.branch(repo.default_branch).commit.sha

        return (release, ref)

    def get_static_dependencies(self, dependencies=None, include_beta=None):
        """Resolves the project -> dependencies section of cumulusci.yml
        to convert dynamic github dependencies into static dependencies
        by inspecting the referenced repositories.

        Keyword arguments:
        :param dependencies: a list of dependencies to resolve
        :param include_beta: when true, return the latest github release, even if pre-release; else return the latest stable release
        """
        if not dependencies:
            dependencies = self.project__dependencies

        if not dependencies:
            return []

        static_dependencies = []
        for dependency in dependencies:
            if "github" not in dependency:
                static_dependencies.append(dependency)
            else:
                static = self.process_github_dependency(
                    dependency, include_beta=include_beta
                )
                static_dependencies.extend(static)
        return static_dependencies

    def pretty_dependencies(self, dependencies, indent=None):
        if not indent:
            indent = 0
        pretty = []
        for dependency in dependencies:
            prefix = f"{' ' * indent}  - "
            for key, value in sorted(dependency.items()):
                extra = []
                if value is None or value is False:
                    continue
                if key == "dependencies":
                    extra = self.pretty_dependencies(
                        dependency["dependencies"], indent=indent + 4
                    )
                    if not extra:
                        continue
                    value = f"\n{' ' * (indent + 4)}"

                pretty.append(f"{prefix}{key}: {value}")
                if extra:
                    pretty.extend(extra)
                prefix = f"{' ' * indent}    "
        return pretty

    def process_github_dependency(  # noqa: C901
        self, dependency, indent=None, include_beta=None
    ):
        if not indent:
            indent = ""

        self.logger.info(
            f"{indent}Processing dependencies from Github repo {dependency['github']}"
        )

        skip = dependency.get("skip")
        if not isinstance(skip, list):
            skip = [skip]

        # Initialize github3.py API against repo
        repo = self.get_repo_from_url(dependency["github"])
        if repo is None:
            raise DependencyResolutionError(
                f"{indent}Github repository {dependency['github']} not found or not authorized."
            )

        repo_owner = str(repo.owner)
        repo_name = repo.name

        # Determine the commit
        release, ref = self.get_ref_for_dependency(repo, dependency, include_beta)

        # Get the cumulusci.yml file
        contents = repo.file_contents("cumulusci.yml", ref=ref)
        cumulusci_yml = cci_safe_load(io.StringIO(contents.decoded.decode("utf-8")))

        # Get the namespace from the cumulusci.yml if set
        package_config = cumulusci_yml.get("project", {}).get("package", {})
        namespace = package_config.get("namespace")
        package_name = (
            package_config.get("name_managed")
            or package_config.get("name")
            or namespace
        )

        # Check for unmanaged flag on a namespaced package
        unmanaged = namespace and dependency.get("unmanaged") is True

        # Look for subfolders under unpackaged/pre
        unpackaged_pre = []
        try:
            contents = repo.directory_contents(
                "unpackaged/pre", return_as=dict, ref=ref
            )
        except NotFoundError:
            contents = None
        if contents:
            for dirname in list(contents.keys()):
                subfolder = f"unpackaged/pre/{dirname}"
                if subfolder in skip:
                    continue
                name = f"Deploy {subfolder}"

                unpackaged_pre.append(
                    {
                        "name": name,
                        "repo_owner": repo_owner,
                        "repo_name": repo_name,
                        "ref": ref,
                        "subfolder": subfolder,
                        "unmanaged": dependency.get("unmanaged"),
                        "namespace_tokenize": dependency.get("namespace_tokenize"),
                        "namespace_inject": dependency.get("namespace_inject"),
                        "namespace_strip": dependency.get("namespace_strip"),
                    }
                )

        # Look for metadata under src (deployed if no namespace)
        unmanaged_src = None
        if unmanaged or not namespace:
            contents = repo.directory_contents("src", ref=ref)
            if contents:
                subfolder = "src"

                unmanaged_src = {
                    "name": f"Deploy {package_name or repo_name}",
                    "repo_owner": repo_owner,
                    "repo_name": repo_name,
                    "ref": ref,
                    "subfolder": subfolder,
                    "unmanaged": dependency.get("unmanaged"),
                    "namespace_tokenize": dependency.get("namespace_tokenize"),
                    "namespace_inject": dependency.get("namespace_inject"),
                    "namespace_strip": dependency.get("namespace_strip"),
                }

        # Look for subfolders under unpackaged/post
        unpackaged_post = []
        try:
            contents = repo.directory_contents(
                "unpackaged/post", return_as=dict, ref=ref
            )
        except NotFoundError:
            contents = None
        if contents:
            for dirname in list(contents.keys()):
                subfolder = f"unpackaged/post/{dirname}"
                if subfolder in skip:
                    continue
                name = f"Deploy {subfolder}"

                dependency = {
                    "name": name,
                    "repo_owner": repo_owner,
                    "repo_name": repo_name,
                    "ref": ref,
                    "subfolder": subfolder,
                    "unmanaged": dependency.get("unmanaged"),
                    "namespace_tokenize": dependency.get("namespace_tokenize"),
                    "namespace_inject": dependency.get("namespace_inject"),
                    "namespace_strip": dependency.get("namespace_strip"),
                }
                # By default, we always inject the project's namespace into
                # unpackaged/post metadata
                if namespace and not dependency.get("namespace_inject"):
                    dependency["namespace_inject"] = namespace
                    dependency["unmanaged"] = unmanaged
                unpackaged_post.append(dependency)

        # Parse values from the repo's cumulusci.yml
        project = cumulusci_yml.get("project", {})
        dependencies = project.get("dependencies")
        if dependencies:
            dependencies = self.get_static_dependencies(
                dependencies, include_beta=include_beta
            )

        # Create the final ordered list of all parsed dependencies
        repo_dependencies = []

        # unpackaged/pre/*
        if unpackaged_pre:
            repo_dependencies.extend(unpackaged_pre)

        if namespace and not unmanaged:
            if release is None:
                raise DependencyResolutionError(
                    f"{indent}Could not find latest release for {namespace}"
                )
            version = release.name
            # If a latest prod version was found, make the dependencies a
            # child of that install
            dependency = {
                "name": f"Install {package_name or namespace} {version}",
                "namespace": namespace,
                "version": version,
            }
            if dependencies:
                dependency["dependencies"] = dependencies
            repo_dependencies.append(dependency)

        # Unmanaged metadata from src (if referenced repo doesn't have a
        # namespace)
        else:
            if dependencies:
                repo_dependencies.extend(dependencies)
            if unmanaged_src:
                repo_dependencies.append(unmanaged_src)

        # unpackaged/post/*
        if unpackaged_post:
            repo_dependencies.extend(unpackaged_post)

        return repo_dependencies

    def get_task(self, name):
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

    def get_flow(self, name):
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

    def get_namespace(self, ns):
        """Look up another project config by its name in the `sources` config.

        Also makes sure the project has been fetched, if it's from an external source.
        """
        spec = getattr(self, f"sources__{ns}")
        if spec is None:
            raise NamespaceNotFoundError(f"Namespace not found: {ns}")
        return self.include_source(spec)

    def include_source(self, spec):
        """Make sure a project has been fetched from its source.

        `spec` is a dict which contains different keys depending on the type of source:

        - `github` indicates a GitHubSource
        - `path` indicates a LocalFolderSource

        This either fetches the project code and constructs its project config,
        or returns a project config that was previously loaded with the same spec.
        """
        frozenspec = tuple(spec.items())
        if frozenspec in self.included_sources:
            project_config = self.included_sources[frozenspec]
        else:
            if "github" in spec:
                source = GitHubSource(self, spec)
            elif "path" in spec:
                source = LocalFolderSource(self, spec)
            else:
                raise Exception(f"Not sure how to load project: {spec}")
            self.logger.info(f"Fetching from {source}")
            project_config = source.fetch()
            project_config.set_keychain(self.keychain)
            project_config.source = source
            self.included_sources[frozenspec] = project_config
        return project_config

    def construct_subproject_config(self, **kwargs):
        """Construct another project config for an external source"""
        return self.__class__(
            self.global_config_obj, included_sources=self.included_sources, **kwargs
        )

    def relpath(self, path):
        """Convert path to be relative to the project repo root."""
        return os.path.relpath(os.path.join(self.repo_root, path))
