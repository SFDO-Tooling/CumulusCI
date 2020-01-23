========
Cookbook
========

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

    from cumulusci.core.tasks.salesforce import BaseSalesforceApiTask

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
    from cumulusci.tasks.salesforce import UpdateAdminProfile as BaseUpdateAdminProfile
    from cumulusci.utils import findReplace
    from cumulusci.utils import findReplaceRegex

    rt_visibility_template = """
    <recordTypeVisibilities>
        <default>{}</default>
        <personAccountDefault>true</personAccountDefault>
        <recordType>{}</recordType>
        <visible>true</visible>
    </recordTypeVisibilities>
    """

    class UpdateAdminProfile(BaseUpdateAdminProfile):

        def _process_metadata(self):
            super(UpdateAdminProfile, self)._process_metadata()

            # Strip record type visibilities
            findReplaceRegex(
                '<recordTypeVisibilities>([^\$]+)</recordTypeVisibilities>',
                '',
                os.path.join(self.tempdir, 'profiles'),
                'Admin.profile'
            )

            # Set record type visibilities
            self._set_record_type('Account.HH_Account', 'false')
            self._set_record_type('Account.Organization', 'true')
            self._set_record_type('Opportunity.NPSP_Default', 'true')

        def _set_record_type(self, name, default):
            rt = rt_visibility_template.format(default, name)
            findReplace(
                '<tabVisibilities>',
                '{}<tabVisibilities>'.format(rt),
                os.path.join(self.tempdir, 'profiles'),
                'Admin.profile',
                max=1,
            )

That's a lot of code, but it is pretty simple to explain:

* The standard UpdateAdminProfile class provides the `_process_metadata` method which modifies the retrieved Admin.profile before it is redeployed.  We want to add our logic after the standard logic does its thing.

* First, we strip out all `<recordTypeVisibilities>*</recordTypeVisibilities>` using the findReplaceRegex util method provided by CumulusCI

* Next, we set visibility on the 3 record types needed by the project and set the proper default record type values.

This then gets wired into the project's builds by the following in the cumulusci.yml::

    tasks:
        update_admin_profile:
            class_path: tasks.salesforce.UpdateAdminProfile
            options:
                package_xml: lib/admin_profile.xml

Note that here we're overriding the default package_xml used by UpdateAdminProfile.  The reason for this is taht we need to retrieve some managed objects that come from dependent packages so we can grant permissions on fields we added to those objects.  Here's the contents of `lib/admin_profile.xml`::

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
