import httplib
import requests
import json

from .exceptions import GithubApiNotFoundError
from .exceptions import GithubApiNoResultsError

class GithubApiMixin(object):
    github_api_base_url = 'https://api.github.com'

    @property
    def github_owner(self):
        return self.github_info['github_owner']

    @property
    def github_repo(self):
        return self.github_info['github_repo']

    @property
    def github_username(self):
        return self.github_info['github_username']

    @property
    def github_password(self):
        return self.github_info['github_password']

    @property
    def master_branch(self):
        return self.github_info.get('master_branch', 'master')

    @property
    def prefix_prod(self):
        return self.github_info.get('prefix_prod', 'prod/')

    @property
    def github_info(self):
        # By default, look for github config info in the release_notes
        # property.  Subclasses can override this if needed
        return self.release_notes_generator.github_info

    def call_api(self, subpath, data=None):
        """ Takes a subpath under the repository (ex: /releases) and returns
        the json data from the api """
        api_url = '{}/repos/{}/{}{}'.format(
            self.github_api_base_url, self.github_owner, self.github_repo,
            subpath)

        # Use Github Authentication if available for the repo
        kwargs = {}
        if self.github_owner and self.github_owner:
            kwargs['auth'] = (self.github_owner, self.github_password)

        if data:
            resp = requests.post(api_url, data=json.dumps(data), **kwargs)
        else:
            resp = requests.get(api_url, **kwargs)

        if resp.status_code == httplib.NOT_FOUND:
            raise GithubApiNotFoundError(resp.content)

        try:
            data = json.loads(resp.content)
            return data
        except:
            return resp.status_code
