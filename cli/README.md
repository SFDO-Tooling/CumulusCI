# cumulusci: The command line interface to CumulusCI

# Setting up your local environment
The cumulusci command is written in Python and is designed to run in a Python virtualenv.  If you don't know what that is, no problem.  Follow the steps below to set up a virtualenv so you can run the cumulusci command yourself.

## Check out CumulusCI

First, you'll need to clone a copy of CumulusCI.  Go to wherever you keep development workspaces on your computer.

    git clone git@github.com:SalesforceFoundation/CumulusCI
    cd CumulusCI
    export CUMULUSCI_PATH=`pwd`

## Installing virtualenv on OS X

The easiest way to get virtualenv on OS X is using Homebrew.  The instructions below assume you already have the brew command

    brew install python

Then, continue along...

## Installing virtualenv

If you don't have the virtualenv command available, you can install it with pip:

    pip install virtualenv

## Creating your virtualenv (venv)

The virtualenv command allows you to build isolate python virtual environments in subfolders which you can easily activate and deactivate from the command line.  This keeps your modules isolated from your system's python and is generally a good idea.  It's also really easy.

    virtualenv venv
    source venv/bin/activate
    which python
        PATH_TO_YOUR_VENV/bin/python
    which pip
        PATH_TO_YOUR_VENV/bin/pip
    
At this point, your virtualenv is activated.  Your shell PATH points to python and pip (Python's package installer) inside your virtualenv.  Anything you install is isolated there.

## Installing the cumulusci command and dependencies

To initialize the cumulusci command, you need to run the following once inside your virtualenv:

    pip install -r requirements.txt

When the installation completes, you should be able to run the cumulusci command

    cumulusci
        Usage: cumulusci [OPTIONS] COMMAND [ARGS]...
        
        Options:
        --help  Show this message and exit.

        Commands:
        apextestsdb_upload  Upload a test_results.json file to the...
        ci                  Commands to make building on CI servers...
        github              Commands for interacting with the Github...
        managed_deploy      Installs a managed package version and...
        mrbelvedere         Commands for integrating builds with...
        package_beta        Use Selenium to upload a package version in...
        package_deploy      Runs a full deployment of the code as managed...
        run_tests           Run Apex tests in the target org via the...
        unmanaged_deploy    Runs a full deployment of the code including...
        update_package_xml  Updates the src/package.xml file by parsing...

As long as your virtualenv is activated, you can go into any repository configured for CumulusCI and use the cumulusci command to perform actions against it.

## Exiting and re-entering your virtualenv

If you start a new terminal session, you will need to initialize your virtualenv.

    cd PATH/TO/CumulusCI
    source venv/bin/activate

To leave your virtualenv

    deactivate

If you want to always have the cumulusci command available, you can add the following lines to your .bash_profile (or similar)

    export CUMULUSCI_PATH=PATH/TO/CumulusCI
    source $CUMULUSCI_PATH/venv/bin/activate

# Environment Variables

Most commands in cumulusci require credentials to external systems.  All credentials in the cumulusci command are passed via environment variables to avoid them ever being stored insecurely in files.

## Salesforce Org Credentials

* SF_USERNAME
* SF_PASSWORD: Append security token to password if needed
* SF_SERVERURL: (optional) Override the default login url: https://login.salesforce.com

## Packaging Org OAuth Credentials

For more information on how to get these values, see https://cumulusci-oauth-tool.herokuapp.com

* OAUTH_CLIENT_ID
* OAUTH_CLIENT_SECRET
* OAUTH_CALLBACK_URL
* REFRESH_TOKEN
* INSTANCE_URL

## Github

* GITHUB_ORG_NAME
* GITHUB_REPO_NAME
* GITHUB_USERNAME
* GITHUB_PASSWORD: Usage of an application token is recommended instead of passwords

## Custom Branch and Tag Naming

CumulusCI defaults to the branch and tag prefixes shown below.  If you're using these, you don't need to configure anything:

* Master Branch: master
* Beta Release Tag: beta/
* Production Release Tag: release/

You can override any of these values with the following environment variables:

* MASTER_BRANCH
* PREFIX_BETA
* PREFIX_RELEASE
