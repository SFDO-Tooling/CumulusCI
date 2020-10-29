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

(If you're capturing post-install metadata that will remain unpackaged, it is best to do so starting with a managed installation of your package. This makes it possible to convert references to the package namespace into CumulusCI's namespace token strings, so that the retrieved metadata can be deployed on top of either managed installations or unmanaged deployments of the package. To set up an org with the latest managed beta release, use the ``install_beta`` flow.)
