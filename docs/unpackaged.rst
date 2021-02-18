Manage Unpackaged Configuration
===============================

Not everything that's part of an application can be part of a package.

CumulusCI implements the Product Delivery Model by offering support for complex applications -- applications that may include multiple managed packages as well as unpackaged metadata, and setup automation that configures org settings or makes precise changes to existing configuration.

The tools used to implement that support are *unpackaged metadata* and *Metadata ETL*. 

Unpackaged metadata refers to metadata that is not delivered as part of a package, and can include both support metadata delivered to users as well as metadata that operationally configures orgs used by the product. 

Metadata ETL is a suite of tasks that support surgically altering existing metadata in an org. It's a powerful technique that changes the unpackaged configuration in an org without risking damage by overwriting existing customizations with stored metadata. Metadata ETL is relevant for delivering applications to customers safely, and is often a superior alternative to unpackaged metadata.

To learn more, see `Metadata ETL<TODO>`_.



Roles of Unpackaged Metadata
----------------------------


``unpackaged/pre``: Prepare an Org
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Some projects require that unpackaged metadata be deployed to finish the customization of an org *before* the project's own code and metadata are deployed.

    Example: The Nonprofit Success Pack (NPSP) must deploy unpackaged Record Types prior to installing its own packages. ``unpackaged/pre`` is the location designed for such metadata, which is stored in subdirectories such as ``unpackaged/pre/first``.

CumulusCI's standard flows that build orgs, such as ``dev_org`` and ``install_prod``, always deploy metadata bundles found in ``unpackaged/pre`` before proceeding to the deployment of the application. It's also easy to include ``unpackaged/pre`` metadata in customer-facing installers run via MetaDeploy.

The ``deploy_pre`` task, which is part of the ``dependencies`` flow, is responsible for deploying these bundles.

.. important:: Do not include metadata in ``unpackaged/pre`` unless it is intended to be delivered to *all* installations of the product.


``unpackaged/post``: Configuration After Package Install
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Projects often include metadata that is genuinely part of the application, but either cannot be delivered as part of a managed package for operational reasons. This metadata must be deployed *after* the project's own code and metadata are deployed first and the org is configured.

    Example: A product that wishes to deliver ``TopicsForObjects`` metadata cannot do so as part of a managed package because that type of metadata is not packageable.

.. note:: To learn more about which components are packageable, see the `Metadata Coverage Report <https://mdcoverage.secure.force.com/docs/metadata-coverage>`_.

..

    ``unpackaged/post`` is the home for this kind of metadata, which is stored in subdirectories such as ``unpackaged/post/first``.

CumulusCI's standard flows that build orgs, such as ``dev_org`` and ``install_prod``, always deploy metadata bundles found in ``unpackaged/post``, making it a full-fledged part of the application. It's also easy to include ``unpackaged/post`` metadata in customer-facing installers run via MetaDeploy.

The ``deploy_post`` task, which is part of the ``config_dev``, ``config_qa``, and ``config_managed`` flows, is responsible for deploying these bundles.

.. important:: Do not include metadata in ``unpackaged/post`` unless it is intended to be delivered to *all* environments (both managed installations and unmanaged deployments). It's also critical for managed package projects that this metadata include namespace tokens (see `namespace injection`_).


``unpackaged/config``: Tailor an Org
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Projects can come with more than one supported configuration in their CumulusCI automation.

    Example: Projects often support distinct, tailored ``dev_org``, ``qa_org``, and ``install_prod`` flows, each of which performs a unique setup for their specific use case.

Unpackaged metadata stored in ``unpackaged/config`` is a tool to support operational needs that tailor orgs to different configurations. 

    Example: A testing-oriented scratch org needs to deploy a customized set of Page Layouts to help testers easily visualize data under test. Such page layouts are stored in ``unpackaged/config/qa``.



Unpackaged Metadata Folder Structure
------------------------------------

All unpackaged metadata is stored in the ``unpackaged`` directory tree, which contains these top-level directories.

* ``unpackaged/pre``
* ``unpackaged/post``
* ``unpackaged/config``

These trees contain metadata bundles in Metadata API format, represented as a directory containing a ``package.xml`` manifest and Metadata API-format source code. CumulusCI does not support Salesforce DX format for unpackaged bundles.



Namespace Injection
-------------------

Projects that build managed packages often construct their unpackaged metadata to be deployable in multiple contexts.

* Unmanaged deployments, such as developer orgs
* Unmanaged namespaced scratch orgs
* Managed contexts, such as a beta test org or a demo org created with ``install_prod``

Because projects that are building an org implementation or a non-namespaced package do not have a namespace, or a distinction between managed and unmanaged contexts, these projects must also build namespaced packages.

    Example: Metadata located in ``unpackaged/post`` is deployed after the application code in both unmanaged and managed contexts. If that metadata contains references to the application components, it must be deployable when that metadata is nampespaced (in a managed context or namespaced scratch org) *and* when it is not (in an unmanaged context).

CumulusCI uses a strategy called *namespace injection* to support this use case. Namespace injection is very powerful, and requires care from application implementors to ensure that metadata remains deployable in all contexts.

Metadata files where a namespace is conditionally applied to components for insertion into different contexts must replace the namespace with a *token*, which CumulusCI replaces with the appropriate value, an empty string, or a default value.

* ``%%%NAMESPACE%%%`` is replaced with the package’s namespace in any context with a namespace (such as a namespaced org or managed org). Otherwise, it remains blank.
* ``%%%NAMESPACED_ORG%%%`` is replaced with the package’s namespace in a namespaced org *only*, not in a managed installation. Otherwise, it remains blank.
    .. note:: This token supports use cases where components in one unpackaged metadata bundle refer to components in another, and the dependency bundle acquires a namespace by being deployed into a namespaced org.
* ``%%%NAMESPACE_OR_C%%%`` is replaced with the package’s namespace in any context with a namespace (such as a namespaced org or managed org). Otherwise, it is replaced with ``c``, the generic namespace used in Lightning components.
* ``%%%NAMESPACED_ORG_OR_C%%%`` is replaced with the package's namespace in a namespaced org *only*, not in a managed installation. Otherwise, it is replaced with ``c``, the generic namespace used in Lightning components.
* ``%%%NAMESPACE_DOT%%%`` is replaced with the package’s namespace in any context with a namespace (such as a namespaced org or managed org) followed by a period (``.``) rather than two underscores.
    .. note:: This token is used to construct references to packaged Record Types.

..

    Example: A portion of metadata from the Nonprofit Success Pack (NPSP) is stored in a subdirectory under ``unpackaged/post``, meaning it's deployed after the application metadata. This metadata updates a Compact Layout on the ``Account`` object, and references packaged metadata from the application as well as from other managed packages. To complete these tasks, this metadata requires the use of namespace tokens to represent the ``npsp`` namespace, letting CumulusCI automatically adapt the metadata to deploy into managed and unmanaged contexts.

.. code-block:: xml

    <?xml version="1.0" encoding="UTF-8"?>
    <CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
        <compactLayouts>
            <fullName>NPSP_Household_Account</fullName>
            <fields>Name</fields>
            <fields>npo02__TotalOppAmount__c</fields>
            <fields>%%%NAMESPACE%%%Number_of_Household_Members__c</fields>
            <label>NPSP Household Account</label>
        </compactLayouts>
    </CustomObject>

..

    Note that only the reference to the NPSP field ``Number_of_Household_Members__c`` is tokenized. (This field is called ``npsp__Number_of_Household_Members__c`` when installed as part of the managed package.) References to NPSP's own managed package dependency, ``npo02``, are not tokenized because this metadata is always namespaced when installed.

    If this metadata isn't tokenized, it fails to deploy into an org containing NPSP as a beta or released managed package.

.. note:: The resolution of component references in namespaced scratch orgs and in managed installations of the same metadata are not identical. Metadata that is tokenized and deploys cleanly in a namespaced scratch org can still fail in a managed context.



Retrieve Unpackaged Metadata
----------------------------

CumulusCI provides tasks to retrieve changes to unpackaged metadata, just as with packaged metadata. For more details on these tasks, see `the dev section<TODO>`_.

When working with unpackaged metadata, it's important to maintain awareness of key considerations related to retrieving metadata that is not part of the main application.

* Take care to separate your development between the different bundles you wish to retrieve.
    Example: If you have changes to make in the application as well as in unpackaged metadata, complete the application changes first, retrieve them, and then make the unpackaged changes and retrieve those. If you conflate changes to components that live in separate elements of your project, it's difficult to untangle them.
* Whenever possible, build your unpackaged metadata in an org that contains a beta or released managed package. By doing so, the metadata contains namespaces when extracted, which CumulusCI easily replaces with tokens when retrieving metadata. It's difficult to manually tokenize metadata that's retrieved from an unmanaged org without namespaces. 

After building changes to unpackaged metadata in a managed org, retrieve it using ``retrieve_changes`` with the additional ``namespace_tokenize`` option, and use the ``path`` option to direct the retrieved metadata to your desired unpackaged directory.

    Example: Run ``retrieve_changes`` to retrieve metadata changes into the ``unpackaged/config/qa`` subdirectory, and replace references to the namespace ``npsp`` with the appropriate token.

.. code-block:: console

    $ cci task run retrieve_changes --path unpackaged/config/qa --namespace_tokenize npsp

Projects that use unpackaged metadata extensively define retrieve tasks to streamline this process.

    Example: Retrieve changes to QA configuration metadata.

.. code-block:: yaml

    retrieve_qa_config:
        description: Retrieves changes to QA configuration metadata
        class_path: cumulusci.tasks.salesforce.sourcetracking.RetrieveChanges
        options:
            path: unpackaged/config/qa
            namespace_tokenize: $project_config.project__package__namespace

..

    The ``retrieve_changes`` task retrieves unpackaged metadata in a managed org, but in this case you must manually insert namespace tokens to deploy metadata in a managed or namespaced context.



Customize Config Flows
----------------------

Projects often customize new tasks that deploy ``unpackaged/config`` bundles, and harness these tasks in flows. 

    Example: Projects that use ``unpackaged/config/qa`` often define a ``deploy_qa_config`` task.

.. code-block:: yaml

    deploy_qa_config:
        description: Deploys additional fields used for QA purposes only
        class_path: cumulusci.tasks.salesforce.Deploy
        options:
            path: unpackaged/config/qa
            namespace_inject: $project_config.project__package__namespace

..

    This task is then added to relevant flows, such as ``config_qa``.

.. code-block:: yaml

    config_qa:
        steps:
            3:
                task: deploy_qa_config

..

    When deployment tasks are used in managed or namespaced contexts, it's important to use the ``unmanaged: False`` option so that CumulusCI injects the namespace appropriately.

.. code-block:: yaml

    config_regression:
        steps:
            3: 
                task: deploy_qa_config
                options:
                    unmanaged: False

For more details on customizing tasks and flows, see `link to relevant section<TODO>`_.
