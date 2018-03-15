from __future__ import unicode_literals
from builtins import object
import base64
import datetime
import json
import logging
import os
import pickle
import re

from collections import OrderedDict

import hiyapyco
import raven
import sarge
from simple_salesforce import Salesforce
import yaml
import requests


from distutils.version import LooseVersion  # pylint: disable=import-error,no-name-in-module
from github3 import login
from Crypto import Random
from Crypto.Cipher import AES

import cumulusci
from cumulusci.core.exceptions import ConfigError
from cumulusci.core.exceptions import DependencyResolutionError
from cumulusci.core.exceptions import KeychainConnectedAppNotFound
from cumulusci.core.exceptions import KeychainNotFound
from cumulusci.core.exceptions import NotInProject
from cumulusci.core.exceptions import ProjectConfigNotFound
from cumulusci.core.exceptions import ScratchOrgException
from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci.core.exceptions import ServiceNotValid
from cumulusci.core.exceptions import SOQLQueryException
from cumulusci.oauth.salesforce import SalesforceOAuth2

__location__ = os.path.dirname(os.path.realpath(__file__))

# constants used by MetaCI
FAILED_TO_CREATE_SCRATCH_ORG = 'Failed to create scratch org'


class BaseConfig(object):
    """ Base class for all configuration objects """

    defaults = {}
    search_path = ['config']

    def __init__(self, config=None):
        if config is None:
            self.config = {}
        else:
            self.config = config
        self._init_logger()
        self._load_config()

    def _init_logger(self):
        """ Initializes self.logger """
        self.logger = logging.getLogger(__name__)

    def _load_config(self):
        """ Performs the logic to initialize self.config """
        pass

    def __getattr__(self, name):
        tree = name.split('__')
        if name.startswith('_'):
            raise AttributeError('Attribute {} not found'.format(name))
        value = None
        value_found = False
        for attr in self.search_path:
            config = getattr(self, attr)
            if len(tree) > 1:
                # Walk through the config dictionary using __ as a delimiter
                for key in tree[:-1]:
                    config = config.get(key)
                    if config is None:
                        break
            if config is None:
                continue

            if tree[-1] in config:
                value = config[tree[-1]]
                value_found = True
                break

        if value_found:
            return value
        else:
            return self.defaults.get(name)


class TaskConfig(BaseConfig):
    """ A task with its configuration merged """
    pass


class FlowConfig(BaseConfig):
    """ A flow with its configuration merged """
    pass


class BaseTaskFlowConfig(BaseConfig):
    """ Base class for all configs that contain tasks and flows """

    def list_tasks(self):
        """ Returns a list of task info dictionaries with keys 'name' and 'description' """
        tasks = []
        for task in list(self.tasks.keys()):
            task_info = self.tasks[task]
            if not task_info:
                task_info = {}
            tasks.append({
                'name': task,
                'description': task_info.get('description'),
            })
        return tasks

    def get_task(self, name):
        """ Returns a TaskConfig """
        config = getattr(self, 'tasks__{}'.format(name))
        return TaskConfig(config)

    def list_flows(self):
        """ Returns a list of flow info dictionaries with keys 'name' and 'description' """
        flows = []
        return flows

    def get_flow(self, name):
        """ Returns a FlowConfig """
        config = getattr(self, 'flows__{}'.format(name))
        return FlowConfig(config)


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
        gh = login(github_config.username, github_config.password)
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
        if not tag.startswith(prefix_beta) and not tag.startswith(prefix_release):
            return None

        if 'Beta' in tag:
            version = tag[len(prefix_beta):]
            version = version.replace('-', ' (').replace('_', ' ') + ')'
        else:
            version = tag[len(prefix_release):]
        return version

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

        # Determine the ref if specified
        kwargs = {}
        if 'tag' in dependency:
            tag = dependency['tag']
            kwargs['ref'] = tag
        else:
            tag = None

        # Get the cumulusci.yml file
        contents = repo.contents('cumulusci.yml', **kwargs)
        cumulusci_yml = hiyapyco.load(contents.decoded)

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
                    'unmanaged': dependency.get('unmanaged'),
                    'namespace_tokenize': dependency.get('namespace_tokenize'),
                    'namespace_inject': dependency.get('namespace_inject'),
                    'namespace_strip': dependency.get('namespace_strip'),
                }
                # By default, we always inject the project's namespace into
                # unpackaged/post metadata
                if namespace and not dependency.get('namespace_inject'):
                    dependency['namespace_inject'] = namespace
                    dependency['unmananged'] = unmanaged
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


class BaseGlobalConfig(BaseTaskFlowConfig):
    """ Base class for the global config which contains all configuration not specific to projects """
    project_config_class = BaseProjectConfig

    config_local_dir = '.cumulusci'

    def list_projects(self):
        """ Returns a list of project names """
        raise NotImplementedError('Subclasses must provide an implementation')

    def get_project_config(self):
        """ Returns a ProjectConfig for the given project """
        return self.project_config_class(self)

    def create_project(self, project_name, config):
        """ Creates a new project configuration and returns it """
        raise NotImplementedError('Subclasses must provide an implementation')


class ConnectedAppOAuthConfig(BaseConfig):
    """ Salesforce Connected App OAuth configuration """
    pass


class OrgConfig(BaseConfig):
    """ Salesforce org configuration (i.e. org credentials) """

    def __init__(self, config, name):
        self.name = name
        super(OrgConfig, self).__init__(config)

    def refresh_oauth_token(self, connected_app):
        client_id = self.client_id
        client_secret = self.client_secret
        if not client_id:
            client_id = connected_app.client_id
            client_secret = connected_app.client_secret
        sf_oauth = SalesforceOAuth2(
            client_id,
            client_secret,
            connected_app.callback_url,  # Callback url isn't really used for this call
            auth_site=self.instance_url,
        )
        resp = sf_oauth.refresh_token(self.refresh_token).json()
        if resp != self.config:
            self.config.update(resp)
        self._load_userinfo()

    @property
    def lightning_base_url(self):
        return self.instance_url.split('.')[0] + '.lightning.force.com'

    @property
    def start_url(self):
        start_url = '%s/secur/frontdoor.jsp?sid=%s' % (
            self.instance_url, self.access_token)
        return start_url

    @property
    def user_id(self):
        return self.id.split('/')[-1]

    @property
    def org_id(self):
        return self.id.split('/')[-2]

    @property
    def username(self):
        """ Username for the org connection. """
        username = self.config.get('username')
        if not username:
            username = self.userinfo__preferred_username
        return username

    def load_userinfo(self):
        self._load_userinfo()

    def _load_userinfo(self):
        headers = {"Authorization": "Bearer " + self.access_token}
        response = requests.get(
            self.instance_url + "/services/oauth2/userinfo", headers=headers)
        if response != self.config.get('userinfo', {}):
            self.config.update({'userinfo': response.json()})


class ScratchOrgConfig(OrgConfig):
    """ Salesforce DX Scratch org configuration """

    @property
    def scratch_info(self):
        if hasattr(self, '_scratch_info'):
            return self._scratch_info

        # Create the org if it hasn't already been created
        if not self.created:
            self.create_org()

        self.logger.info('Getting scratch org info from Salesforce DX')

        # Call force:org:display and parse output to get instance_url and
        # access_token
        command = 'sfdx force:org:display -u {} --json'.format(self.username)
        p = sarge.Command(
            command,
            stderr=sarge.Capture(buffer_size=-1),
            stdout=sarge.Capture(buffer_size=-1),
        )
        p.run()

        org_info = None
        stderr_list = [line.strip() for line in p.stderr]
        stdout_list = [line.strip() for line in p.stdout]

        if p.returncode:
            self.logger.error('Return code: {}'.format(p.returncode))
            for line in stderr_list:
                self.logger.error(line)
            for line in stdout_list:
                self.logger.error(line)
            message = '\nstderr:\n{}'.format('\n'.join(stderr_list))
            message += '\nstdout:\n{}'.format('\n'.join(stdout_list))
            raise ScratchOrgException(message)

        else:
            json_txt = ''.join(stdout_list)

            try:
                org_info = json.loads(''.join(stdout_list))
            except Exception as e:
                raise ScratchOrgException(
                    'Failed to parse json from output. This can happen if '
                    'your scratch org gets deleted.\n  '
                    'Exception: {}\n  Output: {}'.format(
                        e.__class__.__name__,
                        ''.join(stdout_list),
                    )
                )
            org_id = org_info['result']['accessToken'].split('!')[0]

        if org_info['result'].get('password', None) is None:
            self.generate_password()
            return self.scratch_info

        self._scratch_info = {
            'instance_url': org_info['result']['instanceUrl'],
            'access_token': org_info['result']['accessToken'],
            'org_id': org_id,
            'username': org_info['result']['username'],
            'password': org_info['result'].get('password', None),
        }

        self.config.update(self._scratch_info)

        self._scratch_info_date = datetime.datetime.utcnow()

        return self._scratch_info

    @property
    def access_token(self):
        return self.scratch_info['access_token']

    @property
    def instance_url(self):
        return self.scratch_info['instance_url']

    @property
    def org_id(self):
        org_id = self.config.get('org_id')
        if not org_id:
            org_id = self.scratch_info['org_id']
        return org_id

    @property
    def user_id(self):
        if not self.config.get('user_id'):
            sf = Salesforce(
                instance=self.instance_url.replace('https://', ''),
                session_id=self.access_token,
                version='38.0',
            )
            result = sf.query_all(
                "SELECT Id FROM User WHERE UserName='{}'".format(
                    self.username
                )
            )
            self.config['user_id'] = result['records'][0]['Id']
        return self.config['user_id']

    @property
    def username(self):
        username = self.config.get('username')
        if not username:
            username = self.scratch_info['username']
        return username

    @property
    def password(self):
        password = self.config.get('password')
        if not password:
            password = self.scratch_info['password']
        return password

    @property
    def days(self):
        return self.config.setdefault('days', 1)

    @property
    def expired(self):
        return self.expires and self.expires < datetime.datetime.now()

    @property
    def expires(self):
        if self.date_created:
            return self.date_created + datetime.timedelta(days=int(self.days))

    @property
    def days_alive(self):
        if self.expires:
            delta = datetime.datetime.now() - self.date_created 
            return delta.days + 1

    def create_org(self):
        """ Uses sfdx force:org:create to create the org """
        if not self.config_file:
            # FIXME: raise exception
            return
        if not self.scratch_org_type:
            self.config['scratch_org_type'] = 'workspace'

        options = {
            'config_file': self.config_file,
            'devhub': ' --targetdevhubusername {}'.format(self.devhub) if self.devhub else '',
            'namespaced': ' -n' if not self.namespaced else '',
            'days': ' --durationdays {}'.format(self.days) if self.days else '',
            'alias': ' -a {}'.format(self.sfdx_alias) if self.sfdx_alias else '',
            'extraargs': os.environ.get('SFDX_ORG_CREATE_ARGS', ''),
        }

        # This feels a little dirty, but the use cases for extra args would mostly
        # work best with env vars
        command = 'sfdx force:org:create -f {config_file}{devhub}{namespaced}{days}{alias} {extraargs}'.format(**options)
        self.logger.info(
            'Creating scratch org with command {}'.format(command))
        p = sarge.Command(command, stdout=sarge.Capture(buffer_size=-1))
        p.run()

        org_info = None
        re_obj = re.compile(
            'Successfully created scratch org: (.+), username: (.+)')
        stdout = []
        for line in p.stdout:
            match = re_obj.search(line)
            if match:
                self.config['org_id'] = match.group(1)
                self.config['username'] = match.group(2)
            stdout.append(line)
            self.logger.info(line)

        self.config['date_created'] = datetime.datetime.now()

        if p.returncode:
            message = '{}: \n{}'.format(
                FAILED_TO_CREATE_SCRATCH_ORG,
                ''.join(stdout),
            )
            raise ScratchOrgException(message)

        self.generate_password()

        # Flag that this org has been created
        self.config['created'] = True

    def generate_password(self):
        """Generates an org password with the sfdx utility. """

        if self.password_failed:
            self.logger.warn(
                'Skipping resetting password since last attempt failed')
            return

        # Set a random password so it's available via cci org info
        command = 'sfdx force:user:password:generate -u {}'.format(
            self.username)
        self.logger.info(
            'Generating scratch org user password with command {}'.format(command))
        p = sarge.Command(command, stdout=sarge.Capture(
            buffer_size=-1), stderr=sarge.Capture(buffer_size=-1))
        p.run()

        stdout = []
        for line in p.stdout:
            stdout.append(line)
        stderr = []
        for line in p.stderr:
            stderr.append(line)

        if p.returncode:
            self.config['password_failed'] = True
            # Don't throw an exception because of failure creating the
            # password, just notify in a log message
            self.logger.warn(
                'Failed to set password: \n{}\n{}'.format(
                    '\n'.join(stdout), '\n'.join(stderr))
            )

    def delete_org(self):
        """ Uses sfdx force:org:delete to create the org """
        if not self.created:
            self.logger.info(
                'Skipping org deletion: the scratch org has not been created')
            return

        command = 'sfdx force:org:delete -p -u {}'.format(self.username)
        self.logger.info(
            'Deleting scratch org with command {}'.format(command))
        p = sarge.Command(command, stdout=sarge.Capture(buffer_size=-1))
        p.run()

        org_info = None
        stdout = []
        for line in p.stdout:
            stdout.append(line)
            if line.startswith('An error occurred deleting this org'):
                self.logger.error(line)
            else:
                self.logger.info(line)

        if p.returncode:
            message = 'Failed to delete scratch org: \n{}'.format(
                ''.join(stdout))
            raise ScratchOrgException(message)

        # Flag that this org has been created
        self.config['created'] = False
        self.config['username'] = None

    def force_refresh_oauth_token(self):
        # Call force:org:display and parse output to get instance_url and
        # access_token
        command = 'sfdx force:org:open -r -u {}'.format(self.username)
        self.logger.info(
            'Refreshing OAuth token with command: {}'.format(command))
        p = sarge.Command(command, stdout=sarge.Capture(buffer_size=-1))
        p.run()

        stdout_list = []
        for line in p.stdout:
            stdout_list.append(line.strip())

        if p.returncode:
            self.logger.error('Return code: {}'.format(p.returncode))
            for line in stdout_list:
                self.logger.error(line)
            message = 'Message: {}'.format('\n'.join(stdout_list))
            raise ScratchOrgException(message)

    def refresh_oauth_token(self, connected_app):
        """ Use sfdx force:org:describe to refresh token instead of built in OAuth handling """
        if hasattr(self, '_scratch_info'):
            # Cache the scratch_info for 1 hour to avoid unnecessary calls out
            # to sfdx CLI
            delta = datetime.datetime.utcnow() - self._scratch_info_date
            if delta.total_seconds() > 3600:
                del self._scratch_info

                # Force a token refresh
                self.force_refresh_oauth_token()

        # Get org info via sfdx force:org:display
        self.scratch_info

class ServiceConfig(BaseConfig):
    pass


class YamlProjectConfig(BaseProjectConfig):
    config_filename = 'cumulusci.yml'

    def __init__(self, *args, **kwargs):
        # Initialize the dictionaries for the individual configs
        self.config_project = {}
        self.config_project_local = {}
        self.config_additional_yaml = {}

        # optionally pass in a kwarg named 'additional_yaml' that will
        # be added to the YAML merge stack.
        self.additional_yaml = None
        if 'additional_yaml' in kwargs:
            self.additional_yaml = kwargs.pop('additional_yaml')

        super(YamlProjectConfig, self).__init__(*args, **kwargs)

    @property
    def config_project_local_path(self):
        path = os.path.join(
            self.project_local_dir,
            self.config_filename,
        )
        if os.path.isfile(path):
            return path

    def _load_config(self):
        """ Loads the configuration for the project """
        # Verify that we're in a project
        repo_root = self.repo_root
        if not repo_root:
            raise NotInProject(
                'No repository found in current path.  You must be inside a repository to initialize the project configuration')

        # Verify that the project's root has a config file
        if not self.config_project_path:
            raise ProjectConfigNotFound(
                'The file {} was not found in the repo root: {}'.format(
                    self.config_filename,
                    repo_root
                )
            )

        # Start the merged yaml config from the global and global local configs
        merge_yaml = [self.global_config_obj.config_global_path]
        if self.global_config_obj.config_global_local_path:
            merge_yaml.append(self.global_config_obj.config_global_local_path)

        # Load the project's yaml config file
        with open(self.config_project_path, 'r') as f_config:
            project_config = yaml.load(f_config)
        if project_config:
            self.config_project.update(project_config)
            merge_yaml.append(self.config_project_path)

        # Load the local project yaml config file if it exists
        if self.config_project_local_path:
            with open(self.config_project_local_path, 'r') as f_local_config:
                local_config = yaml.load(f_local_config)
            if local_config:
                self.config_project_local.update(local_config)
                merge_yaml.append(self.config_project_local_path)

        # merge in any additional yaml that was passed along
        if self.additional_yaml:
            additional_yaml_config = yaml.load(self.additional_yaml)
            if additional_yaml_config:
                self.config_additional_yaml.update(additional_yaml_config)
                merge_yaml.append(self.additional_yaml)

        self.config = hiyapyco.load(*merge_yaml, method=hiyapyco.METHOD_MERGE)


class YamlGlobalConfig(BaseGlobalConfig):
    config_filename = 'cumulusci.yml'
    config_local_dir = '.cumulusci'
    project_config_class = YamlProjectConfig

    def __init__(self):
        self.config_global_local = {}
        self.config_global = {}
        super(YamlGlobalConfig, self).__init__()

    @property
    def config_global_local_path(self):
        directory = os.path.join(
            os.path.expanduser('~'),
            self.config_local_dir,
        )
        if not os.path.exists(directory):
            os.makedirs(directory)

        config_path = os.path.join(
            directory,
            self.config_filename,
        )
        if not os.path.isfile(config_path):
            return None

        return config_path

    def _load_config(self):
        """ Loads the local configuration """
        # load the global config
        self._load_global_config()

        merge_yaml = [self.config_global_path]

        # Load the local config
        if self.config_global_local_path:
            config = yaml.load(open(self.config_global_local_path, 'r'))
            self.config_global_local = config
            if config:
                merge_yaml.append(self.config_global_local_path)

        self.config = hiyapyco.load(*merge_yaml, method=hiyapyco.METHOD_MERGE)

    @property
    def config_global_path(self):
        return os.path.abspath(os.path.join(
            __location__,
            '..',
            self.config_filename,
        ))

    def _load_global_config(self):
        """ Loads the configuration for the project """

        # Load the global cumulusci.yml file
        with open(self.config_global_path, 'r') as f_config:
            config = yaml.load(f_config)
        self.config_global = config
