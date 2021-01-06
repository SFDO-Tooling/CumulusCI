Release an Unlocked Package
===========================
While CumulusCI was originally created with a focus on developing managed packages,
it can also be used to develop and release `unlocked packages <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_unlocked_pkg_intro.htm>`_.



Prerequisites
-------------
In order to create unlocked package versions, you need to have a few things set up:

1. `Enable Dev Hub in Your Org <https://developer.salesforce.com/docs/atlas.en-us.packagingGuide.meta/packagingGuide/sfdx_setup_enable_devhub.htm>`_
2. `Enable Unlocked and Second-Generation Managed Packaging <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_setup_enable_secondgen_pkg.htm>`_
3. Connect the Dev Hub org to the CumulusCI keychain by running ``cci org connect devhub`` (this is necessary even if sfdx has already authenticated to the Dev Hub).
4. If you want to create an unlocked package with a namespace, you must also create a new Developer Edition org to `Create and Register Your Namespace <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_unlocked_pkg_create_namespace.htm>`_, and link the namespace to your Dev Hub.



Create a Package Version
------------------------
To create a new unlocked package version, run the ``create_package_version`` task against a scratch org:

.. code-block:: console

    $ cci task run create_package_version --org dev --package_type Unlocked

This task will look in your default Dev Hub org (as configured in sfdx) for an unlocked package with the
name and namespace specified in the task options (defaulting to the name and namespace from the 
``project__package`` section of ``cumulusci.yml``). If a matching package doesn't exist yet, it will be created.

The task then submits a request to create the package version, and once completed (which can take some time), 
the task will output some information including the SubscriberPackageVersion Id, which can be used to install the package in another org.

If a package version already exists with the exact same contents, its Id will be returned instead of creating a new package version.



Handling Dependencies
---------------------
If your project has dependencies configured in the ``project`` section of ``cumulusci.yml``, 
CumulusCI will try to convert them into a Subscriber Package Version Id (``04t`` key prefix), 
which is the format required for dependencies in the API for creating a package version.

For dependencies that are specified as a managed package namespace and version, 
or dependencies specified as a GitHub repository with releases that can be resolved to a namespace and version, 
CumulusCI needs a scratch org with the dependencies installed in order to do this conversion.
This is the purpose of the scratch org passed to the ``create_package_version`` task (``dev`` in the example above).
You must make sure the dependencies are installed in this org before running the 
``create_package_version`` task. The scratch org definition file from this scratch org 
will also be used to specify the correct org shape when building the new package version.

For dependencies that are an unpackaged bundle of metadata, CumulusCI will create an additional unlocked package to contain them.



Promote a Package Version
-------------------------
In order to be installed in a production org, an unlocked package version must be
`promoted <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_unlocked_pkg_create_pkg_ver_promote.htm>`_
to mark it as released.

CumulusCI does not yet provide any tools to help with this, so for now you must use the ``sfdx force:package:version:promote`` command.
If additional unlocked packages were created to hold unpackaged dependencies, they must be promoted as well.



Install the Unlocked Package
----------------------------
There are two methods available for installing a package in an org: 

* `Install via the Salesforce CLI <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_unlocked_pkg_install_pkg_cli.htm>`_
* `Install via an installation URL <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_unlocked_pkg_install_pkg_ui.htm>`_

.. note:: Packages can only be installed in Scratch orgs, Sandbox orgs, DE orgs, and Production orgs.
