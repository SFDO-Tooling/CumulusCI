Cookbook
========

Create a Custom Retrieve Task
-----------------------------
If you will be retrieving changes into a directory repeatedly,
consider creating a custom task with the correct options
so that you don't need to specify them on the command line each time.

To do this, add YAML like this to your project's ``cumulusci.yml``:

.. code-block:: yaml

    tasks:
        retrieve_config_dev:
            description: Retrieves the current changes in the scratch org into unpackaged/config/dev
            class_path: cumulusci.tasks.salesforce.sourcetracking.RetrieveChanges
            options:
                path: unpackaged/config/dev
                namespace_tokenize: $project_config.project__package__namespace

If you're capturing post-install metadata that will remain unpackaged, it is best to do so starting with a managed installation of your package.
This makes it possible to convert references to the package namespace into CumulusCI's namespace token strings, so that the retrieved metadata can be deployed on top of either managed installations or unmanaged deployments of the package.
To set up an org with the latest managed beta release, use the ``install_beta`` flow.

Task Recipes
------------

Run a Shell Command
******************************

.. code-block:: yaml

    run_custom_command:
        description: Greets the user
        class_path: cumulusci.cli
        options: 
            command: "echo 'Hello there!"

        

Run a ``sfdx`` Command
****************************
The ``dx`` task lets you run an arbitrary ``sfdx`` command.
You can perform this with ``cci`` on a terminal::

    $ cci task run dx -o command 'force:api:limits:display'

Or you can utilize the same ``class_path`` as the ``dx`` task and make a custom task that can be executed by itself or as a step in a flow.

.. code-block:: yaml

    dx_limits:
        description: Display
        class_path: cumulusci.tasks.sfdx.SFDXBaseTask
        group: dx 
        options: 
            command: sfdx force:limits:api:display

In this case, we actually utilize ``SFDXBaseTask``, if you would like to run a ``sfdx`` command that references an org, utilize ``SFDXOrgTask`` instead.



Custom Deploy
************************
It is often useful to be able to define multiple custom deployment tasks that deployg a specific subset of your projects metadata.
This is particularly true when working with `unpackaged Metadata <TODO>`_.

Here is a custom task that is defined to only deploy only the metadata contained in ``unmanaged/config/reports``.

.. code-block:: yaml

    deploy_reports:
        description: Deploy Reports 
        class_path: cumulusci.tasks.salesforce.Deploy
        options:
            path: unmanaged/config/reports    

Being able to give this task a new name makes it much more intuitive as to what the task is actually doing.
Multiple custom deploy tasks like this allow NPSP to `create flows <https://github.com/SalesforceFoundation/NPSP/blob/87daa94f9494d28ce3a5cc52bd5d5308cc804a2b/cumulusci.yml#L692>` that make it easy to define the order that Metadata is deployed in.
            


Task to Execute Anonymous Apex
*********************************
The following shows an example task named ``project_default_settings`` which runs the public static method ``initializeProjectDefaults()`` located in file ``scripts.initialize.cls``::

    project_default_settings:
        description: Configure the default project settings
        class_path: cumulusci.tasks.apex.anon.AnonymousApexTask
        group: projectName
        options:
            path: scripts/initialize.cls
            apex: initializeProjectDefaults();


Flow Recipes
------------

Robot Recipes
-------------

Metadata ETL Recipes
--------------------

Python Recipes
--------------

