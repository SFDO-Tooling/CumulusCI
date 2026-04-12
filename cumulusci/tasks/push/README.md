# Push Upgrade API Scripts

These scripts are designed to work with the Salesforce Push Upgrade API (in Pilot in Winter 16) which exposes new objects via the Tooling API that allow interacting with push upgrades in a packaging org. The main purpose of these scripts is to use the Push Upgrade API to automate push upgrades through Jenkins.

# push_api.py - Python Wrapper for Push Upgrade API

This python file provides wrapper classes around the Tooling API objects and abstracts interaction with them and their related data to make writing scripts easier. All the other scripts in this directory use the SalesforcePushApi wrapper to interact with the Tooling API.

Initializing the SalesforcePushApi wrapper can be done with the following python code:

    push_api = SalesforcePushApi(sf_user, sf_pass, sf_serverurl)

You can also pass two optional keyword args to the initialization to control the wrapper's behavior

-   **lazy**: A list of objects that should be lazily looked up. Currently, the only implementations for this are 'jobs' and 'subscribers'. If either are included in the list, they will be looked up on demand when needed by a referenced object. For example, if you are querying all jobs and subscribers is not set to lazy, all subscribers will first be retrieved. If lazy is enabled, subscriber orgs will only be retrieved when trying to resolve references for a particular job. Generally, if you have a lot of subscribers and only expect your script to need to lookup a small number of them, enabling lazy for subscribers will reduce api calls and cause the script to run faster.

-   **default_where**: A dictionary with Push Upgrade API objects as key and a value containing a SOQL WHERE clause statement which is applied to all queries against the object to effectively set the universe for a given object. For example:
    default_where = {'PackageSubscriber': "OrgType = 'Sandbox'"}

In the example above, the wrapper would never return a PackageSubscriber which is not a Sandbox org.

# Push Scripts

## Common Environment Variables

The push scripts are all designed to receive their arguments via environment variables. The following are common amongst all of the Push Scripts

-   **SF_USERNAME**: The Salesforce username for the packaging org
-   **SF_PASSWORD**: The Salesforce password and security token for the packaging org
-   **SF_SERVERURL**: The login url for the Salesforce packaging org.

## get_version_id.py

Takes a namespace and version string and looks up the given version. Returns the version's Salesforce Id.

The script handles parsing the version number string into a SOQL query against the MetadataPackageVersion object with the correct MajorVersion, MinorVersion, PatchVersion, ReleaseState, and BuildNumber (i.e. Beta number).

### Required Environment Variables

-   **NAMESPACE**: The Package's namespace prefix
-   **VERSION_NUMBER**: The version number string.

## orgs_for_push.py

Takes a MetadataPackageVersion Id and optionally a where clause to filter Subscribers and returns a list of OrgId's one per line which can be fed into the schedule_push.py script.

### Required Environment Variables

-   **VERSION**: The MetadataPackageVersion Id of the version you want to push upgrade. This is used to look for all users not on the version or a newer version

### Optional Environment Variables

-   **SUBSCRIBER_WHERE**: An extra filter to be applied to all Subscriber queries. For example, setting this to OrgType = 'Sandbox' would find all Sandbox orgs eligible for push upgrade to the specified version

## failed_orgs_for_push.py

Takes a PackagePushRequest Id and optionally a where clause to filter Subscribers and returns a list of OrgId's one per line for all orgs which failed the
