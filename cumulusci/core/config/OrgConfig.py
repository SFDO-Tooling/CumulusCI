from collections import defaultdict
from distutils.version import StrictVersion
import os

import requests
from simple_salesforce import Salesforce

from cumulusci.core.config import BaseConfig
from cumulusci.core.exceptions import SalesforceCredentialsException, CumulusCIException
from cumulusci.oauth.salesforce import SalesforceOAuth2
from cumulusci.oauth.salesforce import jwt_session


SKIP_REFRESH = os.environ.get("CUMULUSCI_DISABLE_REFRESH")


class OrgConfig(BaseConfig):
    """ Salesforce org configuration (i.e. org credentials) """

    # make sure it can be mocked for tests
    SalesforceOAuth2 = SalesforceOAuth2

    def __init__(self, config, name):
        self.name = name
        self._community_info_cache = {}
        self._client = None
        self._latest_api_version = None
        self._installed_packages = None
        super(OrgConfig, self).__init__(config)

    def refresh_oauth_token(self, keychain, connected_app=None):
        if not SKIP_REFRESH:
            SFDX_CLIENT_ID = os.environ.get("SFDX_CLIENT_ID")
            SFDX_HUB_KEY = os.environ.get("SFDX_HUB_KEY")
            if SFDX_CLIENT_ID and SFDX_HUB_KEY:
                info = jwt_session(
                    SFDX_CLIENT_ID, SFDX_HUB_KEY, self.username, self.instance_url
                )
            else:
                info = self._refresh_token(keychain, connected_app)
            if info != self.config:
                self.config.update(info)
        self._load_userinfo()
        self._load_orginfo()

    def _refresh_token(self, keychain, connected_app):
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
                f"Error refreshing OAuth token: {resp.text}"
            )
        return resp.json()

    @property
    def lightning_base_url(self):
        return self.instance_url.split(".")[0] + ".lightning.force.com"

    @property
    def salesforce_client(self):
        if not self._client:
            self._client = Salesforce(
                instance=self.instance_url.replace("https://", ""),
                session_id=self.access_token,
                version=self.latest_api_version,
            )

        return self._client

    @property
    def latest_api_version(self):
        if not self._latest_api_version:
            headers = {"Authorization": "Bearer " + self.access_token}
            response = requests.get(
                self.instance_url + "/services/data", headers=headers
            )
            self._latest_api_version = str(response.json()[-1]["version"])

        return self._latest_api_version

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
        self._org_sobject = self.salesforce_client.Organization.get(self.org_id)

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
        response = self.salesforce_client.restful("connect/communities")

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
                f"Unable to find community information for '{community_name}'"
            )

        return self._community_info_cache[community_name]

    def has_minimum_package_version(self, package_identifier, version_identifier):
        """Return True if the org has a version of the specified package that is
        equal to or newer than the supplied version identifier.

        The package identifier may be either a namespace or a 033 package Id.
        The version identifier should be in "1.2.3" or "1.2.3b4" format.

        A CumulusCIException will be thrown if you request to check a namespace
        and multiple second-generation packages sharing that namespace are installed.
        Use a package Id to handle this circumstance."""
        installed_version = self.installed_packages.get(package_identifier)

        if not installed_version:
            return False
        elif len(installed_version) > 1:
            raise CumulusCIException(
                f"Cannot check installed version of {package_identifier}, because multiple "
                f"packages are installed that match this identifier."
            )

        return installed_version[0] >= version_identifier

    @property
    def installed_packages(self):
        """installed_packages is a dict mapping a namespace or package Id (033*) to the installed package
        version(s) matching that identifier. All values are lists, because multiple second-generation
        packages may be installed with the same namespace.

        To check if a required package is present, call `has_minimum_package_version()` with either the
        namespace or 033 Id of the desired package and its version, in 1.2.3 format.

        Beta version of a package are represented as "1.2.3b5", where 5 is the build number."""
        if not self._installed_packages:
            response = self.salesforce_client.restful(
                "tooling/query/?q=SELECT SubscriberPackage.Id, SubscriberPackage.NamespacePrefix, SubscriberPackageVersion.MajorVersion, "
                "SubscriberPackageVersion.MinorVersion, SubscriberPackageVersion.PatchVersion,  "
                "SubscriberPackageVersion.BuildNumber, SubscriberPackageVersion.IsBeta "
                "FROM InstalledSubscriberPackage"
            )

            self._installed_packages = defaultdict(list)
            for package in response["records"]:
                sp = package["SubscriberPackage"]
                spv = package["SubscriberPackageVersion"]
                # PatchVersion is a 0 on a non-patch version.
                version = (
                    f"{spv['MajorVersion']}.{spv['MinorVersion']}.{spv['PatchVersion']}"
                )
                if spv["IsBeta"]:
                    version += f"b{spv['BuildNumber']}"
                self._installed_packages[sp["NamespacePrefix"]].append(
                    StrictVersion(version)
                )
                self._installed_packages[sp["Id"]].append(StrictVersion(version))

        return self._installed_packages

    def reset_installed_packages(self):
        self._installed_packages = None
