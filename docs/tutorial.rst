========
Tutorial
========

Part 1: Installing CumulusCI
============================

Requirements
------------

* You must have Python version 2.7.x installed
* A local git repository containing Salesforce metadata in the `src/` subfolder or clone CumulusCI-Test for demo::

    git clone https://github.com/SalesforceFoundation/CumulusCI-Test

* Ensure you have virtualenv installed by either installing a package for your OS or installing with pip::

    pip install virtualenv


Using virtualenv
----------------

Run the following::

    virtualenv ~/cumulusci_venv
    source ~/cumulusci_venv/bin/activate

Once activated, you will see (venv) at the start of your shell prompt to let you know the virtualenv is active.  From this point, any Python packages you install will be installed only into the virtualenv and leave your system's Python alone.

If you want to always have the CumulusCI commands available, you can add the following line to your ~/.bash_profile::

    source ~/cumulusci_venv/bin/activate

More information about using virtualenv is available at: http://docs.python-guide.org/en/latest/dev/virtualenvs/


Installation
------------

With your virtualenv activated::

    pip install cumulusci

This will install the latest version of CumulusCI and all its dependencies into the virtualenv.  You can verify the installation by running:

    $ cumulusci2
    Usage: cumulusci2 [OPTIONS] COMMAND [ARGS]...
    
    Options:
    --help  Show this message and exit.
    
    Commands:
    flow     Commands for finding and running flows for a...
    org      Commands for connecting and interacting with...
    project  Commands for interacting with project...
    task     Commands for finding and running tasks for a... 


Project Initialization
----------------------

The `cumulusci2` command is git repository aware.  Changing directories from one local git repository to another will change the project context.  Each project context isolates the following:

* Connected App: The Salesforce Connected App to use for OAuth authentication
* Orgs: Connected Salesforce Orgs are stored in a project specific keychain
* Github Config (optional): The configuration info for scripts that interact with the Github API
* Mrbelvedere Config (optional): The configuration info for scripts that interact with the Mrbelvedere API
* ApexTestsDB Config (optional): The configuration info for scripts that interact with the ApexTestsDB

If you run the `cumulusci2` command from outside a git repository, it will generate an error::

    $ cd ~

    $ cumulusci2
    No repository found in current path.  You must be inside a repository to initialize the project configuration

If you run the `cumulusci2 org list` command from inside a git repository that has not yet been set up for CumulusCI, you can use the `cumulusci2 project init` command to initialize the configuration::

    $ cd path/to/your/repo

    $ cumulusci2 project info
    Usage: cumulusci2 project info [OPTIONS]
    Error: No project configuration found.  You can use the "project init" command to initilize the project for use with CumulusCI

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

Connecting Salesforce Orgs
--------------------------

First, you will need to create a Salesforce Connected App with the following steps:

* In a Salesforce Org, go to Setup -> Create -> Apps
* Click "New" under Connected Apps
* Enter a unique value for the Name and API Name field
* Enter a Contact Email
* Check "Enable OAuth Settings"
* Set the Callback URL to http://localhost:8080
* Enable the scopes: full, refresh_token, and web
* Save the Connected App
* Click the Manage button, then click Edit
* Go back to Setup -> Create -> Apps, and click on the app you created
* Record the client_id (Consumer Key) and the client_secret (Consumer Secret)

Configure the Connected App in your project's keychain

    $ cumulusci2 org configure_connected_app
    client_id:
    client_secret:
    
Configuring the Connected App is a one time operation per project.  Once configured, you can start connecting Salesforce Orgs to your project's keychain::

    $ cumulsci2 org connect dev

    $ cumulusci2 org list

    $ cumulusci2 org default dev

    $ cumulusci2 org list

    $ cumulusci2 org default dev --unset

    $ cumulusci2 org list

    $ cumulusci2 org default dev

Once you have some orgs connected, you can start running tasks against them::

    $ cumulusci2 task list
    create_unmanaged_package: Deploys an empty package with name from project -> name
    create_managed_src: Modifies the src directory for managed deployment.  Strips //cumulusci-managed from all Apex code
    create_unmanaged_ee_src: Modifies the src directory for unmanaged deployment to an EE org
    delete_incremental: Deletes any metadata from the package in the target org not in the local workspace
    delete_incremental_managed: Deletes any metadata from the package in the target packaging org not in the local workspace
    deploy: Deploys the src directory of the repository to the org
    deploy_pre: Deploys all metadata bundles under unpackaged/pre/
    deploy_post: Deploys all metadata bundles under unpackaged/post/
    generate_apex_doc: Generates ApexDoc documentation and uploads to the gh-pages branch
    get_installed_packages: Retrieves a list of the currently installed managed package namespaces and their versions
    github_clone_tag: Lists open pull requests in project Github repository
    github_master_to_feature: Merges the latest commit on the master branch into all open feature branches
    github_pull_requests: Lists open pull requests in project Github repository
    github_release: Creates a Github release for a given managed package version number
    github_release_notes: Generates release notes by parsing pull request bodies of merged pull requests between two tags
    push_all: Schedules a push upgrade of a package version to all subscribers
    push_qa: Schedules a push upgrade of a package version to all orgs listed in push/orgs_qa.txt
    push_sandbox: Schedules a push upgrade of a package version to all subscribers
    push_trial: Schedules a push upgrade of a package version to Trialforce Template orgs listed in push/orgs_trial.txt
    retrieve_packaged: Retrieves the packaged metadata from the org
    retrieve_packaged_ant: Retrieves the packaged metadata
    retrieve_src: Retrieves the packaged metadata into the src directory
    retrieve_unpackaged: Retrieves unpackaged metadata from the org
    revert_managed_src: Reverts the changes from create_managed_src
    revert_unmanaged_ee_src: Reverts the changes from create_unmanaged_ee_src
    run_tests: Runs all apex tests
    run_tests_managed: Runs all apex tests in the packaging org or a managed package subscriber org
    uninstall: Uninstalls the package metadata
    uninstall_unpackaged_pre: Uninstalls the unpackaged/pre bundles
    uninstall_unpackaged_post: Uninstalls the unpackaged/post bundles
    update_admin_profile: Retrieves, edits, and redeploys the Admin.profile with full FLS perms for all objects/fields
    update_meta_xml: Updates all -meta.xml files to have the correct API version and extension package versions
    update_package_xml: Updates src/package.xml with metadata in src/
    update_required_packages: Ensures all managed package versions in version.properties are installed
    upload_beta: Uploads a beta release of the metadata currently in the packaging org
    upload_production: Uploads a beta release of the metadata currently in the packaging org

    $ cumulusci2 task info update_package_xml

    $ cumulusci2 task run update_package_xml
      
    $ cumulusci2 task info deploy

    $ cumulusci2 task run deploy

    $ cumulusci2 task info run_tests

    $ cumulusci2 task run run_tests

    $ cumulusci2 flow list

    $ cumulusci2 flow run deploy_dev_org

    $ cumulusci2 project connect_github

    $ cumulusci2 project connect_apextestsdb

    $ cumulusci2 project connect_mrbelvedere
    



    $ cumulusci2 org connected_app
    $ cumulusci2 org info feature
    $ cumulusci2 org info packaging
    $ cumulusci2 org info beta
    $ export CUMULUSCI_KEYCHAIN_CLASS=cumulusci.core.keychain.EnvironmentProjectKeychain
    $ cumulusci2 org list
    $ export CUMULUSCI_CONNECTED_APP="{__COPIED_FROM_ABOVE__}"
    $ export CUMULUSCI_ORG_feature="{__COPIED_FROM_ABOVE__}"
    $ export CUMULUSCI_ORG_packaging="{__COPIED_FROM_ABOVE__}"
    $ export CUMULUSCI_ORG_beta="{__COPIED_FROM_ABOVE__}"
    $ cumulusci2 org list
    $ cumulusci2 task run --org feature deploy
