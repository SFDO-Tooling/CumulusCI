import os
import yaml
import logging
#from salesforce.oauth import SalesforceOAuth2
#from salesforce.exceptions import MissingOAuthError
#from salesforce.exceptions import MissingOrgCredentialsError

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

class CumulusCI(object):
    def __init__(self, directory):
        self.directory = directory
        self.logger = logging.getLogger(__name__)
    
    @property
    def oauth(self):
        if not hasattr(self, '_oauth'):
            raise MissingOAuthError
        return self._oauth

    @property
    def config(self):
        if not hasattr(self, '_config'):
            self._config = self.parse_config()
        return self._config

    def parse_config(self):
        config = {}

        # Start with the base cumulusci.yml
        f_base_config = open(__location__ + '/cumulusci.yml', 'r')
        base_config = yaml.load(f_base_config)
        config.update(base_config)
            
        # Include the local repo's cumulusci.yml overrides

        # Include the local user's cumulusci.yml overrides

        return config

    def set_org(self, org_name, provider, sandbox=None):
        self._oauth = self.get_org_oauth(org_name)
        self._oauth_provider = provider
        self.refresh_org_oauth()
        self.sandbox = sandbox

    def get_org_oauth(self, org_name):
        # Look up the org file
        path = '{0}'.format(
            os.path.join(
                os.path.expanduser('~'), 
                '.cumulusci', 
                org_name
            )
        )
        if not os.path.isfile(path):
            raise MissingOrgCredentialsError(u"Org credentials file not found for org {0} at path {1}".format(org_name, path))

        org_credentials = open(path, 'r')
        oauth = yaml.load(org_credentials)

        # Parse the file into oauth
        return oauth

    def refresh_org_oauth(self):
        sf_oauth = SalesforceOAuth2(
            self._oauth_provider['client_id'],
            self._oauth_provider['client_secret'],
            self._oauth_provider['callback_url'],
            sandbox=False,  # FIXME: Add support for sandboxes
        )
        response = sf_oauth.refresh_token(self._oauth['refresh_token'])
        if response.get('access_token', None):
            # Set the new token in the session
            self._oauth.update(response)
   
