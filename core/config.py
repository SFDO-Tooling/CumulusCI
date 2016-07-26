import os
import yaml

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

    def __init__(self, global_config):
        super(BaseProjectConfig, self).__init__()
        self.global_config = global_config
        self.config = {}
        self.config_local = {}
        self._load_project_config()
        self._load_local_config()

    def _load_local_config(self):
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
    def _load_local_config(self):
        """ Loads the local configuration """
        pass

    def list_tasks(self):
        """ Returns a list of task info dictionaries with keys 'name' and 'description' """

    def get_task(self):
        """ Returns a TaskConfig """

    def list_flows(self):
        """ Returns a list of flow info dictionaries with keys 'name' and 'description' """

    def get_flow(self):
        """ Returns a FlowConfig """

class YamlProjectConfig(BaseProjectConfig):
    def _load_local_config(self):
        """ Loads the local configuration """
        pass

    def _load_project_config(self):
        """ Loads the configuration for the project """
        config = {}

        # Start with the base cumulusci.yml
        f_base_config = open(__location__ + '/cumulusci.yml', 'r')
        base_config = yaml.load(f_base_config)
        config.update(base_config)

        # Include the local repo's cumulusci.yml overrides

        # Include the local user's cumulusci.yml overrides

        return config
        raise NotImplemented

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

