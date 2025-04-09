import importlib
from cumulusci.cli.runtime import CliRuntime

class ScmClass:
    scmKlass: None
    
    def __init__(self, *args, **kwds):
        runtime = kwds.get('runtime')
        self.scmKlass = None
        # Based on the repo url, Import the corresponding scm modules.
        # Iterate through all the available services and then based on matching repo url's
        # service type set the klass module.
        
        services = runtime.project_config.keychain.list_services()
        service_by_host = {}
        for service_type in services:
            for service in services.get(service_type,[]):
                s = runtime.project_config.keychain.get_service(service_type, service)
                service_by_host.update( {s.organization_url: s} if service_type == 'azure_devops' else {s.server_domain: s})
                
                if service_type == 'azure_devops':
                    server_url = s.organization_url
                    server_domain = server_url.split('/')[0] #TODO: Implement proper mechanism, url format dev.azure.com/{ORGANIZATION}.
                else:
                    server_domain = s.server_domain

                if server_domain and server_domain in runtime.project_config.repo_url:                        
                    if service_type == 'azure_devops':
                        module = importlib.import_module("cumulusci.tasks.azure_devops.base", "BaseAzureTask")
                        self.scmKlass = module.BaseAzureTask
                    else:
                        # For Github Enterprise
                        module = importlib.import_module("cumulusci.tasks.github.base", "BaseGithubTask")
                        self.scmKlass = module.BaseGithubTask
                    break
            if self.scmKlass is not None:
                break
        
        if self.scmKlass is None:
            # Setting default klass
            module = importlib.import_module("cumulusci.tasks.github.base", "BaseGithubTask")
            self.scmKlass = module.BaseGithubTask
        
runtime = CliRuntime(load_keychain=True)
entry_class = ScmClass(runtime=runtime)

BaseScmTask = type('BaseScmTask', (entry_class.scmKlass,), {})
def __init__(self, *args, **kwds):
    super(BaseScmTask, self).__init__(*args, **kwds)
BaseScmTask.__init__ = __init__
