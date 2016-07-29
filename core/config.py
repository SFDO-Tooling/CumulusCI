import os
import yaml

from .exceptions import NotInProject
from .exceptions import ProjectConfigNotFound

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))



class BaseConfig(object):
    """ Base class for all configuration objects """

    defaults = {}
    search_path = ['config']

    def __init__(self):
        self.config = {}    

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
        raise NotImplemented

    def get_task(self):
        """ Returns a TaskConfig """
        raise NotImplemented

    def list_flows(self):
        """ Returns a list of flow info dictionaries with keys 'name' and 'description' """
        raise NotImplemented

    def get_flow(self):
        """ Returns a FlowConfig """
        raise NotImplemented

class BaseGlobalConfig(BaseTaskFlowConfig):
    """ Base class for the global config which contains all configuration not specific to projects """
    
    def __init__(self):
        super(BaseGlobalConfig, self).__init__()
        self._load_global_config()

    def _load_global_config(self):
        """ Load the global configuration """
        raise NotImplemented

    def list_projects(self):
        """ Returns a list of project names """
        raise NotImplemented

    def get_project_config(self, project_name):
        """ Returns a ProjectConfig for the given project """
        raise NotImplemented

    def create_project(self, project_name, config):
        """ Creates a new project configuration and returns it """
        raise NotImplemented

class BaseProjectConfig(BaseTaskFlowConfig):
    """ Base class for a project's configuration which extends the global config """

    search_path = ['config_local','config','config_global_local','config_global']

    def __init__(self, global_config_obj):
        super(BaseProjectConfig, self).__init__()
        self.global_config_obj = global_config_obj
        self.config = {}
        self.config_local = {}
        self._load_project_config()
        self._load_config_local()

    @property
    def config_global_local(self):
        return self.global_config_obj.config_local

    @property
    def config_global(self):
        return self.global_config_obj.config_local

    def _load_config_local(self):
        """ Loads the local configuration """
        raise NotImplemented

    def _load_project_config(self):
        """ Loads the configuration for the project """
        raise NotImplemented

    def list_orgs(self):
        """ Returns a list of all org names for the project """
        raise NotImplemented

    def get_org(self, org_name):    
        """ Returns an OrgConfig for the given org_name """
        raise NotImplemented

    def set_org(self, org_name, config):
        """ Creates or updates an org's oauth info """
        raise NotImplemented

class OrgConfig(BaseConfig):
    """ Salesforce org configuration (i.e. org credentials) """
    pass

class TaskConfig(BaseConfig):
    """ A task with its configuration merged """
    pass

class FlowConfig(BaseConfig):
    """ A flow with its configuration merged """
    pass

class YamlGlobalConfig(BaseGlobalConfig):
    config_local_dir = '.cumulusci'
    search_path = ['config_local','config']

    def _get_config_local_file(self):
        directory = os.path.join(
            os.path.expanduser('~'),
            self.config_local_dir,
        )
        if not os.path.exists(directory):
            os.makedirs(directory)
   
        config_path = os.path.join(
            directory,
            'cumulusci.yml',
        ) 
        if not os.path.exists(config_path):
            return None

        return open(config_path, 'r')
        
    def _load_config_local(self):
        """ Loads the local configuration """
        f_config = self.get_config_local_file()
        if not f_config:
            return
        config = yaml.load(f_config)
        self.config_local.update(config)

    def _load_global_config(self):
        """ Loads the configuration for the project """

        # Load the global cumulusci.yml file
        f_base_config = open(
            os.path.join(
                __location__,
                '..',
                'cumulusci.yml'
            ), 'r'
        )
        base_config = yaml.load(f_base_config)
        self.config.update(base_config)

    def list_tasks(self):
        """ Returns a list of task info dictionaries with keys 'name' and 'description' """
        tasks = []
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

class YamlProjectConfig(BaseProjectConfig):
    config_filename = 'cumulusci.yml'

    def _load_config_local(self):
        """ Loads the local configuration """
        pass

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

    def _load_project_config(self):
        """ Loads the configuration for the project """
        
        repo_root = self.repo_root
        if not repo_root:
            raise NotInProject('No repository found in current path.  You must be inside a repository to initialize the project configuration')
         
        project_config_path = os.path.join(repo_root, self.config_filename)

        if not os.path.isfile(project_config_path):
            raise ProjectConfigNotFound(
                'The file {} was not found in the repo root: {}'.format(
                    self.config_filename,
                    repo_root
                )
            )

        f_config = open(project_config_path, 'r')
        project_config = yaml.load(f_config)
        if project_config:
            self.config.update(project_config)


    def list_tasks(self):
        """ Returns a list of task info dictionaries with keys 'name' and 'description' """

    def get_task(self):
        """ Returns a TaskConfig """

    def list_flows(self):
        """ Returns a list of flow info dictionaries with keys 'name' and 'description' """

    def get_flow(self):
        """ Returns a FlowConfig """

    def list_orgs(self):
        """ Returns a list of all org names for the project """
        raise NotImplemented

    def get_org(self, org_name):    
        """ Returns an OrgConfig for the given org_name """
        raise NotImplemented

    def set_org(self, org_name, config):
        """ Creates or updates an org's oauth info """
        raise NotImplemented
       
class HomeDirLocalConfig(BaseGlobalConfig):
    parent_dir_name = '.cumulusci'

    def __init__(self):
        self.parent_dir = os.path.join(os.path.expanduser('~'), self.parent_dir_name)

    def _get_projects_path(self):
        path = '{0}'.format(
            os.path.join(
                os.path.expanduser('~'), 
                self.parent_dir_name, 
            )
        )
        return path

    def list_projects(self):
        path = self._get_projects_path()
        projects = []
        for item in os.path.listdir(path):
            if not os.path.isdir(os.path.join(path, item)):
                continue
            projects.append(item)
        return projects
                
    def get_project(self, project_name):
        path = self.get_projects_path()
        path = os.path.join(path, project_name)

        if not os.path.isdir(os.path.join(path, item)):
            self._create_project(project_name)

