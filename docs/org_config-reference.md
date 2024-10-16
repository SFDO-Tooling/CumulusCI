# org_config Object Reference

The `org_config` object can be used in the `cumulusci.yml` file to read a large number number of attributes of the Salesforce org currently used. For example, in a [custom flow step](https://cumulusci.readthedocs.io/en/stable/config.html#add-a-flow-step), you can use a `when`clause to adapt the behavior of the new step to the type of org (scratch org or not) by referencing the `org_config.scratch` attribute.

## org_config Object Attributes

-   `scratch` : true indicates the org is a scratch org. False indicates it is a persistent org
-   `is_person_accounts_enabled` : `true` or `false`
-   `installed_packages` : comma-separated list of package names
-   `org_id` : orgid of the Salesforce org
-   `namespace` : namespace of the org
-   `namespaced` : `true` if the org has a namespace
-   `instance_url` : eg https://crazy-demo.scratch.my.salesforce.com
-   `access_token` : access token currently used to authenticate with Salesforce
-   `username` : username of the current Salesforce user
-   `user_id` : user id of the current Salesforce user
-   `is_multiple_currencies_enabled`: `true` or `false`
-   `is_advanced_currency_management_enabled` : `true` or `false`
-   `org_type` : eg "Enterprise Edition" or "Developer Edition"
-   `is_sandbox` : `true` if the org is a sandbox
-   `organization_sobject` : whole Organization SObject (see the [Salesforce documentation for the Organization SObject](https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_organization.htm))

Also :

-   `name`
-   `start_url`
-   `sfdx_alias`
-   `config_file`
-   `lightning_base_url`
-   `latest_api_version`
