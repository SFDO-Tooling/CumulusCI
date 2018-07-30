from __future__ import unicode_literals
from collections import OrderedDict
from distutils.version import LooseVersion
import os

import hiyapyco
import raven

import cumulusci
from cumulusci.core.config import BaseTaskFlowConfig
from cumulusci.core.exceptions import ConfigError
from cumulusci.core.exceptions import DependencyResolutionError
from cumulusci.core.exceptions import KeychainNotFound
from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci.core.exceptions import ServiceNotValid
from cumulusci.core.github import get_github_api


class BaseProjectConfig(BaseTaskFlowConfig):
    """ Base class for a project's configuration which extends the global config """

    search_path = ['config']

    def __init__(self, global_config_obj, config=None):
        self.global_config_obj = global_config_obj
        self.keychain = None
        if not config:
            config = {}
        super(BaseProjectConfig, self).__init__(config=config)

    @property
    def config_global_local(self):
        return self.global_config_obj.config_global_local

    @property
    def config_global(self):
        return self.global_config_obj.config_global

    @property
    def repo_info(self):
        if hasattr(self, '_repo_info'):
            return self._repo_info

        # Detect if we are running in a CI environment and get repo info
        # from env vars for the enviornment instead of .git files
        info = {
            'ci': None
        }

        # Make sure that the CUMULUSCI_AUTO_DETECT environment variable is 
        # set before trying to auto-detect anything from the environment
        if not os.environ.get('CUMULUSCI_AUTO_DETECT'):
            self._repo_info = info
            return self._repo_info

        # Heroku CI
        heroku_ci = os.environ.get('HEROKU_TEST_RUN_ID')
        if heroku_ci:
            info = {
                'branch': os.environ.get('HEROKU_TEST_RUN_BRANCH'),
                'commit': os.environ.get('HEROKU_TEST_RUN_COMMIT_VERSION'),
                'ci': 'heroku',
                'root': '/app',
            }

        # Other CI environment implementations can be implemented here...

        # Apply CUMULUSCI_REPO_* environment variables last so they can
        # override and fill in missing values from the CI environment
        repo_branch = os.environ.get('CUMULUSCI_REPO_BRANCH')
        if repo_branch:
            if repo_branch != info.get('branch'):
                self.logger.info(
                    'CUMULUSCI_REPO_BRANCH found, using its value as the branch'
                )
            info['branch'] = repo_branch
        repo_commit = os.environ.get('CUMULUSCI_REPO_COMMIT')
        if repo_commit:
            if repo_commit != info.get('commit'):
                self.logger.info(
                    'CUMULUSCI_REPO_COMMIT found, using its value as the commit'
                )
            info['commit'] = repo_commit
        repo_root = os.environ.get('CUMULUSCI_REPO_ROOT')
        if repo_root:
            if repo_root != info.get('root'):
                self.logger.info(
                    'CUMULUSCI_REPO_ROOT found, using its value as the repo root'
                )
            info['root'] = repo_root
        repo_url = os.environ.get('CUMULUSCI_REPO_URL')
        if repo_url:
            if repo_url != info.get('url'):
                self.logger.info(
                    'CUMULUSCI_REPO_URL found, using its value as the repo url, owner, and name'
                )
            url_info = self._split_repo_url(repo_url)
            info.update(url_info)

        # If running in a CI environment, make sure we have all the needed
        # git info or throw a ConfigError
        if info['ci']:
            validate = OrderedDict((
                # <key>, <env var to manually override>
                ('branch', 'CUMULUSCI_REPO_BRANCH'),
                ('commit', 'CUMULUSCI_REPO_COMMIT'),
                ('name', 'CUMULUSCI_REPO_URL'),
                ('owner', 'CUMULUSCI_REPO_URL'),
                ('root', 'CUMULUSCI_REPO_ROOT'),
                ('url', 'CUMULUSCI_REPO_URL'),
            ))
            for key, env_var in list(validate.items()):
                if key not in info or not info[key]:
                    message = 'Detected CI on {} but could not determine the repo {}'.format(
                        info['ci'],
                        key,
                    )
                    if env_var:
                        message += '. You can manually pass in the {} with'.format(key)
                        message += ' with the {} environment variable.'.format(env_var)
                    raise ConfigError(message)

        # Log any overrides detected through the environment as a warning
        if len(info) > 1:
            self.logger.info('')
            self.logger.warn(
                'Using environment variables to override repo info:'
            )
            keys = list(info.keys())
            keys.sort()
            for key in keys:
                self.logger.warn(
                    '  {}: {}'.format(key, info[key])
                )
            self.logger.info('')

        self._repo_info = info
        return self._repo_info

    def _split_repo_url(self, url):
        url_parts = url.split('/')
        name = url_parts[-1]
        owner = url_parts[-2]
        if name.endswith('.git'):
            name = name[:-4]
        git_info = {
            'url': url,
            'owner': owner,
            'name': name,
        }
        return git_info

    @property
    def repo_root(self):
        path = self.repo_info.get('root')
        if path:
            return path

        path = os.path.splitdrive(os.getcwd())[1]
        while True:
            if os.path.isdir(os.path.join(path, '.git')):
                return path
            head, tail = os.path.split(path)
            if not tail:
                # reached the root
                break
            path = head

    @property
    def repo_name(self):
        name = self.repo_info.get('name')
        if name:
            return name

        if not self.repo_root:
            return

        in_remote_origin = False
        with open(os.path.join(self.repo_root, '.git', 'config'), 'r') as f:
            for line in f:
                line = line.strip()
                if line == '[remote "origin"]':
                    in_remote_origin = True
                    continue
                if in_remote_origin and line.find('url =') != -1:
                    return self._split_repo_url(line)['name']

    @property
    def repo_url(self):
        url = self.repo_info.get('url')
        if url:
            return url

        if not self.repo_root:
            return

        git_config_file = os.path.join(self.repo_root, '.git', 'config')
        with open(git_config_file, 'r') as f:
            in_remote_origin = False
            for line in f:
                line = line.strip()
                if line == '[remote "origin"]':
                    in_remote_origin = True
                    continue
                if in_remote_origin and 'url = ' in line:
                    return line[7:]

    @property
    def repo_owner(self):
        owner = self.repo_info.get('owner')
        if owner:
            return owner

        if not self.repo_root:
            return

        in_remote_origin = False
        with open(os.path.join(self.repo_root, '.git', 'config'), 'r') as f:
            for line in f:
                line = line.strip()
                if line == '[remote "origin"]':
                    in_remote_origin = True
                    continue
                if in_remote_origin and line.find('url =') != -1:
                    line_parts = line.split('/')
                    return line_parts[-2].split(':')[-1]

    @property
    def repo_branch(self):
        branch = self.repo_info.get('branch')
        if branch:
            return branch

        if not self.repo_root:
            return

        with open(os.path.join(self.repo_root, '.git', 'HEAD'), 'r') as f:
            branch_ref = f.read().strip()
        if branch_ref.startswith('ref: '):
            return '/'.join(branch_ref[5:].split('/')[2:])

    @property
    def repo_commit(self):
        commit = self.repo_info.get('commit')
        if commit:
            return commit

        if not self.repo_root:
            return

        branch = self.repo_branch
        if not branch:
            return

        join_args = [self.repo_root, '.git', 'refs', 'heads']
        join_args.extend(branch.split('/'))
        commit_file = os.path.join(*join_args)

        commit_sha = None
        if os.path.isfile(commit_file):
            with open(commit_file, 'r') as f:
                commit_sha = f.read().strip()
        else:
            packed_refs_path = os.path.join(
                self.repo_root,
                '.git',
                'packed-refs'
            )
            with open(packed_refs_path, 'r') as f:
                for line in f:
                    parts = line.split(' ')
                    if len(parts) == 1:
                        # Skip lines showing the commit sha of a tag on the
                        # preceeding line
                        continue
                    if parts[1].replace('refs/remotes/origin/', '').strip() == branch:
                        commit_sha = parts[0]
                        break

        return commit_sha

    @property
    def use_sentry(self):
        try:
            self.keychain.get_service('sentry')
            return True
        except ServiceNotConfigured:
            return False
        except ServiceNotValid:
            return False

    def init_sentry(self, ):
        """ Initializes sentry.io error logging for this session """
        if not self.use_sentry:
            return

        sentry_config = self.keychain.get_service('sentry')

        tags = {
            'repo': self.repo_name,
            'branch': self.repo_branch,
            'commit': self.repo_commit,
            'cci version': cumulusci.__version__,
        }
        tags.update(self.config.get('sentry_tags', {}))

        env = self.config.get('sentry_environment', 'CumulusCI CLI')

        self.sentry = raven.Client(
            dsn=sentry_config.dsn,
            environment=env,
            tags=tags,
            processors=(
                'raven.processors.SanitizePasswordsProcessor',
            ),
        )

    def get_github_api(self):
        github_config = self.keychain.get_service('github')
        gh = get_github_api(github_config.username, github_config.password)
        return gh

    def get_latest_version(self, beta=False):
        """ Query Github Releases to find the latest production or beta release """
        gh = self.get_github_api()
        repo = gh.repository(self.repo_owner, self.repo_name)
        latest_version = None
        for release in repo.iter_releases():
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

        # depending on where we are in bootstrapping the YamlGlobalConfig
        # the canonical projectname could be located in one of two places
        if self.project__name:
            name = self.project__name
        else:
            try:
                name = self.config_project['project']['name']
            except KeyError:
                name = ''

        path = os.path.join(
            os.path.expanduser('~'),
            self.global_config_obj.config_local_dir,
            name,
        )
        if not os.path.isdir(path):
            os.makedirs(path)
        return path

    def get_tag_for_version(self, version):
        if '(Beta' in version:
            tag_version = version.replace(
                ' (', '-').replace(')', '').replace(' ', '_')
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
            version = tag.replace(prefix_beta, '')
            if '-Beta_' in version:
                # Beta tags are expected to be like "beta/1.0-Beta_1"
                # which is returned as "1.0 (Beta 1)"
                return version.replace('-', ' (').replace('_', ' ') + ')'
            else:
                return
        elif tag.startswith(prefix_release):
            return tag.replace(prefix_release, '')

    def set_keychain(self, keychain):
        self.keychain = keychain

    def _check_keychain(self):
        if not self.keychain:
            raise KeychainNotFound(
                'Could not find config.keychain. You must call ' +
                'config.set_keychain(keychain) before accessing orgs')

    def list_orgs(self):
        """ Returns a list of all org names for the project """
        self._check_keychain()
        return self.keychain.list_orgs()

    def get_org(self, name):
        """ Returns an OrgConfig for the given org_name """
        self._check_keychain()
        return self.keychain.get_org(name)

    def set_org(self, name, org_config):
        """ Creates or updates an org's oauth info """
        self._check_keychain()
        return self.keychain.set_org(name, org_config)

    def get_static_dependencies(self, dependencies=None):
        """ Resolves the project -> dependencies section of cumulusci.yml
            to convert dynamic github dependencies into static dependencies
            by inspecting the referenced repositories
        """
        if not dependencies:
            dependencies = self.project__dependencies

        if not dependencies:
            return

        static_dependencies = []
        for dependency in dependencies:
            if 'github' not in dependency:
                static_dependencies.append(dependency)
            else:
                static = self.process_github_dependency(dependency)
                static_dependencies.extend(static)
        return static_dependencies

    def pretty_dependencies(self, dependencies, indent=None):
        if not indent:
            indent = 0
        pretty = []
        for dependency in dependencies:
            prefix = '{}  - '.format(" " * indent)
            for key, value in list(dependency.items()):
                extra = []
                if value is None or value is False:
                    continue
                if key == 'dependencies':
                    extra = self.pretty_dependencies(
                        dependency['dependencies'], indent=indent + 4)
                    if not extra:
                        continue
                    value = '\n{}'.format(" " * (indent + 4))

                pretty.append('{}{}: {}'.format(prefix, key, value))
                if extra:
                    pretty.extend(extra)
                prefix = '{}    '.format(" " * indent)
        return pretty

    def process_github_dependency(self, dependency, indent=None):
        if not indent:
            indent = ''

        self.logger.info(
            '{}Processing dependencies from Github repo {}'.format(
                indent,
                dependency['github'],
            )
        )

        skip = dependency.get('skip')
        if not isinstance(skip, list):
            skip = [skip, ]

        # Initialize github3.py API against repo
        gh = self.get_github_api()
        repo_owner, repo_name = dependency['github'].split('/')[3:5]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        repo = gh.repository(repo_owner, repo_name)

        # Prepare HTTP auth header for requests calls to Github
        github = self.keychain.get_service('github')
        headers = {'Authorization': 'token {}'.format(github.password)}

        # Determine the ref if specified
        kwargs = {}
        if 'tag' in dependency:
            tag = dependency['tag']
            kwargs['ref'] = tag
        else:
            tag = None

        # Get the cumulusci.yml file
        contents = repo.contents('cumulusci.yml', **kwargs)
        cumulusci_yml = hiyapyco.load(contents.decoded, loglevel='INFO')

        # Get the namespace from the cumulusci.yml if set
        namespace = cumulusci_yml.get('project', {}).get(
            'package', {}).get('namespace')

        # Check for unmanaged flag on a namespaced package
        unmanaged = namespace and dependency.get('unmanaged') is True

        # Look for subfolders under unpackaged/pre
        unpackaged_pre = []
        contents = repo.contents('unpackaged/pre', **kwargs)
        if contents:
            for dirname in list(contents.keys()):
                if 'unpackaged/pre/{}'.format(dirname) in skip:
                    continue
                subfolder = "{}-{}/unpackaged/pre/{}".format(
                    repo.name, repo.default_branch, dirname)
                zip_url = "{}/archive/{}.zip".format(
                    repo.html_url, repo.default_branch)

                unpackaged_pre.append({
                    'zip_url': zip_url,
                    'subfolder': subfolder,
                    'headers': headers,
                    'unmanaged': dependency.get('unmanaged'),
                    'namespace_tokenize': dependency.get('namespace_tokenize'),
                    'namespace_inject': dependency.get('namespace_inject'),
                    'namespace_strip': dependency.get('namespace_strip'),
                })

        # Look for metadata under src (deployed if no namespace)
        unmanaged_src = None
        if unmanaged or not namespace:
            contents = repo.contents('src', **kwargs)
            if contents:
                zip_url = "{}/archive/{}.zip".format(
                    repo.html_url, repo.default_branch)
                subfolder = "{}-{}/src".format(repo.name, repo.default_branch)

                unmanaged_src = {
                    'zip_url': zip_url,
                    'subfolder': subfolder,
                    'headers': headers,
                    'unmanaged': dependency.get('unmanaged'),
                    'namespace_tokenize': dependency.get('namespace_tokenize'),
                    'namespace_inject': dependency.get('namespace_inject'),
                    'namespace_strip': dependency.get('namespace_strip'),
                }

        # Look for subfolders under unpackaged/post
        unpackaged_post = []
        contents = repo.contents('unpackaged/post', **kwargs)
        if contents:
            for dirname in list(contents.keys()):
                if 'unpackaged/post/{}'.format(dirname) in skip:
                    continue
                zip_url = "{}/archive/{}.zip".format(
                    repo.html_url, repo.default_branch)
                subfolder = "{}-{}/unpackaged/post/{}".format(
                    repo.name, repo.default_branch, dirname)

                dependency = {
                    'zip_url': zip_url,
                    'subfolder': subfolder,
                    'headers': headers,
                    'unmanaged': dependency.get('unmanaged'),
                    'namespace_tokenize': dependency.get('namespace_tokenize'),
                    'namespace_inject': dependency.get('namespace_inject'),
                    'namespace_strip': dependency.get('namespace_strip'),
                }
                # By default, we always inject the project's namespace into
                # unpackaged/post metadata
                if namespace and not dependency.get('namespace_inject'):
                    dependency['namespace_inject'] = namespace
                    dependency['unmanaged'] = unmanaged
                unpackaged_post.append(dependency)

        # Parse values from the repo's cumulusci.yml
        project = cumulusci_yml.get('project', {})
        prefix_beta = project.get('git', {}).get('prefix_beta', 'beta/')
        prefix_release = project.get('git', {}).get('prefix_release', 'release/')
        dependencies = project.get('dependencies')
        if dependencies:
            dependencies = self.get_static_dependencies(dependencies)

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
                # github3.py doesn't support the latest release API so we hack
                # it together here
                url = repo._build_url('releases/latest', base_url=repo._api)
                try:
                    version = repo._get(url).json()['name']
                except Exception as e:
                    self.logger.warn('{}{}: {}'.format(
                        indent, e.__class__.__name__, e.message))

            if not version:
                raise DependencyResolutionError(
                    '{}Could not find latest release for {}'.format(indent, namespace)
                )
            # If a latest prod version was found, make the dependencies a
            # child of that install
            dependency = {
                'namespace': namespace,
                'version': version,
            }
            if dependencies:
                dependency['dependencies'] = dependencies
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
