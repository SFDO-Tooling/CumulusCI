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

Swap out an Ant target for a task
---------------------------------
If we wanted to replace the following task with an ant target in our project::

    tasks:
        create_package:
            description: Creates a package in the target org with the default package name for the project
            class_path: cumulusci.tasks.salesforce.CreatePackage
            options:
                path: src

Swap out the create_package test to use an Ant target instead by adding the following to your project's cumulusci.yml::

    tasks:
        create_package:
            class_path: cumulusci.tasks.ant.AntTask
            options:
                target: createUnmanagedPackage

Now any flow in your project that calls the `create_package` task will run your `createUnmanagedPackage` Ant target instead.

Defining a new flow
-------------------

If the out of the box flows provided by CumulusCI don't work for your project, you can define your own flows easily in your project's cumulusci.yml by adding the following::

    flows:
        my_custom_flow:
            description: A custom flow for this project (put a better descriptions here please!)
            tasks:
                - deploy_pre
                - update_dependencies
                - deploy
                - update_admin_profile
                - run_tests

Add a task to an existing flow
------------------------------

Currently, the hierarchical merge that combines the global and project cumulusci.yml files does not allow you to modify the tasks in a flow.  However, you can append a task onto the end of the current flow.  Here is the standard definition of the `dev_org` flow::

    flows:
        dev_org:
            description: Deploys the unmanaged package metadata and all dependencies to the target org
            tasks:
                - task: create_package
                - task: update_dependencies
                - task: deploy_pre
                - task: deploy
                - task: uninstall_packaged_incremental
                - task: deploy_post

If you want to also run the `update_admin_profile` task at the end of the `dev_org` flow for your project, add the following to your cumulusci.yml::

    flows:
        dev_org:
            tasks:
                - task: update_admin_profile

Custom tasks via Python
=======================

While the built in tasks are designed to be highly configurable via the cumulusci.yml and the task's options, sometimes an individual project needs to change the implementation of a task to meet its requirements.  This section shows a few examples custom tasks implemented in Python.

When the cumulusci2 command runs, it adds your current repo's root to the python path.  This means you can write your python customizations to CumulusCI and store them in your project's repo along with your code.

All of the following examples assume that you've created a tasks module in your repo::
 
    mkdir tasks
    touch tasks/__init__.py

Quick background about CumulusCI tasks
--------------------------------------

All tasks in CumulusCI are python classes that subclass `cumulusci.core.tasks.BaseTask`.  The general usage of a task is two step: initialize an instance then call it to run the task.

For most tasks, you'll want to override the `_run_task` method in your subclass to provide implementation.

Query the Enterprise API for Data
---------------------------------

CumulusCI provides a number of base task classes that are useful for building completely custom tasks.  For this example, we'll use the `BaseSalesforceApiTask` which initializes the `simple-salesforce` python library for interacting with the Salesforce REST API.  `BaseSalesforceApiTask` sets `self.sf` to an initialized instance with the access token already set so you just focus on writing your API interaction logic.

Create the file `tasks/rest.py':: python

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

    cumulusci2 task list
    cumulusci2 task info list_contacts
        

Query the Tooling API
---------------------

For this example, we'll use `BaseSalesforceToolingApiTask` to query ApexClasses via the Tooling API.  This base class initializes a modified version of `simple-salesforce` that points to the Tooling API.  The initalized API wrapper is `self.tooling`.

Create the file `tasks/tooling.py`:: python

    from cumulusci.tasks.salesforce import BaseSalesforceToolingApiTask

    class ListApexClasses(BaseSalesforceToolingApiTask):
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

    cumulusci2 task list
    cumulusci2 task info list_classes

Extend the default update_admin_profile task
--------------------------------------------

The previous examples showed how to add a completely new task, but what if we need to implement some custom project specific logic into an existing task?  For this example, we'll take a look at how the Salesforce.org Nonprofit Success Pack modifies the `update_admin_profile` task to grant FLS on custom fields added to a managed object and set the visibility and default values for project specific record types.

The following is the content of the `tasks/salesforce.py` file in the Cumulus repository:: python

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
