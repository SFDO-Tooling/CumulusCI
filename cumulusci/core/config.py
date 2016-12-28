import base64
import datetime
import logging
import os
import pickle
import re

import hiyapyco
import sarge
from simple_salesforce import Salesforce
import yaml

from distutils.version import LooseVersion
from github3 import login
from Crypto import Random
from Crypto.Cipher import AES

from cumulusci.core.exceptions import ConfigError
from cumulusci.core.exceptions import NotInProject
from cumulusci.core.exceptions import KeychainConnectedAppNotFound
from cumulusci.core.exceptions import ProjectConfigNotFound
from cumulusci.core.exceptions import ScratchOrgException
from cumulusci.core.exceptions import SOQLQueryException
from cumulusci.oauth.salesforce import SalesforceOAuth2

__location__ = os.path.dirname(os.path.realpath(__file__))

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
        for task in self.tasks.keys():
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

    def __init__(self, global_config_obj):
        self.global_config_obj = global_config_obj
        self.keychain = None
        super(BaseProjectConfig, self).__init__()

    @property
    def config_global_local(self):
        return self.global_config_obj.config_global_local

    @property
    def config_global(self):
        return self.global_config_obj.config_global

    @property
    def repo_root(self):
        root = None
        pwd = os.getcwd().split(os.sep)
        while pwd:
            if os.path.isdir(os.path.join(os.sep, os.path.join(*pwd),'.git')):
                break
            else:
                pwd.pop()
        if pwd:
            return os.path.join(os.sep, os.path.join(*pwd))

    @property
    def repo_name(self):
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
                    repo_name = line_parts[-1]
                    if repo_name.endswith('.git'):
                        repo_name = repo_name[:-4]
                    return repo_name

    @property
    def repo_url(self):
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
        if not self.repo_root:
            return

        with open(os.path.join(self.repo_root, '.git', 'HEAD'), 'r') as f:
            branch_ref = f.read().strip()
        if branch_ref.startswith('ref: '):
            return '/'.join(branch_ref[5:].split('/')[2:])

    @property
    def repo_commit(self):
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
                        # Skip lines showing the commit sha of a tag on the preceeding line
                        continue
                    if parts[1].replace('refs/remotes/origin/', '').strip() == branch:
                        commit_sha = parts[0]
                        break

        return commit_sha

    def get_latest_version(self, beta=None):
        """ Query Github Releases to find the latest production or beta release """
        github_config = self.keychain.get_service('github')
        gh = login(github_config.username, github_config.password)
        repo = gh.repository(self.repo_owner, self.repo_name)
        latest_version = None
        for release in repo.iter_releases():
            if beta:
                if 'Beta' not in release.tag_name:
                    continue
            else:
                if 'Beta' in release.tag_name:
                    continue
            version = self.get_version_for_tag(release.tag_name)
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
        path = os.path.join(
            os.path.expanduser('~'),
            self.global_config_obj.config_local_dir,
            self.repo_name,
        )
        if not os.path.isdir(path):
            os.makedirs(path)
        return path

    def get_tag_for_version(self, version):
        if '(Beta' in version:
            tag_version = version.replace(' (','-').replace(')','').replace(' ','_')
            tag_name = self.project__git__prefix_beta + tag_version
        else:
            tag_name = self.project__git__prefix_release + version
        return tag_name

    def get_version_for_tag(self, tag):
        if 'Beta' in tag:
            version = tag[len(self.project__git__prefix_beta):]
            version = version.replace('-',' (').replace('_',' ') + ')'
        else:
            version = tag[len(self.project__git__prefix_release):]
        return version


    def set_keychain(self, keychain):
        self.keychain = keychain

    def _check_keychain(self):
        if not self.keychain:
            raise KeychainNotFound('Could not find config.keychain.  You must call config.set_keychain(keychain) before accessing orgs')

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

    def refresh_oauth_token(self, connected_app):
        client_id = self.client_id
        client_secret = self.client_secret
        if not client_id:
            client_id = connected_app.client_id
            client_secret = connected_app.client_secret
        sf_oauth = SalesforceOAuth2(
            client_id,
            client_secret,
            connected_app.callback_url, # Callback url isn't really used for this call
            auth_site=self.auth_site,
        )
        resp = sf_oauth.refresh_token(self.refresh_token).json()
        if resp != self.config:
            self.config.update(resp)

    @property
    def start_url(self):
        start_url = '%s/secur/frontdoor.jsp?sid=%s' % (self.instance_url, self.access_token)
        return start_url

    @property
    def user_id(self):
        return self.id.split('/')[-1]

    @property
    def org_id(self):
        return self.id.split('/')[-2]

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

        # Call force:org:open and parse output to get instance_url and access_token
        command = 'heroku force:org:open -d -u {}'.format(self.username)
        p = sarge.Command(command, stdout=sarge.Capture(buffer_size=-1))
        p.run()

        org_info = None
        stdout_list = []
        for line in p.stdout:
            if line.startswith('Access org'):
                org_info = line.strip()
            stdout_list.append(line.strip())

        if p.returncode:
            message = 'Return code: {}\nstdout: {}\nstderr: {}'.format(
                p.returncode,
                '\n'.join(stdout_list),
                p.stderr,
            )
            self.logger.error(message)
            raise ScratchOrgException(message)

        if not org_info:
            message = 'Did not find org info in command output:\n{}'.format(p.stdout)
            self.logger.error(message)
            raise ScratchOrgException(message)

        # OrgID is the third word of the output
        org_id = org_info.split(' ')[2]

        # Username is the sixth word of the output
        username = org_info.split(' ')[5]

        info_parts = org_info.split('following URL: ')
        if len(info_parts) == 1:
            message = 'Did not find org info in command output:\n{}'.format(p.stdout)
            self.logger.error(message)
            raise ScratchOrgException(message)

        instance_url, access_token = info_parts[1].split('/secur/frontdoor.jsp?sid=')
        self._scratch_info = {
            'instance_url': instance_url,
            'access_token': access_token,
            'org_id': org_id,
            'username': username,
        }
    
        self._scratch_info_date = datetime.datetime.now()

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

    def create_org(self):
        """ Uses heroku force:org:create to create the org """
        if not self.config_file:
            # FIXME: raise exception
            return
        if not self.scratch_org_type:
            self.config['scratch_org_type'] = 'workspace'

        command = 'heroku force:org:create -t {} -f {}'.format(self.scratch_org_type, self.config_file)
        self.logger.info('Creating scratch org with command {}'.format(command))
        p = sarge.Command(command, stdout=sarge.Capture(buffer_size=-1))
        p.run()

        org_info = None
        re_obj = re.compile('Successfully created workspace org: (.+), username: (.+)')
        for line in p.stdout:
            match = re_obj.search(line)
            if match:
                self.config['org_id'] = match.group(1)
                self.config['username'] = match.group(2)
            self.logger.info(line)

        if p.returncode:
            # FIXME: raise exception
            raise ConfigError('Failed to create scratch org: {}'.format('\n'.join(p.stdout)))

        # Flag that this org has been created
        self.config['created'] = True

    def delete_org(self):
        """ Uses heroku force:org:delete to create the org """
        if not self.created:
            self.logger.info('Skipping org deletion: the scratch org has not been created')
            return

        command = 'heroku force:org:delete --force -u {}'.format(self.username)
        self.logger.info('Deleting scratch org with command {}'.format(command))
        p = sarge.Command(command, stdout=sarge.Capture(buffer_size=-1))
        p.run()

        org_info = None
        for line in p.stdout:
            self.logger.info(line)

        if p.returncode:
            # FIXME: raise exception
            raise ConfigError('Failed to delete scratch org')

        # Flag that this org has been created
        self.config['created'] = False
        self.config['username'] = False

    def refresh_oauth_token(self, connected_app):
        """ Use heroku force:org:open to refresh token instead of built in OAuth handling """
        if hasattr(self, '_scratch_info'):
            # Cache the scratch_info for 1 hour to avoid unnecessary calls out to heroku CLI
            delta = datetime.datetime.now() - self._scratch_info_date
            if delta.total_seconds() > 3600:
                del self._scratch_info
        # This triggers a refresh
        self.scratch_info


class ServiceConfig(BaseConfig):
    """ Keychain service configuration """
    pass

class YamlProjectConfig(BaseProjectConfig):
    config_filename = 'cumulusci.yml'


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

        # Initialize the dictionaries for the individual configs
        self.config_project = {}
        self.config_project_local = {}

        # Verify that we're in a project
        repo_root = self.repo_root
        if not repo_root:
            raise NotInProject('No repository found in current path.  You must be inside a repository to initialize the project configuration')

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
        return os.path.join( __location__, '..', self.config_filename)

    def _load_global_config(self):
        """ Loads the configuration for the project """

        # Load the global cumulusci.yml file
        with open(self.config_global_path, 'r') as f_config:
            config = yaml.load(f_config)
        self.config_global = config
