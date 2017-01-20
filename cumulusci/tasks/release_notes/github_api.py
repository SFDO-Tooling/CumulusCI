import httplib
import json
import re

import requests

from .exceptions import GithubApiNotFoundError
from .exceptions import GithubApiNoResultsError
from .exceptions import GithubApiUnauthorized


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
    def prefix_beta(self):
        return self.github_info.get('prefix_beta', 'beta/')

    @property
    def current_tag_info(self):
        is_prod = False
        is_beta = False
        tag = self.current_tag
        if tag.startswith(self.prefix_prod):
            is_prod = True
        elif tag.startswith(self.prefix_beta):
            is_beta = True

        if is_prod:
            version_number = tag.replace(self.prefix_beta, '')
        elif is_beta:
            version_parts = re.findall(
                '{}(\d+\.\d+)-Beta_(\d+)'.format(self.prefix_beta),
                tag,
            )
            assert version_parts
            version_number = '{} (Beta {})'.format(*version_parts[0])
        else:
            version_number = None

        tag_info = {
            'is_prod': is_prod,
            'is_beta': is_beta,
            'version_number': version_number,
        }

        return tag_info

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
        elif resp.status_code == httplib.UNAUTHORIZED:
            raise GithubApiUnauthorized(resp.content)

        try:
            data = json.loads(resp.content)
            return data
        except:
            return resp.status_code
