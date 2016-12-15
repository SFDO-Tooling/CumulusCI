===============================
CumulusCI
===============================

.. image:: https://img.shields.io/pypi/v/cumulusci.svg
           :target: https://pypi.python.org/pypi/cumulusci
.. image:: https://readthedocs.org/projects/cumulusci/badge/?version=latest
           :target: https://cumulusci.readthedocs.io/en/latest/?badge=latest
           :alt: Documentation Status
.. image:: https://pyup.io/repos/github/SalesforceFoundation/CumulusCI/shield.svg
           :target: https://pyup.io/repos/github/SalesforceFoundation/CumulusCI/
           :alt: Updates

CumulusCI is a command line tool belt and set of reusable Python classes useful in the development and release process of building a Salesforce Managed Package application.

Key Features
------------

* Out of the box, CumulusCI provides a complete best practice development and release process based on the processes used by Salesforce.org to build and release managed packages to thousands of users
* Flexible and pluggable system for running tasks (single actions) and flows (sequences of tasks)
* OAuth based org keychain allowing easy connection to Salesforce orgs and stored in local files using AES encryption

Requirements
------------

* Python 2.7.x
* stdbuf - for passing through stdout from Ant
* Ant - for using some task commands

Installation
------------

* pip install cumulusci

Quick Start
-----------

This section provide a brief example of the commands you'd use to start a new project once you have CumulusCI installed::

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
        deploy_dev_org: Runs a complete deployment against a dev org including dependencies but not running tests
    $ cumulusci2 flow run --org test deploy_dev_org
        *** Runs the "dev_org" flow against the "test" org
