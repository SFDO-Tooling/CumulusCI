from __future__ import unicode_literals

import requests

from cumulusci.core.config import BaseConfig
from cumulusci.core.exceptions import SalesforceCredentialsException
from cumulusci.oauth.salesforce import SalesforceOAuth2


class OrgConfig(BaseConfig):
    """ Salesforce org configuration (i.e. org credentials) """

    # make sure it can be mocked for tests
    SalesforceOAuth2 = SalesforceOAuth2

    def __init__(self, config, name):
        self.name = name
        self._community_info_cache = {}
        super(OrgConfig, self).__init__(config)

    def refresh_oauth_token(self, keychain, connected_app=None):
        if keychain:  # it might be none'd and caller adds connected_app
            connected_app = keychain.get_service("connected_app")
        if connected_app is None:
            raise AttributeError(
                "No connected app or keychain was passed to refresh_oauth_token."
            )
        client_id = self.client_id
        client_secret = self.client_secret
        if not client_id:
            client_id = connected_app.client_id
            client_secret = connected_app.client_secret
        sf_oauth = self.SalesforceOAuth2(
            client_id,
            client_secret,
            connected_app.callback_url,  # Callback url isn't really used for this call
            auth_site=self.instance_url,
        )

        resp = sf_oauth.refresh_token(self.refresh_token)
        if resp.status_code != 200:
            raise SalesforceCredentialsException(
                "Error refreshing OAuth token: {}".format(resp.text)
            )
        info = resp.json()
        if info != self.config:
            self.config.update(info)
        self._load_userinfo()
        self._load_orginfo()

    @property
    def lightning_base_url(self):
        return self.instance_url.split(".")[0] + ".lightning.force.com"

    @property
    def start_url(self):
        start_url = "%s/secur/frontdoor.jsp?sid=%s" % (
            self.instance_url,
            self.access_token,
        )
        return start_url

    @property
    def user_id(self):
        return self.id.split("/")[-1]

    @property
    def org_id(self):
        return self.id.split("/")[-2]

    @property
    def username(self):
        """ Username for the org connection. """
        username = self.config.get("username")
        if not username:
            username = self.userinfo__preferred_username
        return username

    def load_userinfo(self):
        self._load_userinfo()

    def _load_userinfo(self):
        headers = {"Authorization": "Bearer " + self.access_token}
        response = requests.get(
            self.instance_url + "/services/oauth2/userinfo", headers=headers
        )
        if response != self.config.get("userinfo", {}):
            self.config.update({"userinfo": response.json()})

    def can_delete(self):
        return False

    def _load_orginfo(self):
        headers = {"Authorization": "Bearer " + self.access_token}
        self._org_sobject = requests.get(
            self.instance_url
            + "/services/data/v45.0/sobjects/Organization/{}".format(self.org_id),
            headers=headers,
        ).json()
        result = {
            "org_type": self._org_sobject["OrganizationType"],
            "is_sandbox": self._org_sobject["IsSandbox"],
        }
        self.config.update(result)

    @property
    def organization_sobject(self):
        return self._org_sobject

    def _fetch_community_info(self):
        """Use the API to re-fetch information about communities"""
        headers = {"Authorization": "Bearer " + self.access_token}
        response = requests.get(
            self.instance_url + "/services/data/v45.0/connect/communities",
            headers=headers,
        ).json()

        # Since community names must be unique, we'll return a dictionary
        # with the community names as keys
        result = {community["name"]: community for community in response["communities"]}
        return result

    def get_community_info(self, community_name, force_refresh=False):
        """Return the community information for the given community

        An API call will be made the first time this function is used,
        and the return values will be cached. Subsequent calls will
        not call the API unless the requested community name is not in
        the cached results, or unless the force_refresh parameter is
        set to True.

        """

        if force_refresh or community_name not in self._community_info_cache:
            self._community_info_cache = self._fetch_community_info()

        if community_name not in self._community_info_cache:
            raise Exception(
                "Unable to find community information for '{}'".format(community_name)
            )

        return self._community_info_cache[community_name]
