# CumulusCI

CumulusCI is a command line tool belt and set of reusable Python classes useful in the development and release process of building a Salesforce Managed Package application.

# Key Features

* Out of the box, CumulusCI provides a complete best practice development and release process based on the processes used by Salesforce.org to build and release managed packages to thousands of users
* Flexible and pluggable system for running tasks (single actions) and flows (sequences of tasks)
* OAuth based org keychain allowing easy connection to Salesforce orgs and stored in local files using AES encryption

# Quick Start

This section provide a brief example of the commands you'd use to start a new project once you have CumulusCI installed

    $ cd <Your_Local_Repo>
    $ cumulusci2 project init
        project_name: MyProject
    $ cat cumulusci.yml
        project:
            name: MyProject
    $ cumulusci2 org config_connected_app
        client_id: 12345890
        client_secret:
    $ cumulusci2 org connect dev
        *** Opens a browser at the Salesforce login prompt to complete OAuth grant
    $ cumulusci2 org list
        dev
    $ cumulusci2 org info dev
        *** Displays the OAuth configuration info for the org named "dev"
    $ cumulusci2 org browser dev
        *** Opens a browser tab to the org using OAuth to bypass login
    $ cumulusci2 org connect --sandbox test
        *** Opens a browser at the Salesforce login prompt to complete OAuth grant
    $ cumulusci2 org list
        dev
        test
    $ cumulusci2 task list
        *** List all available tasks
        deploy: Deploys the src directory to the target Salesforce org
    $ cumulusci2 task run --org dev deploy
        *** Runs the "deploy" task against the "dev" org
    $ cumulusci2 flow list
        *** List all available flows
        dev_org: Runs a complete deployment against a dev org including dependencies but not running tests
    $ cumulusci2 flow run --org test dev_org
        *** Runs the "dev_org" flow against the "test" org
    
# Installation

Eventually, binary distributions of will be available to download for easier installation.  In the meantime, you can use the following process to get CumulusCI installed on your system.

## Setting up your local environment
The cumulusci command is written in Python and is designed to run in a Python virtualenv.  If you don't know what that is, no problem.  Follow the steps below to set up a virtualenv so you can run the cumulusci command yourself.

### Check out CumulusCI

First, you'll need to clone a copy of CumulusCI.  Go to wherever you keep development workspaces on your computer.

    git clone git@github.com:SalesforceFoundation/CumulusCI
    cd CumulusCI
    export CUMULUSCI_PATH=`pwd`

### Installing virtualenv on OS X

The easiest way to get virtualenv on OS X is using Homebrew.  The instructions below assume you already have the brew command

    brew install python

Then, continue along...

### Installing virtualenv

If you don't have the virtualenv command available, you can install it with pip:

    pip install virtualenv

### Creating your virtualenv (venv)

The virtualenv command allows you to build isolate python virtual environments in subfolders which you can easily activate and deactivate from the command line.  This keeps your modules isolated from your system's python and is generally a good idea.  It's also really easy.

    virtualenv venv
    source venv/bin/activate
    which python
        PATH_TO_YOUR_VENV/bin/python
    which pip
        PATH_TO_YOUR_VENV/bin/pip
    
At this point, your virtualenv is activated.  Your shell PATH points to python and pip (Python's package installer) inside your virtualenv.  Anything you install is isolated there.

## Installing the cumulusci2 command and dependencies

To initialize the cumulusci2 command, you need to run the following once inside your virtualenv:

    pip install -r requirements.txt

When the installation completes, you should be able to run the cumulusci2 command

    cumulusci2
        Usage: cumulusci2 [OPTIONS] COMMAND [ARGS]...
        
        Options:
          --help  Show this message and exit.

        Commands:
          flow     Commands for finding and running flows for a...
          org      Commands for connecting and interacting with...
          project  Commands for interacting with project...
          task     Commands for finding and running tasks for a...
        

As long as your virtualenv is activated, you can go into any repository configured for CumulusCI and use the cumulusci2 command to perform actions against it.

### Exiting and re-entering your virtualenv

If you start a new terminal session, you will need to initialize your virtualenv.

    cd PATH/TO/CumulusCI
    source venv/bin/activate

To leave your virtualenv

    deactivate

If you want to always have the cumulusci command available, you can add the following lines to your .bash_profile (or similar)

    export CUMULUSCI_PATH=PATH/TO/CumulusCI
    source $CUMULUSCI_PATH/venv/bin/activate
