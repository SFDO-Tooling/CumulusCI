========
Tutorial
========

This tutorial is for macOS. Linux and Windows are not yet officially supported but should work for the most part. We have added some Windows and Linux info where possible.

Part 1: Installing CumulusCI
============================

Before starting the tutorial, make sure you've completed :ref:`installing CumulusCI`.

Part 2: Project Configuration
=============================

In order to use CumulusCI you will need a local git repository containing Salesforce metadata in the `src/` subfolder.

If you want to use our example project, fork our CumulusCI-Test repo:

.. code-block:: console

    $ git clone https://github.com/YOUR_GITHUB_FORK_USER/CumulusCI-Test

If you are using the CumulusCI-Test repo with a Developer Edition Salesforce org, you will need to enable Chatter in the org if it is not already enabled.  With Salesforce DX Scratch Orgs, this is handled for you.

Project Initialization
----------------------

The `cci` command is git repository aware. Changing directories from one local git repository to another will change the project context. Each project context isolates the following:

* Orgs: Connected Salesforce Orgs are stored in a project specific keychain
* Services: Named service connections such as Github

If you run the `cci` command from outside a git repository, it will generate an error.

If you run the `cci project info` command from inside a git repository that has already been set up for CumulusCI, it will print the project info:

.. code-block:: console

    $ cd path/to/your/repo

.. code-block:: console

    $ cci project info
    name: CumulusCI Test
    package:
        name: CumulusCI Test
        name_managed: None
        namespace: ccitest
        install_class: None
        uninstall_class: None
        api_version: 33.0
    git:
        default_branch: main
        prefix_feature: feature/
        prefix_beta: beta/
        prefix_release: release/
        release_notes:
            parsers:
                1:
                    class_path: cumulusci.tasks.release_notes.parser.GithubLinesParser
                    title: Critical Changes
                2:
                    class_path: cumulusci.tasks.release_notes.parser.GithubLinesParser
                    title: Changes
                3:
                    class_path: cumulusci.tasks.release_notes.parser.GithubIssuesParser
                    title: Issues Closed
                4:
                    class_path: cumulusci.tasks.release_notes.parser.GithubLinesParser
                    title: New Metadata
                5:
                    class_path: cumulusci.tasks.release_notes.parser.GithubLinesParser
                    title: Deleted Metadata
        repo_url: https://github.com/SFDO-Tooling/CumulusCI-Test
    test:
        name_match: %_TEST%

If you run the same command from inside a git repository that has not yet been set up for CumulusCI, you will get an error:

.. code-block:: console

    $ cci project info
    The file cumulusci.yml was not found in the repo root. Are you in a CumulusCI project directory?

You can use the `cci project init` command to initialize the configuration:

.. code-block:: console

    $ cci project init
    Name: MyRepoName
    Package name: My Repo Name
    Package namespace: mynamespace
    Package api version [38.0]:
    Git prefix feature [feature/]:
    Git default branch [main]:
    Git prefix beta [beta/]:
    Git prefix release [release/]:
    Test namematch [%_TEST%]:
    Your project is now initialized for use with CumulusCI
    You can use the project edit command to edit the project's config file

.. code-block:: console

    $ cat cumulusci.yml
    project:
        name: MyRepoName
        package:
            name: My Repo Name
            namespace: mynamespace

The newly created `cumulusci.yml` file is the configuration file for wiring up any project specific tasks, flows, and CumulusCI customizations for this project. You can add and commit it to your git repository:

.. code-block:: console

    $ git add cumulusci.yml
    $ git commit -m "Initialized CumulusCI Configuration"

GitHub Service
--------------

To get through some of the tasks later in the tutorial, you will need to connect GitHub as a service in cci.

Go to https://github.com/settings/tokens/new and create a new personal access token with both "repo" and "gist" scopes specified. Copy the access token to use as the password when configuring the GitHub service.

Run the following and provide your GitHub username and token:

.. code-block:: console

    $ cci service connect github

Once you've configured the `github` service it will be available to all projects.  Services are stored in the global CumulusCI keychain by default.

Part 3: Connecting Salesforce Orgs
==================================

CumulusCI's Project Keychain
----------------------------

The project keychain in CumulusCI allows you to store credentials to persistent (Production, Sandbox, Developer) orgs or to scratch orgs.  All files are stored under `~/.cumulusci/ProjectName` as AES encrypted files.

CumulusCI's Project Keychain is aware of your local repository and each repository configured for CumulusCI gets its own project keychain.  This means you can name your dev org for ProjectA `dev` and your dev org for ProjectB `dev` instead of `ProjectA_dev` and `ProjectB_dev`.  When you change directories between ProjectA and ProjectB's local git repositories, CumulusCI automatically switches your project keychain for you.  This allows you to keep your org names short, easy to read, and most important, easy to type.

Using Salesforce DX Scratch Orgs
--------------------------------

While it is possible to use `cci org connect <org_name>` to connect to a Developer Edition org, the real fun is using CumulusCI along with scratch orgs created using Salesforce DX.

If you haven't already set up Salesforce DX, you need to take care of a few steps:

1. `Install the Salesforce CLI <https://developer.salesforce.com/docs/atlas.en-us.sfdx_setup.meta/sfdx_setup/sfdx_setup_install_cli.htm>`_
2. `Enable Dev Hub in Your Org <https://developer.salesforce.com/docs/atlas.en-us.sfdx_setup.meta/sfdx_setup/sfdx_setup_enable_devhub.htm>`_
3. `Connect SFDX to Your Dev Hub Org <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_auth_web_flow.htm>`_ (be sure to use the ``--setdefaultdevhubusername`` option).

If you already have the `sfdx` command installed, have connected to your devhub, and have set the `defaultdevhubusername` config setting (use `sfdx force:config:list` to verify), you're ready to start using `cci` with `sfdx`. SFDX supports multiple DevHubs, so CumulusCI will use the one set as defaultdevhubusername when creating scratch orgs.

You can learn more about Salesforce DX at https://developer.salesforce.com/platform/dx.

CumulusCI wraps the creation of scratch orgs to provide some useful extra features:

* Each project starts with 4 scratch org configs meant for different phases of the development process: `beta`, `dev`, `feature`, `release`
* Scratch org configs for each project can be overridden in the project's cumulusci.yml
* New named scratch org configs can be added to projects for scratch configs unique to the project
* Scratch org configs can specify whether the org should be created with or without a namespace
* Scratch org configs persist in your keychain meaning you can easily spin up another instance of the same config if your org expires
* Scratch orgs are created automatically with an alias using the pattern 'ProjectName__orgname'
* Scratch orgs automatically get a password generated which is available via `cci org info <org_name>`

So, let's try that all out.  One important thing to note is that CumulusCI automatically creates all named scratch org configs in your project's keychain for you.  You can see this by running:

.. code-block:: console

    $ cci org list
    org        default  scratch  config_name  username
    ---------  -------  -------  -----------  ------------------------------------
    beta                *        beta
    dev                 *        dev
    feature             *        feature
    release             *        release

Although CumulusCI has those scratch org configs in its org list, no actual scratch orgs have been created yet.  The reason why is that scratch orgs in the CumulusCI keychain are really just a lazy configuration to create a scratch org.  An actual scratch org will be created when you try to do something against that org name (i.e. `dev`) for the first time.  If you run an action against a scratch org config that hasn't yet generated a scratch org, it will create the org and remember that it has now created the org:

.. code-block:: console

    $ cci org info dev
    2017-11-02 15:20:04: Creating scratch org with command sfdx force:org:create -f orgs/dev.json -n -a "CumulusCI Test__dev"
    2017-11-02 15:20:15: Successfully created scratch org: 00D..., username: test-...@cumulusci-test_dev_workspace.net
    2017-11-02 15:20:15: Generating scratch org user password with command sfdx force:user:password:generate -u test-...@cumulusci-test_dev_workspace.net
    2017-11-02 15:20:18: Getting scratch org info from Salesforce DX
    config_file: orgs/dev.json
    scratch: True
    namespaced: False
    config_name: dev
    sfdx_alias: CumulusCI Test__dev
    scratch_org_type: workspace
    org_id: 00D...
    username: test-atve4xqm8zji@cumulusci-test_dev_workspace.net
    created: True
    access_token: 00D...!.............
    password: Random Password Would be Here
    instance_url: https://inspiration-speed-3192-dev-ed.cs66.my.salesforce.com

Now, if we look at the org list, we can see a username for our scratch org.  That means `dev` now has a real scratch org connected to it:

.. code-block:: console

    $ cci org list
    org        default  scratch  config_name  username
    ---------  -------  -------  -----------  --------------------------------------------------
    beta                *        beta
    dev                 *        dev          test-...@cumulusci-test_dev_workspace.net
    feature             *        feature
    packaging                                 mrbelvedere@cumulusci-test.packaging
    release             *        release

The new scratch org persists under the same name to CumulusCI.  The next time you call it, the same org is reused instead of a new scratch org being created:

.. code-block:: console

    $ cci org info dev
    2017-11-02 15:24:25: Getting scratch org info from Salesforce DX
    config_file: orgs/dev.json
    scratch: True
    namespaced: False
    config_name: dev
    sfdx_alias: CumulusCI Test__dev
    scratch_org_type: workspace
    org_id: 00D****
    username: test-******@cumulusci-test_dev_workspace.net
    created: True
    access_token: 00D******
    password: Random Password Would Be Here
    instance_url: https://inspiration-speed-3192-dev-ed.cs66.my.salesforce.com

If you want to delete the scratch org, use `cci org scratch_delete <org_name>`:

.. code-block:: console

    $ cci org scratch_delete dev
    2017-11-02 15:26:13: Deleting scratch org with command sfdx force:org:delete -p -u test-...@cumulusci-test_dev_workspace.net
    2017-11-02 15:26:17: Successfully marked scratch org test-...@cumulusci-test_dev_workspace.net for deletion

If for some reason the whole scratch org config misbehaves, you can easily recreate it with `cci org scratch <config_name> <org_name>`:

.. code-block:: console

    $ cci org scratch dev dev

There may be times when you need to import an existing scratch org that wasn't created by CumulusCI. You can do so with `cci org import <username_or_alias> <org_name>`:

.. code-block:: console

    $ cci org import test-...@example.com dev
    2018-11-15 09:23:16: Getting scratch org info from Salesforce DX
    Imported scratch org: 00D...........0, username: test-...@example.com

You can hop into a browser logged into any org in your keychain with `cci org browser <org_name>`.

Creating a Connected App
------------------------

In order to connect persistent orgs such as a Developer Edition, Enterprise Edition, or Sandbox org to CumulusCI, you need to have a Connected App configured in a persistent Salesforce org.  You have a choice of whether to create the Connected App from the command line or in Salesforce Setup.

Create With CumulusCI
^^^^^^^^^^^^^^^^^^^^^

CumulusCI includes a task to easily deploy the Salesforce Connected App to any org in your sdfx keychain.  By default, this will deploy to the org configured as the defaultdevhubusername.

.. code-block:: console

    $ cci task run connected_app

This command will also configure CumulusCI's connected_app service in the keychain for you.  If you want to see the information for the connected app, you can view it with:

.. code-block:: console

    $ cci service info connected_app

Creating Manually
^^^^^^^^^^^^^^^^^

If you would rather create the Salesforce Connected App manually, use the following steps:

* In a Salesforce Org, go to Setup -> Create -> Apps
  * In Lightning, go to Setup -> Apps -> App Manager
* Click "New" under Connected Apps or in Lightning "New Connected App"

  * Enter a unique value for the Name and API Name field
  * Enter a Contact Email
  * Check "Enable OAuth Settings"
  * Set the Callback URL to http://localhost:8080/callback
  * Enable the scopes: full, refresh_token, and web
  * Save the Connected App

* Click the Manage button, then click Edit
* Record the client_id (Consumer Key) and the client_secret (Consumer Secret)

Configure the Connected App as a service:

.. code-block:: console

    $ cci service connect connected_app
    Callback url: <input>
    Client id: <input>
    Client secret: <input>
    connected_app is now configured for global use

Configuring the Connected App is a one time operation. Once configured, you can start connecting Salesforce Orgs to your project's keychain.


Connecting a Packaging Org
--------------------------

To really show the power of CumulusCI, we'll automate the entire process of releasing and testing a beta managed package.  We'll need to set up a packaging org.  The steps you'll need to do are:

* Create a new Developer Edition org
* Log into the org
* Go to Setup -> Packages and create an Unmanaged Package named whatever you want to call your package
* Assign a namespace to the org and point it at the Unmanaged Package you created

Once you have the org, connect it to `cci`'s project keychain with `cci org connect <org_name>`:

.. code-block:: console

    $ cci org connect packaging
    Launching web browser for URL https://login.salesforce.com/services/oauth2/authorize?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost:8080/callback&scope=web%20full%20refresh_token&prompt=login
    Spawning HTTP server at http://localhost:8080/callback with timeout of 300 seconds.
    If you are unable to log in to Salesforce you can press ctrl+c to kill the server and return to the command line.

This should open a browser on your computer pointed to the Salesforce login page. Log in and then grant access to the app. Note that since the login to capture credentials occurs in your normal browser, you can use browser password managers such as LastPass to log in. Once access is granted and you see a browser page that says `Congratulations` you can close the browser tab and return to the terminal. Your org is now connected via OAuth and CumulusCI never needs to know your actual user password. As an added benefit, OAuth authentication remains valid even after password changes.

You should now see the packaging org available in `cci org list`:

.. code-block:: console

    $ cci org list
    org        default  scratch  config_name  username
    ---------  -------  -------  -----------  ------------------------------------
    beta                *        beta
    dev                 *        dev
    feature             *        feature
    packaging                                 mrbelvedere@cumulusci-test.packaging
    release             *        release


Default Org
-----------

You can set a default org on your project which will then be used as the org for all tasks and flows.:

.. code-block:: console

    $ cci org default dev
    dev is now the default org

.. code-block:: console

    $ cci org list
    org        default  scratch  config_name  username
    ---------  -------  -------  -----------  ------------------------------------
    beta                *        beta
    dev        *        *        dev
    feature             *        feature
    packaging                                 mrbelvedere@cumulusci-test.packaging
    release             *        release


.. code-block:: console

    $ cci org default dev --unset
    dev is no longer the default org. No default org set.

.. code-block:: console

    $ cci org list
    org        default  scratch  config_name  username
    ---------  -------  -------  -----------  ------------------------------------
    beta                *        beta
    dev                 *        dev
    feature             *        feature
    packaging                                 mrbelvedere@cumulusci-test.packaging
    release             *        release

So we can start running some tasks, let's set dev as our default again:

.. code-block:: console

    $ cci org default dev

Part 4: Running Tasks
=====================

Once you have some orgs connected, you can start running tasks against them. First, you'll want to get a list of tasks available to run:

.. code-block:: console

    $ cci task list

    task                            description
    ------------------------------  -------------------------------------------------------------------------------------------------------
    create_package                  Creates a package in the target org with the default package name for the project
    create_managed_src              Modifies the src directory for managed deployment. Strips //cumulusci-managed from all Apex code
    create_unmanaged_ee_src         Modifies the src directory for unmanaged deployment to an EE org
    deploy                          Deploys the src directory of the repository to the org
    deploy_pre                      Deploys all metadata bundles under unpackaged/pre/
    deploy_post                     Deploys all metadata bundles under unpackaged/post/
    deploy_post_managed             Deploys all metadata bundles under unpackaged/post/
    get_installed_packages          Retrieves a list of the currently installed managed package namespaces and their versions
    github_clone_tag                Lists open pull requests in project Github repository
    github_master_to_feature        Merges the latest commit on the main branch into all open feature branches
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

You can view the details on an individual task:

.. code-block:: console

    $ cci task info update_package_xml

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

You can run a task:

.. code-block:: console

    $ cci task run update_package_xml

    2016-11-03 11:57:53: Generating src/package.xml from metadata in src

Task Options
------------

And you can run a task passing any of the options via the command line:

.. code-block:: console

    $ cci task run update_package_xml -o managed True -o output managed_package.xml

    INFO:UpdatePackageXml:Generating managed_package.xml from metadata in src

Running Tasks Against a Salesforce Org
--------------------------------------

The update_package_xml task works only on local files and does not require a connection to a Salesforce org. The deploy task uses the Metadata API to deploy the src directory to the target org and thus requires a Salesforce org. Since we already made dev our default org, we can still just run the task against our dev org by calling it without any options:

.. code-block:: console

    $ cci task info deploy

    Description: Deploys the src directory of the repository to the org
    Class: cumulusci.tasks.salesforce.Deploy

    Default Option Values
        path: src

    Option  Required  Description
    ------  --------  ----------------------------------------------
    path    *         The path to the metadata source to be deployed

    $ cci task run deploy

    2016-11-03 11:58:01: Pending
    2016-11-03 11:58:05: [InProgress]: Processing Type: CustomObject
    2016-11-03 11:58:06: [InProgress]: Processing Type: CustomObject
    2016-11-03 11:58:08: [InProgress]: Processing Type: QuickAction
    2016-11-03 11:58:09: [InProgress]: Processing Type: ApexClass
    2016-11-03 11:58:13: [Done]
    2016-11-03 11:58:14: [Success]: Succeeded

Now that the metadata is deployed, you can run the tests:

.. code-block:: console

    $ cci task info run_tests
    Description: Runs all apex tests
    Class: cumulusci.tasks.salesforce.RunApexTests

    Option             Required  Description
    -----------------  --------  ------------------------------------------------------------------------------------------------------
    test_name_exclude            Query to find Apex test classes to exclude ("%" is wildcard). Defaults to project__test__name_exclude
    managed                      If True, search for tests in the namespace only. Defaults to False
    test_name_match    *         Query to find Apex test classes to run ("%" is wildcard). Defaults to project__test__name_match
    poll_interval                Seconds to wait between polling for Apex test results. Defaults to 3
    namespace                    Salesforce project namespace. Defaults to project__package__namespace
    junit_output                 File name for JUnit output. Defaults to test_results.xml

    $ cci task run run_tests
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

Flows are simply named sequences of tasks. Flows are designed to be run against a single target org. CumulusCI comes with a number of best practice flows out of the box.:

.. code-block:: console

    $ cci flow list

    flow          description
    ------------  --------------------------------------------------------------------------------
    dev_org       Deploys the unmanaged package metadata and all dependencies to the target org
    ci_feature    Deploys the unmanaged package metadata and all dependencies to the target org
    ci_master     Deploys the managed package metadata and all dependencies to the packaging org
    ci_beta       Installs a beta version and runs tests
    ci_release    Installs a production release version and runs tests
    release_beta  Uploads and releases a beta version of the metadata currently in packaging
    unmanaged_ee  Deploys the unmanaged package metadata and all dependencies to the target EE org

Listing Flows' Tasks
--------------------
To see the list of tasks a flow will run, use the flow info command:

.. code-block:: console

    $ cci flow info dev_org
    description: Deploys the unmanaged package metadata and all dependencies to the target org
    tasks:
        0.5:
            task: unschedule_apex
        1:
            task: create_package
        2:
            task: update_dependencies
        3:
            task: deploy_pre
        4:
            task: deploy
        5:
            task: uninstall_packaged_incremental
        6:
            task: deploy_post
        7:
            task: update_admin_profile


Running a Flow
--------------

To set up our newly connected dev org, run the dev_org flow:

.. code-block:: console

    $ cci flow run dev_org

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
    2016-11-03 12:02:43:   path: unpackaged/post
    2016-11-03 12:02:43: Deploying all metadata bundles in path /Users/jlantz/dev/CumulusCI-Test/unpackaged/post
    2016-11-03 12:02:43: Deploying bundle: unpackaged/post/salesforce1
    2016-11-03 12:02:43: Pending
    2016-11-03 12:02:50: [Done]
    2016-11-03 12:02:51: [Success]: Succeeded

Part 6: Running Feature and Beta Builds
=======================================

Now that we have everything connected and working, let's try running the 3 core builds that make up our development build workflow at Salesforce.org:

Feature Test
------------

The `ci_feature` flow is meant to be run against the `feature` scratch org config.  It installs all dependencies, deploys the package metadata, and runs all apex tests.  You can run the same build that your CI system would run locally:

.. code-block:: console

   $ cci flow run ci_feature --org feature

Upload Beta
-----------

The `ci_master` flow deploys your package metadata to the packaging org.  The `release_beta` flow creates a Github Release along with automatically generated release notes created by parsing the Pull Request bodies of all PR's merged since the last production release.  You can run this locally with:

.. code-block:: console

   $ cci flow run ci_master --org packaging
   $ cci flow run release_beta --org packaging

Beta Test
---------

The `ci_beta` flow uses the Github API to determine the latest beta release for the project.  NOTE: This requires that you're using `release_beta` to create Github Releases:

.. code-block:: console

    $ cci flow run ci_beta --org beta

You can also pass the version number:

.. code-block:: console

    $ cci flow run ci_beta --org beta -o install_managed_beta__version "1.1 (Beta 12)"

Automate it with MetaCI
-----------------------

Once you have these flows set up, you can now use MetaCI to run these same builds against your project automatically on Heroku.  For more information, check out http://metaci-cli.readthedocs.io


Part 7: Digging Deeper
======================

Custom Tasks
------------

Create a local python tasks module:

.. code-block:: console

    $ mkdir tasks
    $ touch tasks/__init__.py

Create the file **tasks/salesforce.py** with the following content:

.. code-block:: python

    from cumulusci.tasks.salesforce import BaseSalesforceApiTask

    class ListContacts(BaseSalesforceApiTask):

        def _run_task(self):
            res = self.sf.query('Select Id, FirstName, LastName from Contact LIMIT 10')
            for contact in res['records']:
                self.logger.info('{Id}: {FirstName} {LastName}'.format(**contact))

    class ListApexClasses(BaseSalesforceApiTask):

        def _run_task(self):
            res = self.tooling.query('Select Id, Name, NamespacePrefix from ApexClass LIMIT 10')
            for apexclass in res['records']:
                self.logger.info('{Id}: [{NamespacePrefix}] {Name}'.format(**apexclass))

Finally, wire in your new tasks by editing the cumulusci.yml file in your repo and adding the following lines:

.. code-block:: yaml

    tasks:
        list_contacts:
            description: Prints out 10 Contacts from the target org using the Enterprise API
            class_path: tasks.salesforce.ListContacts
        list_apex_classes:
            description: Prints out 10 ApexClasses from the target org using the Tooling API
            class_path: tasks.salesforce.ListApexClasses

Now your new tasks are available in the task list:

.. code-block:: console

    $ cci task list
    task                            description
    ------------------------------  ---------------------------------------------------------------------------------
    create_package                  Creates a package in the target org with the default package name for the project
    ...
    list_contacts                   Prints out 10 Contacts from the target org using the Enterprise API
    list_apex_classes               Prints out 10 ApexClasses from the target org using the Tooling API

Run the tasks:

.. code-block:: console

    $ cci task run list_contacts

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

    $ cci task run list_apex_classes

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
