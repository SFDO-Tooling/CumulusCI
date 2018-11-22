from __future__ import unicode_literals
from collections import OrderedDict
from distutils.version import LooseVersion
import os

import raven

import cumulusci
from cumulusci.core.utils import ordered_yaml_load, merge_config
from cumulusci.core.config import BaseTaskFlowConfig
from cumulusci.core.exceptions import (
    ConfigError,
    DependencyResolutionError,
    KeychainNotFound,
    ServiceNotConfigured,
    ServiceNotValid,
    NotInProject,
    ProjectConfigNotFound,
)
from cumulusci.core.github import get_github_api
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

        super(BaseProjectConfig, self).__init__(config=config)

    @property
    def config_project_local_path(self):
        path = os.path.join(self.project_local_dir, self.config_filename)
        if os.path.isfile(path):
            return path

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
                "The file {} was not found in the repo root: {}. Are you in a CumulusCI Project directory?".format(
                    self.config_filename, repo_root
                )
            )

        # Load the project's yaml config file
        with open(self.config_project_path, "r") as f_config:
            project_config = ordered_yaml_load(f_config)

        if project_config:
            self.config_project.update(project_config)

        # Load the local project yaml config file if it exists
        if self.config_project_local_path:
            with open(self.config_project_local_path, "r") as f_local_config:
                local_config = ordered_yaml_load(f_local_config)
            if local_config:
                self.config_project_local.update(local_config)

        # merge in any additional yaml that was passed along
        if self.additional_yaml:
            additional_yaml_config = ordered_yaml_load(self.additional_yaml)
            if additional_yaml_config:
                self.config_additional_yaml.update(additional_yaml_config)

        self.config = merge_config(
            OrderedDict(
                [
                    ("global_config", self.config_global),
                    ("global_local", self.config_global_local),
                    ("project_config", self.config_project),
                    ("project_local_config", self.config_project_local),
                    ("additional_yaml", self.config_additional_yaml),
                ]
            )
        )

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

        # Apply CUMULUSCI_REPO_* environment variables last so they can
        # override and fill in missing values from the CI environment
        repo_branch = os.environ.get("CUMULUSCI_REPO_BRANCH")
        if repo_branch:
            if repo_branch != info.get("branch"):
                self.logger.info(
                    "CUMULUSCI_REPO_BRANCH found, using its value as the branch"
                )
            info["branch"] = repo_branch
        repo_commit = os.environ.get("CUMULUSCI_REPO_COMMIT")
        if repo_commit:
            if repo_commit != info.get("commit"):
                self.logger.info(
                    "CUMULUSCI_REPO_COMMIT found, using its value as the commit"
                )
            info["commit"] = repo_commit
        repo_root = os.environ.get("CUMULUSCI_REPO_ROOT")
        if repo_root:
            if repo_root != info.get("root"):
                self.logger.info(
                    "CUMULUSCI_REPO_ROOT found, using its value as the repo root"
                )
            info["root"] = repo_root
        repo_url = os.environ.get("CUMULUSCI_REPO_URL")
        if repo_url:
            if repo_url != info.get("url"):
                self.logger.info(
                    "CUMULUSCI_REPO_URL found, using its value as the repo url, owner, and name"
                )
            url_info = self._split_repo_url(repo_url)
            info.update(url_info)

        # If running in a CI environment, make sure we have all the needed
        # git info or throw a ConfigError
        if info["ci"]:
            validate = OrderedDict(
                (
                    # <key>, <env var to manually override>
                    ("branch", "CUMULUSCI_REPO_BRANCH"),
                    ("commit", "CUMULUSCI_REPO_COMMIT"),
                    ("name", "CUMULUSCI_REPO_URL"),
                    ("owner", "CUMULUSCI_REPO_URL"),
                    ("root", "CUMULUSCI_REPO_ROOT"),
                    ("url", "CUMULUSCI_REPO_URL"),
                )
            )
            for key, env_var in list(validate.items()):
                if key not in info or not info[key]:
                    message = "Detected CI on {} but could not determine the repo {}".format(
                        info["ci"], key
                    )
                    if env_var:
                        message += ". You can manually pass in the {} with".format(key)
                        message += " with the {} environment variable.".format(env_var)
                    raise ConfigError(message)

        # Log any overrides detected through the environment as a warning
        if len(info) > 1:
            self.logger.info("")
            self.logger.warning("Using environment variables to override repo info:")
            keys = list(info.keys())
            keys.sort()
            for key in keys:
                self.logger.warning("  {}: {}".format(key, info[key]))
            self.logger.info("")

        self._repo_info = info
        return self._repo_info

    def _split_repo_url(self, url):
        url_parts = url.split("/")
        name = url_parts[-1]
        owner = url_parts[-2]
        if name.endswith(".git"):
            name = name[:-4]
        git_info = {"url": url, "owner": owner, "name": name}
        return git_info

    @property
    def repo_root(self):
        path = self.repo_info.get("root")
        if path:
            return path

        path = os.path.splitdrive(os.getcwd())[1]
        while True:
            if os.path.isdir(os.path.join(path, ".git")):
                return path
            head, tail = os.path.split(path)
            if not tail:
                # reached the root
                break
            path = head

    @property
    def repo_name(self):
        name = self.repo_info.get("name")
        if name:
            return name

        if not self.repo_root:
            return

        in_remote_origin = False
        with open(os.path.join(self.repo_root, ".git", "config"), "r") as f:
            for line in f:
                line = line.strip()
                if line == '[remote "origin"]':
                    in_remote_origin = True
                    continue
                if in_remote_origin and line.find("url =") != -1:
                    return self._split_repo_url(line)["name"]

    @property
    def repo_url(self):
        url = self.repo_info.get("url")
        if url:
            return url

        if not self.repo_root:
            return

        git_config_file = os.path.join(self.repo_root, ".git", "config")
        with open(git_config_file, "r") as f:
            in_remote_origin = False
            for line in f:
                line = line.strip()
                if line == '[remote "origin"]':
                    in_remote_origin = True
                    continue
                if in_remote_origin and "url = " in line:
                    return line[len("url = ") :]

    @property
    def repo_owner(self):
        owner = self.repo_info.get("owner")
        if owner:
            return owner

        if not self.repo_root:
            return

        in_remote_origin = False
        with open(os.path.join(self.repo_root, ".git", "config"), "r") as f:
            for line in f:
                line = line.strip()
                if line == '[remote "origin"]':
                    in_remote_origin = True
                    continue
                if in_remote_origin and line.find("url =") != -1:
                    line_parts = line.split("/")
                    return line_parts[-2].split(":")[-1]

    @property
    def repo_branch(self):
        branch = self.repo_info.get("branch")
        if branch:
            return branch

        if not self.repo_root:
            return

        with open(os.path.join(self.repo_root, ".git", "HEAD"), "r") as f:
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

    @property
    def use_sentry(self):
        try:
            self.keychain.get_service("sentry")
            return True
        except ServiceNotConfigured:
            return False
        except ServiceNotValid:
            return False

    def init_sentry(self,):
        """ Initializes sentry.io error logging for this session """
        if not self.use_sentry:
            return

        sentry_config = self.keychain.get_service("sentry")

        tags = {
            "repo": self.repo_name,
            "branch": self.repo_branch,
            "commit": self.repo_commit,
            "cci version": cumulusci.__version__,
        }
        tags.update(self.config.get("sentry_tags", {}))

        env = self.config.get("sentry_environment", "CumulusCI CLI")

        self.sentry = raven.Client(
            dsn=sentry_config.dsn,
            environment=env,
            tags=tags,
            processors=("raven.processors.SanitizePasswordsProcessor",),
        )

    # Skipping coverage because the module structure
    # makes it hard to patch our get_github_api global
    def get_github_api(self):  # pragma: nocover
        github_config = self.keychain.get_service("github")
        gh = get_github_api(github_config.username, github_config.password)
        return gh

    def get_latest_version(self, beta=False):
        """ Query Github Releases to find the latest production or beta release """
        gh = self.get_github_api()
        repo = gh.repository(self.repo_owner, self.repo_name)
        latest_version = None
        for release in repo.releases():
            if beta != release.tag_name.startswith(self.project__git__prefix_beta):
                continue
            version = self.get_version_for_tag(release.tag_name)
            if version is None:
                continue
            version = LooseVersion(version)
            if not latest_version or version > latest_version:
                latest_version = version
        return latest_version

    @property
    def config_project_path(self):
        if not self.repo_root:
            return
        path = os.path.join(self.repo_root, self.config_filename)
        if os.path.isfile(path):
            return path

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
        if name is None:
            name = (
                ""
            )  # not entirely sure why this was happening in tests but this is the goal...

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

    def get_static_dependencies(self, dependencies=None, include_beta=None):
        """Resolves the project -> dependencies section of cumulusci.yml
            to convert dynamic github dependencies into static dependencies
            by inspecting the referenced repositories

        Keyword arguments:
        :param dependencies: a list of dependencies to resolve
        :param include_beta: when true, return the latest github release,
            even if pre-release; else return the latest stable release
        """
        if not dependencies:
            dependencies = self.project__dependencies

        if not dependencies:
            return

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
            prefix = "{}  - ".format(" " * indent)
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
                    value = "\n{}".format(" " * (indent + 4))

                if key == "repo":
                    pretty.append("{}{}: {}".format(prefix, key, value.full_name))
                else:
                    pretty.append("{}{}: {}".format(prefix, key, value))
                if extra:
                    pretty.extend(extra)
                prefix = "{}    ".format(" " * indent)
        return pretty

    def process_github_dependency(self, dependency, indent=None, include_beta=None):
        if not indent:
            indent = ""

        self.logger.info(
            "{}Processing dependencies from Github repo {}".format(
                indent, dependency["github"]
            )
        )

        skip = dependency.get("skip")
        if not isinstance(skip, list):
            skip = [skip]

        # Initialize github3.py API against repo
        gh = self.get_github_api()
        repo_owner, repo_name = dependency["github"].split("/")[3:5]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]
        repo = gh.repository(repo_owner, repo_name)

        # Determine the ref if specified
        kwargs = {}
        if "tag" in dependency:
            tag = dependency["tag"]
            kwargs["ref"] = tag
        else:
            tag = None

        # Get the cumulusci.yml file
        contents = repo.file_contents("cumulusci.yml", **kwargs)
        cumulusci_yml = ordered_yaml_load(contents.decoded)

        # Get the namespace from the cumulusci.yml if set
        namespace = cumulusci_yml.get("project", {}).get("package", {}).get("namespace")

        # Check for unmanaged flag on a namespaced package
        unmanaged = namespace and dependency.get("unmanaged") is True

        # Look for subfolders under unpackaged/pre
        unpackaged_pre = []
        try:
            contents = repo.directory_contents(
                "unpackaged/pre", return_as=dict, **kwargs
            )
        except NotFoundError:
            contents = None
        if contents:
            for dirname in list(contents.keys()):
                subfolder = "unpackaged/pre/{}".format(dirname)
                if subfolder in skip:
                    continue

                unpackaged_pre.append(
                    {
                        "repo": repo,
                        "ref": tag,
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
            contents = repo.directory_contents("src", **kwargs)
            if contents:
                subfolder = "src"

                unmanaged_src = {
                    "repo": repo,
                    "ref": tag,
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
                "unpackaged/post", return_as=dict, **kwargs
            )
        except NotFoundError:
            contents = None
        if contents:
            for dirname in list(contents.keys()):
                subfolder = "unpackaged/post/{}".format(dirname)
                if subfolder in skip:
                    continue

                dependency = {
                    "repo": repo,
                    "ref": tag,
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
        prefix_beta = project.get("git", {}).get("prefix_beta", "beta/")
        prefix_release = project.get("git", {}).get("prefix_release", "release/")
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
            version = None
            if tag:
                version = self.get_version_for_tag(tag, prefix_beta, prefix_release)
            else:
                version = self._find_release_version(repo, indent, include_beta)

            if not version:
                raise DependencyResolutionError(
                    "{}Could not find latest release for {}".format(indent, namespace)
                )
            # If a latest prod version was found, make the dependencies a
            # child of that install
            dependency = {"namespace": namespace, "version": version}
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

    def _find_release_version(self, repo, indent, include_beta=None):
        version = None
        if include_beta:
            latest_release = next(repo.releases())
            version = latest_release.name
        else:
            # github3.py doesn't support the latest release api so we hack
            # it together here
            url = repo._build_url("releases/latest", base_url=repo._api)
            try:
                version = repo._get(url).json()["name"]
            except Exception as e:
                self.logger.warning(
                    "{}{}: {}".format(indent, e.__class__.__name__, str(e))
                )
        return version
