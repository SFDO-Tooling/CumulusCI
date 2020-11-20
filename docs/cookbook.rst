========
Cookbook
========

.. contents::
   :depth: 2

Custom Tasks via YAML
=====================

With just some simple changes in the cumulusci.yml file, you can override a lot of build functionality without ever touching any Python code.

Change directory for deploy task
--------------------------------

The global cumulusci.yml file that comes with cumulusci defines the `deploy` task with the following YAML::

    tasks:
        deploy:
            description: Deploys the src directory of the repository to the org
            class_path: cumulusci.tasks.salesforce.Deploy
            options:
                path: src

You can override the `path` option by adding the following to your project's cumulusci.yml file::

    tasks:
        deploy:
            options:
                path: some_other_dir

Custom Flows via YAML
=====================

The main cumulusci.yml file defines the `dev_org` flow using the following YAML.  We'll use the `dev_org` flow for the flow customization examples::

    flows:
        dev_org:
            description: Deploys the unmanaged package metadata and all dependencies to the target org
            steps:
                1:
                    flow: dependencies
                2:
                    flow: deploy_unmanaged
                3:
                    flow: deploy_pre
                4:
                    task: deploy
                5:
                    task: uninstall_packaged_incremental
                6:
                    task: deploy_post

Customize vs Create
-------------------

A key philosophy of the user experience for CumulusCI is to keep things consistent from project to project while allowing for project specific customizations.  For example, the included `dev_org` allows a developer to run a complete deployment to set up a development environment.  Rather than each project defining its own `dev_org_myproject` flow, it's a better user experience to just customize the `dev_org` flow for projects that need something different.  This way, a developer switching from Project Repo A to Project Repo B can run the same command, `cci flow run dev_org` in each project instead of having to know the custom flow names for each project.

Add a task to the dev_org flow
------------------------------

If you want to also run the `run_tests` at the end of the `dev_org` flow, you would add the following to your project's cumulusci.yml::

    flows:
        dev_org:
            steps:
                4:
                    task: run_tests

Skip a task in a flow
---------------------

If you never want to run the `uninstall_packaged_incremental` task, add the following to your project's cumulusci.yml::

    flows:
        deploy_unmanaged:
            tasks:
                4:
                    task: None

Rearrange two tasks in a flow
-----------------------------

If you wanted to run `deploy_pre` before `update_dependencies`, add the following to your project's cumulusci.yml::

    flows:
        dependencies:
            tasks:
                1:
                    task: deploy_pre
                2:
                    task: update_dependencies

Defining a new flow
-------------------

If you can't customize an out of the box flow or have a use case for which there is no out of the box flow, you can create your own project specific flows by adding the following structure to your cumulusci.yml::

    flows:
        my_custom_flow: # Name this whatever you want
            description: A custom flow for this project (put a better descriptions here please!)
            steps:
                1:
                    flow: dependencies
                3:
                    flow: deploy_unmanaged
                4:
                    task: update_admin_profile
                5:
                    task: run_tests


Custom tasks via Python
=======================

While the built in tasks are designed to be highly configurable via the cumulusci.yml and the task's options, sometimes an individual project needs to change the implementation of a task to meet its requirements.  This section shows a few examples custom tasks implemented in Python.

When the cci command runs, it adds your current repo's root to the python path.  This means you can write your python customizations to CumulusCI and store them in your project's repo along with your code.

All of the following examples assume that you've created a tasks module in your repo::

    mkdir tasks
    touch tasks/__init__.py

Quick background about CumulusCI tasks
--------------------------------------

All tasks in CumulusCI are python classes that subclass `cumulusci.core.tasks.BaseTask`.  The general usage of a task is two step: initialize an instance then call it to run the task.

For most tasks, you'll want to override the `_run_task` method in your subclass to provide the implementation. The return value of this function is saved as part of the StepResult. Exceptions from `cumulusci.core.exceptions` should be raised to communicate task status to the user or flow. If no exceptions are thrown, the task is considered to have completed successfully.

Task Exceptions
---------------

If the task has an error that should be considered a build failure (e.g. a metadata deployment failure, test failure, etc) it can raise the exception `cumulusci.core.exceptions.CumulusCIFailure`. If you want to flag a usage error (e.g. the task receives an invalid set of options) it should raise the exception `cumulusci.core.exceptions.CumulusCIUsageError`.

Query the Enterprise API for Data
---------------------------------

CumulusCI provides a number of base task classes that are useful for building completely custom tasks.  For this example, we'll use the `BaseSalesforceApiTask` which initializes the `simple-salesforce` python library for interacting with the Salesforce REST API.  `BaseSalesforceApiTask` sets `self.sf` to an initialized instance with the access token already set so you just focus on writing your API interaction logic.

Create the file `tasks/rest.py`::

    from cumulusci.tasks.salesforce import BaseSalesforceApiTask

    class ListContacts(BaseSalesforceApiTask):
        def _run_task(self):
            res = self.sf.query('Select Id, FirstName, LastName from Contact LIMIT 10')
            for contact in res['records']:
                self.logger.info('{Id}: {FirstName} {LastName}'.format(**contact))

To wire this task up to CumulusCI, add the following in your project's cumulusci.yml::

    tasks:
        list_contacts:
            description: Prints 10 Contacts
            class_path: tasks.rest.ListContacts

Verify that the task shows up::

    cci task list
    cci task info list_contacts


Query the Tooling API
---------------------

In this example, we'll use another API exposed by the `BaseSalesforceApiTask`, the Tooling API! The base task class initializes a wrapper to the enterprise api (`self.sf`), to the bulk api (`self.bulk`), and to the tooling api (`self.tooling`). With a modified `simple-salesforce` instance pointing to the tooling API, we can query for Apex Classes in our org.

Create the file `tasks/tooling.py`::

    from cumulusci.tasks.salesforce import BaseSalesforceApiTask

    class ListApexClasses(BaseSalesforceApiTask):
        def _run_task(self):
            res = self.tooling.query('Select Id, Name, NamespacePrefix from ApexClass LIMIT 10')
            for apexclass in res['records']:
                self.logger.info('{Id}: [{NamespacePrefix}] {Name}'.format(**apexclass))

To wire this task up to CumulusCI, add the following in your project's cumulusci.yml::

    tasks:
        list_classes:
            description: Prints 10 Apex Classes
            class_path: tasks.tooling.ListClasses

Verify that the task shows up::

    cci task list
    cci task info list_classes

Extend the default update_admin_profile task
--------------------------------------------

The previous examples showed how to add a completely new task, but what if we need to implement some custom project specific logic into an existing task?  For this example, we'll take a look at how the Salesforce.org Nonprofit Success Pack modifies the `update_admin_profile` task to grant FLS on custom fields added to a managed object and set the visibility and default values for project specific record types.

The following is the content of the `tasks/salesforce.py` file in the NPSP repository::

    import os
    from cumulusci.tasks.salesforce import UpdateProfile as BaseUpdateProfile
    from cumulusci.utils import find_replace
    from cumulusci.utils import find_replace_regex

    rt_visibility_template = """
    <recordTypeVisibilities>
        <default>{}</default>
        <personAccountDefault>true</personAccountDefault>
        <recordType>{}</recordType>
        <visible>true</visible>
    </recordTypeVisibilities>
    """

    class UpdateProfile(BaseUpdateProfile):

        def _process_metadata(self):
            super(UpdateProfile, self)._process_metadata()

            # Strip record type visibilities
            find_replace_regex(
                '<recordTypeVisibilities>([^\$]+)</recordTypeVisibilities>',
                '',
                os.path.join(self.retrieve_dir, 'profiles'),
                'Admin.profile'
            )

            # Set record type visibilities
            self._set_record_type('Account.HH_Account', 'false')
            self._set_record_type('Account.Organization', 'true')
            self._set_record_type('Opportunity.NPSP_Default', 'true')

        def _set_record_type(self, name, default):
            rt = rt_visibility_template.format(default, name)
            find_replace(
                '<tabVisibilities>',
                '{}<tabVisibilities>'.format(rt),
                os.path.join(self.retrieve_dir, 'profiles'),
                'Admin.profile',
                max=1,
            )

That's a lot of code, but it is pretty simple to explain:

* The standard UpdateProfile class provides the `_process_metadata` method which modifies the retrieved Admin.profile before it is redeployed.  We want to add our logic after the standard logic does its thing.

* First, we strip out all `<recordTypeVisibilities>*</recordTypeVisibilities>` using the find_replace_regex util method provided by CumulusCI

* Next, we set visibility on the 3 record types needed by the project and set the proper default record type values.

This then gets wired into the project's builds by the following in the cumulusci.yml::

    tasks:
        update_admin_profile:
            class_path: tasks.salesforce.UpdateProfile
            options:
                package_xml: lib/admin_profile.xml

Note that here we're overriding the default package_xml used by UpdateProfile.  The reason for this is taht we need to retrieve some managed objects that come from dependent packages so we can grant permissions on fields we added to those objects.  Here's the contents of `lib/admin_profile.xml`::

    <?xml version="1.0" encoding="UTF-8"?>
    <Package xmlns="http://soap.sforce.com/2006/04/metadata">
        <types>
            <members>*</members>
            <members>Account</members>
            <members>Campaign</members>
            <members>Contact</members>
            <members>Lead</members>
            <members>Opportunity</members>
            <members>npe01__OppPayment__c</members>
            <members>npo02__Household__c</members>
            <members>npo02__Opportunity_Rollup_Error__c</members>
            <members>npe03__Custom_Field_Mapping__c</members>
            <members>npe03__Recurring_Donation__c</members>
            <members>npe4__Relationship__c</members>
            <members>npe4__Relationship_Auto_Create__c</members>
            <members>npe4__Relationship_Error__c</members>
            <members>npe4__Relationship_Lookup__c</members>
            <members>npe5__Affiliation__c</members>
            <name>CustomObject</name>
        </types>
        <types>
            <members>Admin</members>
            <name>Profile</name>
        </types>
        <version>36.0</version>
    </Package>


Continuous Integration with CumulusCI and GitHub Actions
========================================================

The “CI” in CumulusCI stands for “continuous integration.” Continuous
integration is the practice of automatically running a project’s tests
for any change before that change is merged to the main branch. This
helps keep the main branch in a state where it can be released at any
time, because the repository can be configured to protect the main
branch so that changes can only be merged if the tests have passed.

CumulusCI flows can be run on your own computer, or they can be run in a
CI system such as GitHub Actions, CircleCI, or Azure Pipelines. This
recipe will show how to use GitHub Actions to run Apex tests in a
scratch org after every commit. (For other CI systems the steps should
be similar, though the details of the configuration will be different.)

.. note::
   The Salesforce.org release engineering team, which built CumulusCI, also maintains a CI system
   called `MetaCI <https://github.com/SFDO-Tooling/MetaCI>`_. MetaCI is an open source app built
   to run on Heroku, and is designed specifically to work with CumulusCI and Salesforce. However,
   MetaCI is a bit complicated to set up and operate, so this recipe aims to provide
   a simpler alternative that can work fine in many cases.

In order to follow along, you should already have a repository that is
hosted on GitHub and configured as a CumulusCI project. In other words,
we’re assuming your project already has a ``cumulusci.yml`` and that you are
successfully running CumulusCI flows locally.

.. note::
   GitHub Actions is free for open source (public) repositories.
   Check with GitHub about pricing for private repositories.

Create a GitHub Action workflow
-------------------------------

In GitHub Actions, you can define *workflows* which run automatically in
response to events in the repository. We’re going to create an action
called ``Apex Tests`` which runs whenever commits are pushed to GitHub.

Workflows are defined using files in YAML format in the
``.github/workflows`` folder within the repository. To set up the Apex
Tests workflow, use your editor to create a file named
``apex_tests.yml`` in this folder and add the following contents:

.. code-block:: yaml

   name: Apex Tests

   on: [push]

   env:
     CUMULUSCI_KEYCHAIN_CLASS: cumulusci.core.keychain.EnvironmentProjectKeychain
     CUMULUSCI_SERVICE_github: ${{ secrets.CUMULUSCI_SERVICE_github }}

   jobs:
     unit_tests:
       name: "Run Apex tests"
       runs-on: ubuntu-latest
       steps:
       - uses: actions/checkout@v2
       - name: Install sfdx
         run: |
           mkdir sfdx
           wget -qO- https://developer.salesforce.com/media/salesforce-cli/sfdx-linux-amd64.tar.xz | tar xJ -C sfdx --strip-components 1
           ./sfdx/install
           echo ${{ secrets.SFDX_AUTH_URL }} > sfdx_auth
           sfdx force:auth:sfdxurl:store -f sfdx_auth -d
       - name: Set up Python
         uses: actions/setup-python@v1
         with:
           python-version: "3.8"
       - name: Install CumulusCI
         run: |
           python -m pip install -U pip
           pip install cumulusci
       - run: |
           cci flow run ci_feature --org dev --delete-org

This workflow defines a *job* named ``Run Apex Tests`` which will run
these steps in the CI environment after any commits are pushed:

-  Check out the repository at the commit that was pushed
-  Install the Salesforce CLI and authorize a Dev Hub user
-  Install Python 3.8 and CumulusCI
-  Run the ``ci_feature`` flow in CumulusCI in the ``dev`` scratch org,
   and then delete the org. The ``ci_feature`` flow deploys the package
   and then runs its Apex tests.

It also configures CumulusCI to use a special keychain, the
``EnvironmentProjectKeychain``, which will load org and service
configuration from environment variables instead of from files.

Configure secrets
-----------------

You may have noticed that the workflow refers to a couple of “secrets,”
``CUMULUSCI_SERVICE_github`` and ``SFDX_AUTH_URL``. You need to add
these secrets to the repository settings before you can use this
workflow.

To find the settings for Secrets, open your repository in GitHub. Click
the Settings tab. Then click the Secrets link on the left.

``CUMULUSCI_SERVICE_github``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CumulusCI may need access to the GitHub API in order to do things like
look up information about dependency packages. To set this up, we’ll set
a secret to configure the CumulusCI github service.

First, follow GitHub’s instructions to `create a Personal Access Token
<https://help.github.com/en/github/authenticating-to-github/creating-a-personal-access-token-for-the-command-line>`_.

Now, in your repository’s Secrets settings, click the “Add a new secret”
link. Enter ``CUMULUSCI_SERVICE_github`` as the Name of the secret. For
the Value, enter the following JSON:

.. code-block:: json

   {"username": "USERNAME", "token": "TOKEN", "email": "EMAIL"}

But replace ``USERNAME`` with your github username, ``TOKEN`` with the Personal
Access Token you just created, and ``EMAIL`` with your email address.
Finally, click the “Add secret” button to save the secret.

``SFDX_AUTH_URL``
~~~~~~~~~~~~~~~~~

CumulusCI needs to be able to access a Salesforce org with the Dev Hub
feature enabled in order to create scratch orgs. The easiest way to do
this is to set up this connection locally, then copy its sfdx auth URL
to a secret on GitHub.

Since you already have CumulusCI working locally, you should be able to
run ``sfdx force:org:list`` to identify the username that is configured
as the default Dev Hub username — it is marked with ``(D)``.

Now run ``sfdx force:org:display --verbose -u [username]``, replacing
``[username]`` with your Dev Hub username. Look for the ``Sfdx Auth Url``
and copy it.

.. warning::
   *Important: Treat this URL like a password. It provides access to log in
   as this user!*

Now in your repository’s Secrets settings, click the “Add a new secret”
link. Enter ``SFDX_AUTH_URL`` as the Name of the secret, and the URL from
above as the Value. Click the “Add secret” button to save the secret.

.. note::
   Advanced note: These instructions connect sfdx to your Dev Hub using
   the standard Salesforce CLI connected app and a refresh token. It is
   also possible to authenticate sfdx using the force:auth:jwt:grant
   command with a custom connected app client id and private key.

Your Secrets should look like this:

.. image:: images/github_secrets.png
   :alt: Screenshot showing the CUMULUSCI_SERVICE_github and SFDX_AUTH_URL secrets

Test the workflow
-----------------

Now you should be able to try out the workflow. Commit the new
``.github/workflows/apex_tests.yml`` file to the repository and push the
commit to GitHub. You should be able to watch the status of this
workflow in the repository’s Actions tab:

.. image:: images/github_workflow.png
   :alt: Screenshot showing a running Github Action workflow

If you open a pull request for a branch that includes the workflow, you
will find a section at the bottom of the pull request that shows the
results of the checks that were performed by the workflow:

.. image:: images/github_checks.png
   :alt: Screenshot showing a successful check on a GitHub pull request

It is possible to configure
the repository’s main branch as a *protected branch* so that changes
can only be merged to it if these checks are passing.

See GitHub’s documentation for instructions to `configure protected
branches <https://help.github.com/en/github/administering-a-repository/configuring-protected-branches>`_
and `enable required status
checks <https://help.github.com/en/github/administering-a-repository/enabling-required-status-checks>`_.

Run headless browser tests
--------------------------

It is possible to run Robot Framework tests that control a real browser
as long as the CI environment has the necessary software installed. For
Chrome, it must have Chrome and chromedriver. For Firefox, it must have
Firefox and geckodriver.

Fortunately GitHub Actions comes preconfigured with an image that
includes these browsers. However it is necessary to run the browser in
headless mode. When using CumulusCI’s ``robot`` task, this can be done
by passing the ``-o vars BROWSER:headlesschrome`` option.

Here is a complete workflow to run Robot Framework tests for any commit:

.. code-block:: yaml

   name: Robot Tests

   on: [push]

   env:
     CUMULUSCI_KEYCHAIN_CLASS: cumulusci.core.keychain.EnvironmentProjectKeychain
     CUMULUSCI_SERVICE_github: ${{ secrets.CUMULUSCI_SERVICE_github }}

   jobs:
     unit_tests:
       name: "Run Robot Framework tests"
       runs-on: ubuntu-latest
       steps:
       - uses: actions/checkout@v2
       - name: Install sfdx
         run: |
           mkdir sfdx
           wget -qO- https://developer.salesforce.com/media/salesforce-cli/sfdx-linux-amd64.tar.xz | tar xJ -C sfdx --strip-components 1
           ./sfdx/install
           echo ${{ secrets.SFDX_AUTH_URL }} > sfdx_auth
           sfdx force:auth:sfdxurl:store -f sfdx_auth -d
       - name: Set up Python
         uses: actions/setup-python@v1
         with:
           python-version: "3.8"
       - name: Install CumulusCI
         run: |
           python -m pip install -U pip
           pip install cumulusci
       - run: |
           cci task run robot --org dev -o vars BROWSER:headlesschrome
       - name: Store robot results
         uses: actions/upload-artifact@v1
         with:
           name: robot
           path: robot/CumulusCI-Test/results
       - name: Delete scratch org
         if: always()
         run: |
           cci org scratch_delete dev

References
~~~~~~~~~~

- `GitHub Actions documentation <https://help.github.com/en/actions>`_

Large Volume Data Synthesis with Snowfakery
===========================================

It is possible to use CumulusCI to generate arbitrary amounts of
synthetic data using the ``generate_and_load_from_yaml`` 
`task <https://cumulusci.readthedocs.io/en/latest/tasks.html#generate-and-load-from-yaml>`_. That
task is built on the `Snowfakery language
<https://snowfakery.readthedocs.io/en/docs/>`_. CumulusCI ships
with Snowfakery embedded, so you do not need to install it.

To start, you will need a Snowfakery recipe. You can learn about
writing them in the `Snowfakery docs
<https://snowfakery.readthedocs.io/en/docs/>`_.

Once you have it, you can fill an org with data like this:


``$ cci task run generate_and_load_from_yaml -o generator_yaml
datasets/some_snowfakery_yaml -o num_records 1000 -o num_records_tablename
Account —org dev``

``generator_yaml`` is a reference to your Snowkfakery recipe.

``num_records_tablename`` says what record type will control how
many records are created.

``num_records`` says how many of that record type ("Account" in
this case) to make.

Generated Record Counts
-----------------------

The counting works like this:

  * Snowfakery always executes a *complete* recipe. It never stops halfway through.
  
  * At the end of executing a recipe, it checks whether it has
    created enough of the object type defined by ``num_records_tablename``
  
  * If so, it finishes. If not, it runs the recipe again.

So if your recipe creates 10 Accounts, 5 Contacts and 15 Opportunities,
then when you run the command above it will run the recipe
100 times (100*10=1000) which will generate 1000 Accounts, 500 Contacts
and 1500 Opportunites.

Batch Sizes
-----------

You can also control batch sizes with the ``-o batch_size BATCHSIZE``
parameter. This is not the Salesforce bulk API batch size. No matter
what batch size you select, CumulusCI will properly split your data
into batches for the bulk API.

You need to understand the loading process to understand why you
might want to set the ``batch_size``.

If you haven't set the ``batch_size`` then Snowfakery generates all
of the records for your load job at once.

So the first reason why you might want to set the batch_size is
because you don't have enough local disk space for the number of
records you are generating (across all tables).

This isn't usually a problem though.

The more common problem arises from the fact that Salesforce bulk
uploads are always done in batches of records a particular SObject.
So in the case above, it would upload 1000 Accounts, then 500
Contacts, then 1500 Opportunites. (remember that our scenario
involves a recipe that generates 10 Accounts, 5 Contacts and 15
Opportunites).

Imagine if the numbers were more like 1M, 500K and 1.5M. And further,
imagine if your network crashed after 1M Accounts and 499K Contacts 
were uploaded. You would not have a single "complete set" of 10/5/15.
Instead you would have 1M "partial sets".

If, by contrast, you had set your batch size to 100_000, your network
might die more around the 250,000 Account mark, but you would have
200,000/20 [#]_ =10K *complete sets*  plus some "extra" Accounts 
which you might ignore or delete. You can restart your load with a 
smaller goal (800K Accounts) and finish the job.

.. [#] remember that our sets have 20 Accounts each

Another reason you might choose smaller batch sizes is to minimize
the risk of row locking errors when you have triggers enabled.
Turning off triggers is generally preferable, and CumulusCI `has a
task
<https://cumulusci.readthedocs.io/en/latest/tasks.html#disable-tdtm-trigger-handlers>`_
for doing for TDTM trigger handlers, but sometimes you cannot avoid
them. Using smaller batch sizes may be preferable to switching to
serial mode. If every SObject in a batch uploads less than 10,000
rows then you are defacto in serial mode (because only one "bulk mode
batch" at a time is being processed).

In general, bigger batch sizes achieve higher throughput. No batching
at all is the fastest.

Smaller batch sizes reduce the risk of something going wrong. You
may need to experiment to find the best batch size for your use
case.
