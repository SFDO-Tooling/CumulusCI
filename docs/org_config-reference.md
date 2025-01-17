# org_config Object Reference

The `org_config` object can be used in the `cumulusci.yml` file to read a large number number of attributes of the Salesforce org currently used. For example, in a [custom flow step](https://cumulusci.readthedocs.io/en/stable/config.html#add-a-flow-step), you can use a `when` clause to adapt the behavior of the new step to the type of org (scratch org or not) by referencing the `org_config.scratch` attribute.

The following information is documented here in the application's source code :
https://github.com/SFDO-Tooling/CumulusCI/blob/main/cumulusci/core/config/org_config.py

## org_config Object Attributes

-   `access_token` : access token currently used to authenticate with Salesforce
-   `installed_packages` : comma-separated list of package names; a `dict` mapping a namespace or metadata package ID (starts with `033`) to the installed package version(s) matching that identifier. All values are lists, because multiple second-generation packages may be installed with the same namespace. The beta version of a package is represented as "1.2.3b5", where 5 is the build number.
-   `instance_url` : eg `https://crazy-demo.scratch.my.salesforce.com`
-   `instance_name` : eg `crazy-demo`
-   `is_advanced_currency_management_enabled` : `true` or `false`
-   `is_multiple_currencies_enabled`: `true` or `false`
-   `is_person_accounts_enabled` : `true` or `false`
-   `is_sandbox` : `true` if the org is a sandbox
-   `is_survey_advanced_features_enabled`: `true` or `false`
-   `lightning_base_url` : base url ending with `.lightning.force.com`
-   `namespace` : namespace of the org
-   `namespaced` : `true` if the org has a namespace
-   `org_id` : Organization ID of the Salesforce org
-   `org_type` : eg "Enterprise Edition" or "Developer Edition"
-   `organization_sobject` : The Organization object (see the [Salesforce documentation for the Organization SObject](https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_organization.htm)) for the org.
-   `scratch` : `True` when the org is a scratch org.
-   `start_url`: the frontdoor URL that results in an instant login, like `https://mydomain.my.salesforce.com/secur/frontdoor.jsp?sid=...`
-   `user_id` : user ID of the current Salesforce user
-   `userinfo`: user OAuth2 information (see https://help.salesforce.com/s/articleView?id=sf.remoteaccess_using_userinfo_endpoint.htm)
-   `username` : username of the current Salesforce user

## Other org_config Object Attributes

-   `config_file`
-   `config_name`
-   `latest_api_version`
-   `name`
-   `salesforce_client`
-   `sfdx_alias`

## org_config Object Methods

-   `has_minimum_package_version(package_identifier, version_identifier)`: `true` if the org has a version of the specified package that is equal to or newer than the supplied version identifier.
    The package identifier may be either a namespace or a `033` MetadataPackage ID.
    The version identifier should be in "1.2.3" or "1.2.3b4" format.

    `when` expressions can use the `has_minimum_package_version` method to check if a package is installed with a sufficient version.

    For example:
    `when: org_config.has_minimum_package_version("namespace", "1.0")`

    See a real-life example here : https://trailhead.salesforce.com/fr/trailblazer-community/feed/0D54V00007erukZSAQ

-   `get_community_info(community_name, force_refresh=False)`: Returns the community information for the given community (see https://developer.salesforce.com/docs/atlas.en-us.chatterapi.meta/chatterapi/connect_responses_community.htm)

    An API call will be made the first time this method is used,
    and the return values will be cached. Subsequent calls will
    not call the API unless the requested community name is not in
    the cached results, or unless the force_refresh parameter is
    set to True
