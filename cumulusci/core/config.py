import base64
import os
import pickle

import hiyapyco
import yaml

from Crypto import Random
from Crypto.Cipher import AES

from cumulusci.core.exceptions import NotInProject
from cumulusci.core.exceptions import KeychainConnectedAppNotFound
from cumulusci.core.exceptions import ProjectConfigNotFound
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
        self._load_config()

    def _load_config(self):
        """ Performs the logic to initialize self.config """
        pass

    def __getattr__(self, name):
        tree = name.split('__')
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
        return config

    def list_flows(self):
        """ Returns a list of flow info dictionaries with keys 'name' and 'description' """
        flows = []
        return flows

    def get_flow(self, name):
        """ Returns a FlowConfig """
        config = getattr(self, 'flows__{}'.format(name))
        return config

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
        f = open(os.path.join(self.repo_root, '.git', 'config'), 'r')
        for line in f.read().splitlines():
            line = line.strip()
            if line == '[remote "origin"]':
                in_remote_origin = True
                continue
            if line.find('url =') != -1:
                line_parts = line.split('/')
                return line_parts[-1]

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
        sf_oauth = SalesforceOAuth2(
            connected_app.client_id, 
            connected_app.client_secret, 
            connected_app.callback_url,
            False
        )
        resp = sf_oauth.refresh_token(self.refresh_token).json()
        if resp != self.config:
            self.config.update(resp)

    @property
    def start_url(self):
        start_url = '%s/secur/frontdoor.jsp?sid=%s' % (self.instance_url, self.access_token)
        return start_url


class TaskConfig(BaseConfig):
    """ A task with its configuration merged """
    pass

class FlowConfig(BaseConfig):
    """ A flow with its configuration merged """
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
        f_config = open(self.config_project_path, 'r')
        project_config = yaml.load(f_config)
        if project_config:
            self.config_project.update(project_config)
            merge_yaml.append(self.config_project_path)

        # Load the local project yaml config file if it exists
        if self.config_project_local_path:
            f_local_config = open(self.config_project_local_path, 'r')
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
        f_config = open(self.config_global_path, 'r')
        config = yaml.load(f_config)
        self.config_global = config
