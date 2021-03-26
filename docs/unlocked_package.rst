Release an Unlocked Package
===========================

While CumulusCI was originally created to develop managed packages, it can also be used to develop and release `unlocked packages <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_unlocked_pkg_intro.htm>`_.

.. warning::

    We do not currently support setting the Ancestor Id for a 2GP package.


Prerequisites
-------------

To create unlocked package versions, complete these steps.

* `Enable DevHub Features in Your Org <https://developer.salesforce.com/docs/atlas.en-us.packagingGuide.meta/packagingGuide/sfdx_setup_enable_devhub.htm>`_.
* `Enable Unlocked and Second-Generation Managed Packaging <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_setup_enable_secondgen_pkg.htm>`_.
* Connect the Dev Hub org to the CumulusCI keychain by running ``cci org connect devhub``. (This is necessary even if ``sfdx`` has already authenticated to the Dev Hub).
* To create an unlocked package with a namespace, you must also create a new Developer Edition org to `Create and Register Your Namespace <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_unlocked_pkg_create_namespace.htm>`_, and link the namespace to your Dev Hub.



Create a Package Version
------------------------

To create a new unlocked package version, run the ``create_package_version`` task against a scratch org.

.. code-block:: console

    $ cci task run create_package_version --org <org_name> --package_type Unlocked

This task looks in your default Dev Hub org (as configured in ``sfdx``) for an unlocked package with the name and namespace specified in the task options (defaulting to the name and namespace from the ``project__package`` section of the ``cumulusci.yml`` file). If a matching package doesn't exist, CumulusCI first creates a `Package2 <https://developer.salesforce.com/docs/atlas.en-us.api_tooling.meta/api_tooling/tooling_api_objects_package2.htm>`_ object, and then submits a `request <https://developer.salesforce.com/docs/atlas.en-us.api_tooling.meta/api_tooling/tooling_api_objects_package2versioncreaterequest.htm>`_ to create the package version. When completed (which can take some time), the task outputs a ``SubscriberPackageVersion`` ID, which can be used to install the package in another org.

If a package version already exists with the exact same contents, as determined by the hash of the package metadata, its ``SubscriberPackageVersion`` ID is returned rather than creating a new version.



Handle Dependencies
---------------------

CumulusCI tries to convert dependencies configured under the ``project`` section of the ``cumulusci.yml`` file into a ``SubscriberPackageVersion`` ID (``04t`` key prefix). This format is required for dependencies in the API to create a package version.

For dependencies that are specified as a managed package namespace and version, or dependencies specified as a GitHub repository with releases that can be resolved to a namespace and version, CumulusCI needs a scratch org with the dependencies installed to execute this conversion in the ``create_package_version`` task.

.. important:: Install the dependencies in this scratch org *before* running the ``create_package_version`` task! 

The scratch org's definition file also specifies the correct org shape when building the new package version.

For dependencies that are an unpackaged bundle of metadata, CumulusCI creates an additional unlocked package to contain them.



Promote a Package Version
-------------------------

To be installed in a production org, an 2GP package version must be `promoted <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_unlocked_pkg_create_pkg_ver_promote.htm>`_ to mark it as released.

Use the ``promote_package_version`` task along with a valid ``SubscriberPackageVersionId`` to promote a 2GP package.

.. code-block:: console

    $ cci task run promote_package_version --version_id 04t000000000000

If additional unlocked packages were created to hold unpackaged dependencies, they must be promoted as well.
To promote dependencies automatically use ``--promote_dependencies True``.

.. code-block:: console

    $ cci task run promote_package_version --version_id 04t000000000000 --promote_dependencies True

Alternatively, you can use the ``sfdx force:package:version:promote`` command to promote a 2GP package.


Install the Unlocked Package
----------------------------

To install an unlocked package with CumulusCI:

Configure either the ``update_dependencies`` or the ``install_managed`` task and provide the ``SubscriberPackageVersion`` ID of the unlocked package to be used.

The ``update_dependencies`` task can be configured in the ``cumulusci.yml`` file.

.. code-block::yaml

    task: update_dependencies
    options:
        dependencies:
            - version_id: 04t000000000000

For the ``install_managed`` task, run it via ``cci``...

.. code-block::console

    $ cci task run intsall_managed --version 04t000000000000 --org <org_name>

Or configure it in the ``cumulusci.yml`` file.

.. code-block::yaml

    task: install_managed
    options:
        version: 04t000000000000

To install unlocked packages in an org that doesn't use CumulusCI, use one of these methods. 

* `Install via the Salesforce CLI <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_unlocked_pkg_install_pkg_cli.htm>`_
* `Install via an Installation URL <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_unlocked_pkg_install_pkg_ui.htm>`_
