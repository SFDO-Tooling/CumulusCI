import os
import re
from collections import defaultdict, namedtuple
from contextlib import contextmanager
from datetime import date, datetime
from typing import Optional
from urllib.parse import urlparse

import requests
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceError, SalesforceResourceNotFound

from cumulusci.core.config import BaseConfig
from cumulusci.core.exceptions import (
    CumulusCIException,
    DependencyResolutionError,
    ServiceNotConfigured,
)
from cumulusci.oauth.client import OAuth2Client, OAuth2ClientConfig
from cumulusci.oauth.salesforce import SANDBOX_LOGIN_URL, jwt_session
from cumulusci.utils import parse_api_datetime
from cumulusci.utils.fileutils import open_fs_resource
from cumulusci.utils.http.requests_utils import safe_json_from_response
from cumulusci.utils.version_strings import StrictVersion

SKIP_REFRESH = os.environ.get("CUMULUSCI_DISABLE_REFRESH")
SANDBOX_MYDOMAIN_RE = re.compile(r"\.cs\d+\.my\.(.*)salesforce\.com")
MYDOMAIN_RE = re.compile(r"\.my\.(.*)salesforce\.com")


VersionInfo = namedtuple("VersionInfo", ["id", "number"])


class OrgConfig(BaseConfig):
    """Salesforce org configuration (i.e. org credentials)"""

    access_token: str
    config_file: str
    config_name: str
    created: bool
    date_created: (datetime, date)  # type: ignore
    days: int
    email_address: str
    instance_name: str
    instance_url: str
    expires: str  # TODO: note that ScratchOrgConfig has a bool method of same name
    expired: bool  # ditto
    is_sandbox: bool
    namespace: str
    namespaced: bool
    org_type: str
    password: str
    scratch: bool
    scratch_org_type: str
    set_password: bool
    sfdx_alias: str
    userinfo: str
    id: str
    active: bool
    default: bool
    client_id: str
    refresh_token: str
    client_secret: str
    connected_app: str
    serialization_format: str

    createable: Optional[bool] = None

    # make sure it can be mocked for tests
    OAuth2Client = OAuth2Client

    def __init__(self, config: dict, name: str, keychain=None, global_org=False):
        self.keychain = keychain
        self.global_org = global_org

        self.name = name
        self.force_sandbox = config.get("sandbox", False) if config else False
        self._community_info_cache = {}
        self._latest_api_version = None
        self._installed_packages = None
        self._is_person_accounts_enabled = None
        self._multiple_currencies_is_enabled = False

        super().__init__(config)

    def refresh_oauth_token(self, keychain, connected_app=None, is_sandbox=False):
        """Get a fresh access token and store it in the org config.

        If the SFDX_CLIENT_ID and SFDX_HUB_KEY environment variables are set,
        this is done using the Oauth2 JWT flow.

        Otherwise it is done using the Oauth2 Refresh Token flow using the connected app
        configured in the keychain's connected_app service.

        Also refreshes user and org info that is cached in the org config.
        """
        if not SKIP_REFRESH:
            SFDX_CLIENT_ID = os.environ.get("SFDX_CLIENT_ID")
            SFDX_HUB_KEY = os.environ.get("SFDX_HUB_KEY")
            if SFDX_CLIENT_ID and SFDX_HUB_KEY:
                auth_url = SANDBOX_LOGIN_URL if self.force_sandbox else self.id
                info = jwt_session(
                    SFDX_CLIENT_ID,
                    SFDX_HUB_KEY,
                    self.username,
                    self.instance_url,
                    auth_url=auth_url,
                    is_sandbox=is_sandbox,
                )
            else:
                info = self._refresh_token(keychain, connected_app)
            if info != self.config:
                self.config.update(info)
        self._load_userinfo()
        self._load_orginfo()

    @contextmanager
    def save_if_changed(self):
        orig_config = self.config.copy()
        yield
        if self.config != orig_config:
            self.logger.info("Org info updated, writing to keychain")
            self.save()

    def _refresh_token(self, keychain, connected_app):
        if keychain:  # it might be none'd and caller adds connected_app
            try:
                connected_app = keychain.get_service(
                    "connected_app", self.connected_app
                )
            except ServiceNotConfigured:
                raise ServiceNotConfigured(
                    f"This org was connected using the {self.connected_app} connected_app service, which is no longer configured."
                )
        if connected_app is None:
            raise AttributeError(
                "No connected app or keychain was passed to refresh_oauth_token."
            )
        client_id = self.client_id
        client_secret = self.client_secret
        if not client_id:
            client_id = connected_app.client_id
            client_secret = connected_app.client_secret

        sf_oauth_config = OAuth2ClientConfig(
            client_id=client_id,
            client_secret=client_secret,
            auth_uri=f"{self.instance_url}/services/oauth2/authorize",
            token_uri=f"{self.instance_url}/services/oauth2/token",
            scope="web full refresh_token",
        )
        sf_oauth = self.OAuth2Client(sf_oauth_config)
        return sf_oauth.refresh_token(self.refresh_token)

    @property
    def lightning_base_url(self):
        instance_url = self.instance_url.rstrip("/")
        if SANDBOX_MYDOMAIN_RE.search(instance_url):
            return SANDBOX_MYDOMAIN_RE.sub(r".lightning.\1force.com", instance_url)
        elif MYDOMAIN_RE.search(instance_url):
            return MYDOMAIN_RE.sub(r".lightning.\1force.com", instance_url)
        else:
            return self.instance_url.split(".")[0] + ".lightning.force.com"

    @property
    def salesforce_client(self):
        """Return a simple_salesforce.Salesforce instance authorized to this org.
        Does not perform a token refresh."""
        return Salesforce(
            instance=self.instance_url.replace("https://", ""),
            session_id=self.access_token,
            version=self.latest_api_version,
        )

    @property
    def latest_api_version(self):
        if not self._latest_api_version:
            headers = {"Authorization": "Bearer " + self.access_token}
            response = requests.get(
                self.instance_url + "/services/data", headers=headers
            )
            try:
                version = safe_json_from_response(response)[-1]["version"]
            except (KeyError, IndexError, TypeError):
                raise CumulusCIException(
                    f"Cannot decode API Version `{response.text[0:100]}``"
                )
            self._latest_api_version = str(version)

        return self._latest_api_version

    @property
    def start_url(self):
        """The frontdoor URL that results in an instant login"""
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
        try:
            if org_id := self.config.get("org_id"):
                return org_id
            elif hasattr(self, "id") and self.id:
                return self.id.split("/")[-2]
            else:
                return None
        except Exception as e:  # pragma: no cover
            assert e is None, e

    @property
    def username(self):
        """Username for the org connection."""
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
            config_data = safe_json_from_response(response)
            self.config.update({"userinfo": config_data})

    def can_delete(self):
        return False

    def _load_orginfo(self):
        """Query the Organization sObject and populate local config values from the result."""
        self._org_sobject = self.salesforce_client.Organization.get(self.org_id)

        result = {
            "org_type": self._org_sobject["OrganizationType"],
            "is_sandbox": self._org_sobject["IsSandbox"],
            "instance_name": self._org_sobject["InstanceName"],
            "namespace": self._org_sobject["NamespacePrefix"],
        }
        self.config.update(result)

    def populate_expiration_date(self):
        if not self.organization_sobject:
            self._load_orginfo()
        if self.organization_sobject["TrialExpirationDate"] is None:
            self.config["expires"] = "Persistent"
        else:
            self.config["expires"] = parse_api_datetime(
                self.organization_sobject["TrialExpirationDate"]
            ).date()

    @property
    def organization_sobject(self):
        """Cached copy of Organization sObject. Does not perform API call."""
        return getattr(self, "_org_sobject", None)

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

        return installed_version[0].number >= version_identifier

    @property
    def installed_packages(self):
        """installed_packages is a dict mapping a namespace, package name, or package Id (033*) to the installed package
        version(s) matching that identifier. All values are lists, because multiple second-generation
        packages may be installed with the same namespace.

        Keys include:
        - namespace: "mycompany"
        - package name: "My Package Name"
        - namespace@version: "mycompany@1.2.3"
        - package ID: "033ABCDEF123456"

        To check if a required package is present, call `has_minimum_package_version()` with either the
        namespace or 033 Id of the desired package and its version, in 1.2.3 format.

        Beta version of a package are represented as "1.2.3b5", where 5 is the build number.
        """
        if self._installed_packages is None:
            isp_result = self.salesforce_client.restful(
                "tooling/query/?q=SELECT SubscriberPackage.Id, SubscriberPackage.Name, SubscriberPackage.NamespacePrefix, "
                "SubscriberPackageVersionId FROM InstalledSubscriberPackage"
            )
            _installed_packages = defaultdict(list)
            for isp in isp_result["records"]:
                sp = isp["SubscriberPackage"]
                try:
                    spv_result = self.salesforce_client.restful(
                        "tooling/query/?q=SELECT Id, MajorVersion, MinorVersion, PatchVersion, BuildNumber, "
                        f"IsBeta FROM SubscriberPackageVersion WHERE Id='{isp['SubscriberPackageVersionId']}'"
                    )
                except SalesforceError as err:
                    self.logger.warning(
                        f"Ignoring error while trying to check installed package {isp['SubscriberPackageVersionId']}: {err.content}"
                    )
                    continue
                if not spv_result["records"]:
                    # This _shouldn't_ happen, but it is possible in customer orgs.
                    continue
                spv = spv_result["records"][0]

                version = f"{spv['MajorVersion']}.{spv['MinorVersion']}"
                if spv["PatchVersion"]:
                    version += f".{spv['PatchVersion']}"
                if spv["IsBeta"]:
                    version += f"b{spv['BuildNumber']}"
                version_info = VersionInfo(spv["Id"], StrictVersion(version))
                namespace = sp["NamespacePrefix"]
                package_name = sp.get("Name", None)
                _installed_packages[namespace].append(version_info)
                namespace_version = f"{namespace}@{version}"
                _installed_packages[namespace_version].append(version_info)
                _installed_packages[sp["Id"]].append(version_info)
                # Add package name as a key for specific package detection
                if package_name:
                    _installed_packages[package_name].append(version_info)

            self._installed_packages = _installed_packages
        return self._installed_packages

    def reset_installed_packages(self):
        self._installed_packages = None

    def save(self):
        assert self.keychain, "Keychain was not set on OrgConfig"
        self.keychain.set_org(self, self.global_org)

    def get_domain(self):
        instance_url = self.config.get("instance_url", "")
        return urlparse(instance_url).hostname or ""

    def get_orginfo_cache_dir(self, cachename):
        "Returns a context managed FSResource object"
        assert self.keychain, "Keychain should be set"
        if self.global_org:
            cache_dir = self.keychain.global_config_dir
        else:
            cache_dir = self.keychain.cache_dir
        assert self.get_domain()
        assert self.username
        uniqifier = self.get_domain() + "__" + str(self.username).replace("@", "__")
        cache_dir = cache_dir / "orginfo" / uniqifier / cachename

        cache_dir.mkdir(parents=True, exist_ok=True)
        return open_fs_resource(cache_dir)

    @property
    def is_person_accounts_enabled(self):
        """
        Returns if the org has person accounts enabled, i.e. if Account has an ``IsPersonAccount`` field.

        **Example**

        Selectively run a task in a flow only if Person Accounts is or is not enabled.

        .. code-block:: yaml

            flows:
                load_storytelling_data:
                    steps:
                        1:
                            task: load_dataset
                            options:
                                mapping: datasets/with_person_accounts/mapping.yml
                                sql_path: datasets/with_person_accounts/data.sql
                            when: org_config.is_person_accounts_enabled
                        2:
                            task: load_dataset
                            options:
                                mapping: datasets/without_person_accounts/mapping.yml
                                sql_path: datasets/without_person_accounts/data.sql
                            when: not org_config.is_person_accounts_enabled

        """
        if self._is_person_accounts_enabled is None:
            self._is_person_accounts_enabled = any(
                field["name"] == "IsPersonAccount"
                for field in self.salesforce_client.Account.describe()["fields"]
            )
        return self._is_person_accounts_enabled

    @property
    def is_multiple_currencies_enabled(self):
        """
        Returns if the org has `Multiple Currencies <https://help.salesforce.com/articleView?id=admin_enable_multicurrency.htm>`_ enabled by checking if the `CurrencyType <https://developer.salesforce.com/docs/atlas.en-us.api.meta/api/sforce_api_objects_currencytype.htm>`_ Sobject is exposed.


        **Notes**

        - Multiple Currencies cannot be disabled once enabled.
        - Enabling `Multiple Currencies <https://help.salesforce.com/articleView?id=admin_enable_multicurrency.htm>`_ exposes both the `CurrencyType <https://developer.salesforce.com/docs/atlas.en-us.api.meta/api/sforce_api_objects_currencytype.htm>`_ and the `DatedConversionRate <https://developer.salesforce.com/docs/atlas.en-us.api.meta/api/sforce_api_objects_datedconversionrate.htm>`_ Sobjects.

        **Enable Multiple Currencies programatically**

        `Multiple Currencies <https://help.salesforce.com/articleView?id=admin_enable_multicurrency.htm>`_ can be enabled with Metadata API by updating the org's `CurrencySettings <https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_currencysettings.htm>`_ as the following:

        .. code-block:: xml

            <?xml version="1.0" encoding="UTF-8"?>
            <CurrencySettings xmlns="http://soap.sforce.com/2006/04/metadata">
                <!-- Enables Multiple Currencies -->
                <enableMultiCurrency>true</enableMultiCurrency>
            </CurrencySettings>

        **Example**

        Selectively run a task in a flow only if Multiple Currencies <https://help.salesforce.com/articleView?id=admin_enable_multicurrency.htm>`_ is or is not enabled.

        .. code-block:: yaml

            flows:
                load_storytelling_data:
                    steps:
                        1:
                            task: load_dataset
                            options:
                                mapping: datasets/with_multiple_currencies/mapping.yml
                                sql_path: datasets/with_multiple_currencies/data.sql
                            when: org_config.is_multiple_currencies_enabled
                        2:
                            task: load_dataset
                            options:
                                mapping: datasets/without_multple_currencies/mapping.yml
                                sql_path: datasets/without_multple_currencies/data.sql
                            when: not org_config.is_multiple_currencies_enabled

        """
        # When Multiple Currencies is enabled, the CurrencyType Sobject is exposed.
        # If Mutiple Currencies is not enabled:
        # - CurrencyType Sobject is not exposed.
        # - simple_salesforce raises a SalesforceResourceNotFound exception when trying to describe CurrencyType.
        # NOTE: Multiple Currencies can be enabled through Metadata API by setting CurrencySettings.enableMultiCurrency as "true". Therefore, we should try to dynamically check if Multiple Currencies is enabled.
        # NOTE: Once enabled, Multiple Currenies cannot be disabled.
        if not self._multiple_currencies_is_enabled:
            try:
                # Multiple Currencies is enabled if CurrencyType can be described (implying the Sobject is exposed).
                self.salesforce_client.CurrencyType.describe()
                self._multiple_currencies_is_enabled = True
            except SalesforceResourceNotFound:
                # CurrencyType Sobject is not exposed meaning Multiple Currencies is not enabled.
                # Keep self._multiple_currencies_is_enabled False.
                pass
        return self._multiple_currencies_is_enabled

    @property
    def is_advanced_currency_management_enabled(self):
        """
        Returns if the org has `Advanced Currency Management (ACM) <https://help.salesforce.com/articleView?id=administration_enable_advanced_currency_management.htm>`_ enabled by checking if both:

        - `Multiple Currencies <https://help.salesforce.com/articleView?id=admin_enable_multicurrency.htm>`_ is enabled (which exposes the ``DatedConversionRate`` Sobject).
        - ``DatedConversionRate`` is createable.

        **Notes**

        - If Advanced Currency Management (ACM) is disabled, ``DatedConversionRate`` is no longer createable.
        - Multiple Currencies cannot be disabled once enabled.

        **Enable Advanced Currency Managment (ACM) programatically**

        `Advanced Currency Management (ACM) <https://help.salesforce.com/articleView?id=administration_enable_advanced_currency_management.htm>`_ can be enabled with Metadata API by updating the org's `CurrencySettings <https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_currencysettings.htm>`_ as the following:

        .. code-block:: xml

            <?xml version="1.0" encoding="UTF-8"?>
            <CurrencySettings xmlns="http://soap.sforce.com/2006/04/metadata">
                <!-- Enables Multiple Currencies -->
                <enableMultiCurrency>true</enableMultiCurrency>

                <!-- Enables Advanced Currency Management (ACM) -->
                <enableCurrencyEffectiveDates>true</enableCurrencyEffectiveDates>
            </CurrencySettings>

        **Example**

        Selectively run a task in a flow only if `Advanced Currency Management (ACM) <https://help.salesforce.com/articleView?id=administration_enable_advanced_currency_management.htm>`_ is or is not enabled.

        .. code-block:: yaml

            flows:
                load_storytelling_data:
                    steps:
                        1:
                            task: load_dataset
                            options:
                                mapping: datasets/with_acm/mapping.yml
                                sql_path: datasets/with_acm/data.sql
                            when: org_config.is_advanced_currency_management_enabled
                        2:
                            task: load_dataset
                            options:
                                mapping: datasets/without_acm/mapping.yml
                                sql_path: datasets/without_acm/data.sql
                            when: not org_config.is_advanced_currency_management_enabled

        """
        # NOTE: Advanced Currency Management (ACM) can be enabled via Metadata API by setting:
        # - CurrencySettings.enableMultiCurrency as "true" to enable Multiple Currencies.
        # - CurrencySettings.enableCurrencyEffectiveDates as "true" to enable Advanced Currency Management (ACM).
        # NOTE: Once enabled, Multiple Currenies cannot be disabled.
        # Avdanced Currency Management (ACM) is enabled if:
        # - Multiple Currencies is enabled (which exposes the DatedConversionRate Sobject)
        # - DatedConversionRate Sobject is createable.
        # Advanced Currency Management (ACM) can be disabled, and if so, DatedConversionRate Sobject will no longer be createable.
        try:
            # Always check the describe since ACM can be disabled.
            return self.salesforce_client.DatedConversionRate.describe()["createable"]
        except SalesforceResourceNotFound:
            # DatedConversionRate Sobject is not exposed meaning Multiple Currencies is not enabled.
            return False

    @property
    def is_survey_advanced_features_enabled(self) -> bool:
        return any(
            f["name"] == "PermissionsAllowSurveyAdvancedFeatures"
            for f in self.salesforce_client.PermissionSet.describe()["fields"]
        )

    def resolve_04t_dependencies(self, dependencies):
        """Look up 04t SubscriberPackageVersion ids for 1GP project dependencies"""
        from cumulusci.core.dependencies.dependencies import (
            PackageNamespaceVersionDependency,
            PackageVersionIdDependency,
        )

        # Circular dependency.

        new_dependencies = []
        for dependency in dependencies:
            if isinstance(dependency, PackageNamespaceVersionDependency):
                # get the SubscriberPackageVersion id
                key = f"{dependency.namespace}@{dependency.version}"
                version_info = self.installed_packages.get(key)
                if version_info:
                    new_dependencies.append(
                        PackageVersionIdDependency(
                            version_id=version_info[0].id,
                            package_name=dependency.package_name,
                        )
                    )
                else:
                    raise DependencyResolutionError(
                        f"Could not find 04t id for package {key} in org {self.name}"
                    )
            else:
                new_dependencies.append(dependency)

        return new_dependencies
