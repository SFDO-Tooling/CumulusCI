import coreapi
from cumulusci.core.tasks import BaseTask
from cumulusci.core.exceptions import ServiceNotConfigured

class ApiClient(object):
    def __init__(self, config):
        self.service = config.keychain.get_service('metaci')            
           
        auth = coreapi.auth.TokenAuthentication(self.service.token, scheme='Token')
        self.client = coreapi.Client(auth=auth)
        self._load_document()

    def _load_document(self):
        self.document = self.client.get(self.service.url + '/api/schema')
    
    def __call__(self, *args, **kwargs):
        """ A shortcut to allow api_client('action') instead of api_client.client.action(self.document, 'action') """
        resp = self.client.action(self.document, args, **kwargs)
        return resp


class BaseMetaCITask(BaseTask):
    def _update_credentials(self):
        self.api = ApiClient(self.project_config)

class GetOrgsFromMetaCI(BaseMetaCITask):
    task_options = {
        'repo_id': {
            'description': 'The MetaCI Repo ID',
            'required': True,
        },
        'output_file': {
            'description': 'The file to write out to.',
            'required': False
        },
    }

    def _run_task(self):
        orgs = self.api('registered_orgs','list',params={'repo':self.options['repo_id']})['results']
        org_ids = []
        if orgs:
            for org in orgs:
                self.logger.info('{}: {} - {}'.format(org['org_id'], org['name'], org['release_cycle']))
                if org['release_cycle'] == 'QA':
                    org_ids.append(org['org_id'] + "\n")

        if 'output_file' in self.options:
            with open(self.options['output_file'],'w') as f:
                f.writelines(org_ids)
        

        