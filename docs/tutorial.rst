========
Tutorial
========

Part 1: Installing CumulusCI
============================

Requirements
------------

* You must have Python version 2.7.x installed
* A local git repository containing Salesforce metadata in the `src/` subfolder OR fork then clone CumulusCI-Test for demo::

    git clone https://github.com/YOUR_GITHUB_FORK_USER/CumulusCI-Test

If you are using the CumulusCI-Test repo, enable Chatter in your dev org.

* Ensure you have virtualenv installed by either installing a package for your OS or installing with pip::

    pip install virtualenv


Using virtualenv
----------------

Run the following::

    virtualenv ~/cumulusci_venv
    source ~/cumulusci_venv/bin/activate

Once activated, you will see (cumulusci_venv) at the start of your shell prompt to let you know the virtualenv is active.  From this point, any Python packages you install will be installed only into the virtualenv and leave your system's Python alone.

If you want to always have the CumulusCI commands available, you can add the following line to your ~/.bash_profile::

    source ~/cumulusci_venv/bin/activate

More information about using virtualenv is available at: http://docs.python-guide.org/en/latest/dev/virtualenvs/


Installation
------------

With your virtualenv activated::

    pip install cumulusci

This will install the latest version of CumulusCI and all its dependencies into the virtualenv.  You can verify the installation by running::

    $ cumulusci2
    Usage: cumulusci2 [OPTIONS] COMMAND [ARGS]...

    Options:
    --help  Show this message and exit.

    Commands:
    flow     Commands for finding and running flows for a...
    org      Commands for connecting and interacting with...
    project  Commands for interacting with project...
    shell    Drop into a python shell
    task     Commands for finding and running tasks for a...
    version  Print the current version of CumulusCI

Part 2: Project Configuration
=============================

Keychain Key
------------

The cumulusci2 command stores all credentials in AES encrypted files under the ~/.cumulusci folder.  To use the CLI, you must set the environment variable `CUMULUSCI_KEY` to a 16 character string which is your password to access your keychain.  Do not forget this password!::

    $ export CUMULUSCI_KEY=0a2b4c6d8e0f2g4h  # Must be 16 characters long

Project Initialization
----------------------

The `cumulusci2` command is git repository aware.  Changing directories from one local git repository to another will change the project context.  Each project context isolates the following:

* Connected App: The Salesforce Connected App to use for OAuth authentication
* Orgs: Connected Salesforce Orgs are stored in a project specific keychain
* Services: Named service connections such as Github, ApexTestsDB, and mrbelvedere

If you run the `cumulusci2` command from outside a git repository, it will generate an error::

    $ cd ~

    $ cumulusci2
    No repository found in current path.  You must be inside a repository to initialize the project configuration

If you run the `cumulusci2 project info` command from inside a git repository that has already been set up for CumulusCI, it will print the project info::

    $ cd path/to/your/repo

    $ cumulusci2 project info
    {
        "apexdoc": {
            "banner": null,
            "homepage": null,
            "url": "https://github.com/SalesforceFoundation/ApexDoc/releases/download/1.7/apexdoc.jar"
        },
        "dependencies": null,
        "git": {
            "default_branch": "master",
            "prefix_beta": "beta/",
            "prefix_feature": "feature/",
            "prefix_release": "release/"
        },
        "name": "MyRepoName",
        "package": {
            "api_version": 38.0,
            "install_class": null,
            "name": "My Repo Name",
            "name_managed": null,
            "namespace": "mynamespace",
            "uninstall_class": null
        },
        "test": {
            "name_match": "%_TEST%"
        }
    }

If you run the same command from inside a git repository that has not yet been set up for CumulusCI, you will get an error::

    $ cumulusci2 project info
    Usage: cumulusci2 project info [OPTIONS]
    Error: No project configuration found.  You can use the "project init" command to initilize the project for use with CumulusCI

As the instructions say, you can use the `cumulusci2 project init` command to initialize the configuration::

    $ cumulusci2 project init
    Name: MyRepoName
    Package name: My Repo Name
    Package namespace: mynamespace
    Package api version [38.0]:
    Git prefix feature [feature/]:
    Git default branch [master]:
    Git prefix beta [beta/]:
    Git prefix release [release/]:
    Test namematch [%_TEST%]:
    Your project is now initialized for use with CumulusCI
    You can use the project edit command to edit the project's config file

    $ cat cumulusci.yml
    project:
        name: MyRepoName
        package:
            name: My Repo Name
            namespace: mynamespace

The newly created `cumulusci.yml` file is the configuration file for wiring up any project specific tasks, flows, and CumulusCI customizations for this project.  You can add and commit it to your git repository::

    $ git add cumulusci.yml
    $ git commit -m "Initialized CumulusCI Configuration"

Part 3: Connecting Salesforce Orgs
==================================

Creating a Connected App
------------------------

First, you will need to create a Salesforce Connected App with the following steps:

* In a Salesforce Org, go to Setup -> Create -> Apps
* Click "New" under Connected Apps

  * Enter a unique value for the Name and API Name field
  * Enter a Contact Email
  * Check "Enable OAuth Settings"
  * Set the Callback URL to http://localhost:8080/callback
  * Enable the scopes: full, refresh_token, and web
  * Save the Connected App

* Click the Manage button, then click Edit
* Record the client_id (Consumer Key) and the client_secret (Consumer Secret)

Configuring the Project's Connected App
---------------------------------------

Configure the Connected App in your project's keychain::

    $ cumulusci2 org config_connected_app
    client_id:
    client_secret:

Connecting an Org
-----------------

Configuring the Connected App is a one time operation per project.  Once configured, you can start connecting Salesforce Orgs to your project's keychain::

    $ cumulusci2 org connect dev

    Launching web browser for URL https://login.salesforce.com/services/oauth2/authorize?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost:8080/callback&scope=web%20full%20refresh_token&prompt=login
    Spawning HTTP server at http://localhost:8080/callback with timeout of 300 seconds.
    If you are unable to log in to Salesforce you can press ctrl+c to kill the server and return to the command line.

This should open a browser on your computer pointed to the Salesforce login page.  Log in and then grant access to the app.  Note that since the login to capture credentials occurs in your normal browser, you can use browser password managers such as LastPass to log in.  Once access is granted and you see a browser page that says `OK` you can close the browser tab and return to the terminal.  Your org is now connected via OAuth and CumulusCI never needs to know your actual user password.  As an added benefit, OAuth authentication remains valid even after password changes::

    $ cumulusci2 org list

    org        is_default
    ---------  ----------
    dev

Default Org
-----------

You can set a default org on your project which will then be used as the org for all tasks and flows.::

    $ cumulusci2 org default dev

    dev is now the default org

    $ cumulusci2 org list

    org        is_default
    ---------  ----------
    dev        *

    $ cumulusci2 org default dev --unset

    dev is no longer the default org.  No default org set.

    $ cumulusci2 org list

    org        is_default
    ---------  ----------
    dev

So we can start running some tasks, let's set dev as our default again::

    $ cumulusci2 org default dev

Part 4: Running Tasks
=====================

Once you have some orgs connected, you can start running tasks against them.  First, you'll want to get a list of tasks available to run::

    $ cumulusci2 task list

    task                            description
    ------------------------------  -------------------------------------------------------------------------------------------------------
    create_package                  Creates a package in the target org with the default package name for the project
    create_managed_src              Modifies the src directory for managed deployment.  Strips //cumulusci-managed from all Apex code
    create_unmanaged_ee_src         Modifies the src directory for unmanaged deployment to an EE org
    deploy                          Deploys the src directory of the repository to the org
    deploy_pre                      Deploys all metadata bundles under unpackaged/pre/
    deploy_post                     Deploys all metadata bundles under unpackaged/post/
    deploy_post_managed             Deploys all metadata bundles under unpackaged/post/
    get_installed_packages          Retrieves a list of the currently installed managed package namespaces and their versions
    github_clone_tag                Lists open pull requests in project Github repository
    github_master_to_feature        Merges the latest commit on the master branch into all open feature branches
    github_pull_requests            Lists open pull requests in project Github repository
    github_release                  Creates a Github release for a given managed package version number
    github_release_notes            Generates release notes by parsing pull request bodies of merged pull requests between two tags
    install_managed                 Install the latest managed production release
    install_managed_beta            Installs the latest managed beta release
    push_all                        Schedules a push upgrade of a package version to all subscribers
    push_qa                         Schedules a push upgrade of a package version to all orgs listed in push/orgs_qa.txt
    push_sandbox                    Schedules a push upgrade of a package version to all subscribers
    push_trial                      Schedules a push upgrade of a package version to Trialforce Template orgs listed in push/orgs_trial.txt
    retrieve_packaged               Retrieves the packaged metadata from the org
    retrieve_src                    Retrieves the packaged metadata into the src directory
    revert_managed_src              Reverts the changes from create_managed_src
    revert_unmanaged_ee_src         Reverts the changes from create_unmanaged_ee_src
    run_tests                       Runs all apex tests
    run_tests_debug                 Runs all apex tests
    run_tests_managed               Runs all apex tests in the packaging org or a managed package subscriber org
    uninstall_managed               Uninstalls the managed version of the package
    uninstall_packaged              Uninstalls all deleteable metadata in the package in the target org
    uninstall_packaged_incremental  Deletes any metadata from the package in the target org not in the local workspace
    uninstall_src                   Uninstalls all metadata in the local src directory
    uninstall_pre                   Uninstalls the unpackaged/pre bundles
    uninstall_post                  Uninstalls the unpackaged/post bundles
    uninstall_post_managed          Uninstalls the unpackaged/post bundles
    update_admin_profile            Retrieves, edits, and redeploys the Admin.profile with full FLS perms for all objects/fields
    update_dependencies             Installs all dependencies in project__dependencies into the target org
    update_meta_xml                 Updates all -meta.xml files to have the correct API version and extension package versions
    update_package_xml              Updates src/package.xml with metadata in src/
    update_package_xml_managed      Updates src/package.xml with metadata in src/
    upload_beta                     Uploads a beta release of the metadata currently in the packaging org
    upload_production               Uploads a beta release of the metadata currently in the packaging org

Getting Task Info
-----------------

You can view the details on an individual task::

    $ cumulusci2 task info update_package_xml

    Description: Updates src/package.xml with metadata in src/
    Class: cumulusci.tasks.metadata.package.UpdatePackageXml

    Default Option Values
        path: src

    Option   Required  Description
    -------  --------  ----------------------------------------------------------------------------------------------
    path     *         The path to a folder of metadata to build the package.xml from
    delete             If True, generate a package.xml for use as a destructiveChanges.xml file for deleting metadata
    managed            If True, generate a package.xml for deployment to the managed package packaging org
    output             The output file, defaults to <path>/package.xml

Running a Task
--------------

You can run a task::

    $ cumulusci2 task run update_package_xml
    
    2016-11-03 11:57:53: Generating src/package.xml from metadata in src

Task Options
------------

And you can run a task passing any of the options via the command line::

    $ cumulusci2 task run update_package_xml -o managed True -o output managed_package.xml

    INFO:UpdatePackageXml:Generating managed_package.xml from metadata in src

Running Tasks Against a Salesforce Org
--------------------------------------

The update_package_xml task works only on local files and does not require a connection to a Salesforce org.  The deploy task uses the Metadata API to deploy the src directory to the target org and thus requires a Salesforce org.  Since we already made dev our default org, we can still just run the task against our dev org by calling it without any options::

    $ cumulusci2 task info deploy

    Description: Deploys the src directory of the repository to the org
    Class: cumulusci.tasks.salesforce.Deploy

    Default Option Values
        path: src

    Option  Required  Description
    ------  --------  ----------------------------------------------
    path    *         The path to the metadata source to be deployed

    $ cumulusci2 task run deploy

    2016-11-03 11:58:01: Pending
    2016-11-03 11:58:05: [InProgress]: Processing Type: CustomObject
    2016-11-03 11:58:06: [InProgress]: Processing Type: CustomObject
    2016-11-03 11:58:08: [InProgress]: Processing Type: QuickAction
    2016-11-03 11:58:09: [InProgress]: Processing Type: ApexClass
    2016-11-03 11:58:13: [Done]
    2016-11-03 11:58:14: [Success]: Succeeded

Now that the metadata is deployed, you can run the tests::

    $ cumulusci2 task info run_tests
    Description: Runs all apex tests
    Class: cumulusci.tasks.salesforce.RunApexTests

    Option             Required  Description
    -----------------  --------  ------------------------------------------------------------------------------------------------------
    test_name_exclude            Query to find Apex test classes to exclude ("%" is wildcard).  Defaults to project__test__name_exclude
    managed                      If True, search for tests in the namespace only.  Defaults to False
    test_name_match    *         Query to find Apex test classes to run ("%" is wildcard).  Defaults to project__test__name_match
    poll_interval                Seconds to wait between polling for Apex test results.  Defaults to 3
    namespace                    Salesforce project namespace.  Defaults to project__package__namespace
    junit_output                 File name for JUnit output.  Defaults to test_results.xml

    $ cumulusci2 task run run_tests
    2016-11-03 12:01:04: Running query: SELECT Id, Name FROM ApexClass WHERE NamespacePrefix = null AND (Name LIKE '%_TEST%')
    2016-11-03 12:01:05: Found 2 test classes
    2016-11-03 12:01:05: Queuing tests for execution...
    2016-11-03 12:01:07: Completed: 0  Processing: 0  Queued: 2
    2016-11-03 12:01:10: Completed: 2  Processing: 0  Queued: 0
    2016-11-03 12:01:10: Apex tests completed
    2016-11-03 12:01:12: Class: SampleClass_TEST
    2016-11-03 12:01:12: 	Pass: fillInFirstNameTest
    2016-11-03 12:01:12: Class: SamplePage_CTRL_TEST
    2016-11-03 12:01:12: 	Pass: getSamplesTest
    2016-11-03 12:01:12: --------------------------------------------------------------------------------
    2016-11-03 12:01:12: Pass: 2  Fail: 0  CompileFail: 0  Skip: 0
    2016-11-03 12:01:12: --------------------------------------------------------------------------------

Part 5: Flows
=============

Listing Flows
-------------

Flows are simply named sequences of tasks.  Flows are designed to be run against a single target org.  CumulusCI comes with a number of best practice flows out of the box.::

    $ cumulusci2 flow list

    flow          description
    ------------  --------------------------------------------------------------------------------
    dev_org       Deploys the unmanaged package metadata and all dependencies to the target org
    ci_feature    Deploys the unmanaged package metadata and all dependencies to the target org
    ci_master     Deploys the managed package metadata and all dependencies to the packaging org
    ci_beta       Installs a beta version and runs tests
    ci_release    Installs a production release version and runs tests
    release_beta  Uploads and releases a beta version of the metadata currently in packaging
    unmanaged_ee  Deploys the unmanaged package metadata and all dependencies to the target EE org

Running a Flow
--------------

To set up our newly connected dev org, run the dev_org flow::

    $ cumulusci2 flow run dev_org

    2016-11-03 12:01:48: ---------------------------------------
    2016-11-03 12:01:48: Initializing flow class BaseFlow:
    2016-11-03 12:01:48: ---------------------------------------
    2016-11-03 12:01:48: Flow Description: Deploys the unmanaged package metadata and all dependencies to the target org
    2016-11-03 12:01:48: Tasks:
    2016-11-03 12:01:48:   create_package: Creates a package in the target org with the default package name for the project
    2016-11-03 12:01:48:   update_dependencies: Installs all dependencies in project__dependencies into the target org
    2016-11-03 12:01:48:   deploy_pre: Deploys all metadata bundles under unpackaged/pre/
    2016-11-03 12:01:48:   deploy: Deploys the src directory of the repository to the org
    2016-11-03 12:01:48:   uninstall_packaged_incremental: Deletes any metadata from the package in the target org not in the local workspace
    2016-11-03 12:01:48:   deploy_post: Deploys all metadata bundles under unpackaged/post/
    2016-11-03 12:01:48: 
    2016-11-03 12:01:48: Running task: create_package
    2016-11-03 12:01:49: Options:
    2016-11-03 12:01:49:   api_version: 33.0
    2016-11-03 12:01:49:   package: CumulusCI-Test
    2016-11-03 12:01:49: Pending
    2016-11-03 12:01:53: [Done]
    2016-11-03 12:01:54: [Success]: Succeeded
    2016-11-03 12:01:54: 
    2016-11-03 12:01:54: Running task: update_dependencies
    2016-11-03 12:01:56: Options:
    2016-11-03 12:01:56: Project has no dependencies, doing nothing
    2016-11-03 12:01:56: 
    2016-11-03 12:01:56: Running task: deploy_pre
    2016-11-03 12:01:56: Options:
    2016-11-03 12:01:56:   path: unpackaged/pre
    2016-11-03 12:01:56: Deploying all metadata bundles in path /Users/jlantz/dev/CumulusCI-Test/unpackaged/pre
    2016-11-03 12:01:56: Deploying bundle: unpackaged/pre/account_record_types
    2016-11-03 12:01:56: Pending
    2016-11-03 12:01:58: [InProgress]: Processing Type: CustomObject
    2016-11-03 12:02:00: [InProgress]: Processing Type: CustomObject
    2016-11-03 12:02:02: [Done]
    2016-11-03 12:02:03: [Success]: Succeeded
    2016-11-03 12:02:03: Deploying bundle: unpackaged/pre/opportunity_record_types
    2016-11-03 12:02:03: Pending
    2016-11-03 12:02:07: [InProgress]: Processing Type: CustomObject
    2016-11-03 12:02:08: [InProgress]: Processing Type: CustomObject
    2016-11-03 12:02:09: [InProgress]: Processing Type: CustomObject
    2016-11-03 12:02:12: [Done]
    2016-11-03 12:02:13: [Success]: Succeeded
    2016-11-03 12:02:13: 
    2016-11-03 12:02:13: Running task: deploy
    2016-11-03 12:02:14: Options:
    2016-11-03 12:02:14:   path: src
    2016-11-03 12:02:14: Pending
    2016-11-03 12:02:18: [InProgress]: Processing Type: CustomObject
    2016-11-03 12:02:19: [InProgress]: Processing Type: CustomObject
    2016-11-03 12:02:20: [InProgress]: Processing Type: QuickAction
    2016-11-03 12:02:22: [InProgress]: Processing Type: ApexClass
    2016-11-03 12:02:28: [Done]
    2016-11-03 12:02:29: [Success]: Succeeded
    2016-11-03 12:02:29: 
    2016-11-03 12:02:29: Running task: uninstall_packaged_incremental
    2016-11-03 12:02:29: Options:
    2016-11-03 12:02:29:   path: src
    2016-11-03 12:02:29:   package: CumulusCI-Test
    2016-11-03 12:02:29: Retrieving metadata in package CumulusCI-Test from target org
    2016-11-03 12:02:29: Pending
    2016-11-03 12:02:34: [Done]
    2016-11-03 12:02:35: Deleting metadata in package CumulusCI-Test from target org
    2016-11-03 12:02:35: Pending
    2016-11-03 12:02:41: [Done]
    2016-11-03 12:02:42: [Success]: Succeeded
    2016-11-03 12:02:42: 
    2016-11-03 12:02:42: Running task: deploy_post
    2016-11-03 12:02:43: Options:
    2016-11-03 12:02:43:   namespace_token: %%%NAMESPACE%%%
    2016-11-03 12:02:43:   path: unpackaged/post
    2016-11-03 12:02:43:   namespace: ccitest
    2016-11-03 12:02:43:   managed: False
    2016-11-03 12:02:43:   filename_token: ___NAMESPACE___
    2016-11-03 12:02:43: Deploying all metadata bundles in path /Users/jlantz/dev/CumulusCI-Test/unpackaged/post
    2016-11-03 12:02:43: Deploying bundle: unpackaged/post/salesforce1
    2016-11-03 12:02:43: Pending
    2016-11-03 12:02:50: [Done]
    2016-11-03 12:02:51: [Success]: Succeeded
    
Part 6: Digging Deeper
======================

Custom Tasks
------------

Create a local python tasks module::

    $ mkdir tasks
    $ touch tasks/__init__.py

Create the file `tasks/salesforce.py` with the following content::

    from cumulusci.tasks.salesforce import BaseSalesforceApiTask
    from cumulusci.tasks.salesforce import BaseSalesforceToolingApiTask

    class ListContacts(BaseSalesforceApiTask):

        def _run_task(self):
            res = self.sf.query('Select Id, FirstName, LastName from Contact LIMIT 10')
            for contact in res['records']:
                self.logger.info('{Id}: {FirstName} {LastName}'.format(**contact))

    class ListApexClasses(BaseSalesforceToolingApiTask):

        def _run_task(self):
            res = self.tooling.query('Select Id, Name, NamespacePrefix from ApexClass LIMIT 10')
            for apexclass in res['records']:
                self.logger.info('{Id}: [{NamespacePrefix}] {Name}'.format(**apexclass))

Finally, wire in your new tasks by editing the cumulusci.yml file in your repo and adding the following lines::

    tasks:
        list_contacts:
            description: Prints out 10 Contacts from the target org using the Enterprise API
            class_path: tasks.salesforce.ListContacts
        list_apex_classes:
            description: Prints out 10 ApexClasses from the target org using the Tooling API
            class_path: tasks.salesforce.ListApexClasses

Now your new tasks are available in the task list::

    $ cumulusci2 task list
    task                            description
    ------------------------------  ---------------------------------------------------------------------------------
    create_package                  Creates a package in the target org with the default package name for the project
    ...
    list_contacts                   Prints out 10 Contacts from the target org using the Enterprise API
    list_apex_classes               Prints out 10 ApexClasses from the target org using the Tooling API

Run the tasks::

    $ cumulusci2 task run list_contacts

    2016-11-03 12:04:34: 003j00000045WfwAAE: Siddartha Nedaerk
    2016-11-03 12:04:34: 003j00000045WfxAAE: Jake Llorrac
    2016-11-03 12:04:34: 003j00000045WfeAAE: Rose Gonzalez
    2016-11-03 12:04:34: 003j00000045WffAAE: Sean Forbes
    2016-11-03 12:04:34: 003j00000045WfgAAE: Jack Rogers
    2016-11-03 12:04:34: 003j00000045WfhAAE: Pat Stumuller
    2016-11-03 12:04:34: 003j00000045WfiAAE: Andy Young
    2016-11-03 12:04:34: 003j00000045WfjAAE: Tim Barr
    2016-11-03 12:04:34: 003j00000045WfkAAE: John Bond
    2016-11-03 12:04:34: 003j00000045WflAAE: Stella Pavlova

    $ cumulusci2 task run list_apex_classes

    2016-11-03 12:04:40: 01pj000000164zgAAA: [npe01] Tests
    2016-11-03 12:04:40: 01pj000000164zeAAA: [npe01] IndividualAccounts
    2016-11-03 12:04:40: 01pj000000164zfAAA: [npe01] NPSPPkgVersionCheck
    2016-11-03 12:04:40: 01pj000000164zdAAA: [npe01] Constants
    2016-11-03 12:04:40: 01pj000000164zsAAA: [npe03] RecurringDonations
    2016-11-03 12:04:40: 01pj000000164ztAAA: [npe03] RecurringDonationsPkgVersionCheck
    2016-11-03 12:04:40: 01pj000000164zuAAA: [npe03] RecurringDonations_BATCH
    2016-11-03 12:04:40: 01pj000000164zvAAA: [npe03] RecurringDonations_SCHED
    2016-11-03 12:04:40: 01pj000000164zwAAA: [npe03] RecurringDonations_TEST
    2016-11-03 12:04:40: 01pj000000164zxAAA: [npe4] Relationships_INST

Further Exploration
-------------------

These will be filled out in more detail in the future but are a brief overview of commands to explore next::

    $ cumulusci2 project connect_github
    $ cumulusci2 project connect_apextestsdb
    $ cumulusci2 project connect_mrbelvedere


Environment Keychain
--------------------

The keychain class can be overridden to change storage implementations.  The default keychain for the cumulusci2 CLI stores AES encrypted files under `~/.cumulusci`.  The EnvironmentProjectKeychain class provides a keychain implementation which receives its credentials from environment variables.  This is useful for using the CLI on CI servers such as Jenkins or CircleCI.::

    $ cumulusci2 org connected_app
    $ cumulusci2 org info feature
    $ cumulusci2 org info packaging
    $ cumulusci2 org info beta
    $ cumulusci2 project show_github
    $ export CUMULUSCI_KEYCHAIN_CLASS=cumulusci.core.keychain.EnvironmentProjectKeychain
    $ cumulusci2 org list
    $ export CUMULUSCI_CONNECTED_APP="{__COPIED_FROM_ABOVE__}"
    $ export CUMULUSCI_ORG_feature="{__COPIED_FROM_ABOVE__}"
    $ export CUMULUSCI_ORG_packaging="{__COPIED_FROM_ABOVE__}"
    $ export CUMULUSCI_ORG_beta="{__COPIED_FROM_ABOVE__}"
    $ export CUMULUSCI_SERVICE_github="{__COPIED_FROM_ABOVE__}"
    $ cumulusci2 org list
    $ cumulusci2 task run --org feature deploy
