Manage Unpackaged Configuration
===============================

Not everything that's part of an application can be part of a package.

CumulusCI implements the Product Delivery Model by offering support for complex applications - applications that may include multiple managed packages, as well as unpackaged metadata, and setup automation that configures org settings or makes precise changes to existing configuration.

The tools used to implement that support are *unpackaged metadata* and *Metadata ETL*. 

Unpackaged metadata refers to metadata that is not delivered as part of a package, and can include both support metadata delivered to users as well as metadata that is used operationally in configuring orgs used by the product. 

Metadata ETL is a suite of tasks that support surgically altering existing metadata in an org. Metadata ETL is a powerful technique for delivering changes to unpackaged configuration in an org without risking damage by overwriting existing customizations with stored metadata. Metadata ETL is particularly relevant for delivering applications to customers safely and is often a superior alternative to unpackaged metadata. See :ref:`metadata-etl` for more information.

Roles of Unpackaged Metadata
----------------------------

``unpackaged/pre``: Preparing an Org
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Some projects need to have unpackaged metadata deployed to finish the customization of an org, *before* the project's own code and metadata are deployed. For example, the Nonprofit Success Pack needs to deploy unpackaged Record Types prior to installing its own packages. ``unpackaged/pre`` is the location designed for such metadata, which is stored in subdirectories such as ``unpackaged/pre/first``.

CumulusCI's out-of-the-box flows that build an org, such as ``dev_org`` and ``install_prod``, always deploy metadata bundles found in ``unpackaged/pre`` before proceeding to the deployment of the application. Further, it's easy to include ``unpackaged/pre`` metadata in customer-facing installers run via MetaDeploy.

The task ``deploy_pre``, which is part of the ``dependencies`` flow, is responsible for deploying these bundles.

Metadata should not be included in ``unpackaged/pre`` unless it is intended to be delivered to all installations of the product.

``unpackaged/post``: Configuration After Package Install
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Projects often include metadata that is genuinely part of the application, but either cannot be delivered as part of a managed package or for operational reasons should not be. For example, a product that wishes to deliver ``TopicsForObjects`` metadata cannot do so as part of a managed package, because that type of metadata is not packageable. (See the `Metadata Coverage Report <https://mdcoverage.secure.force.com/docs/metadata-coverage>`_ for more about which components are packageable).

``unpackaged/post`` is the home for metadata of this kind, which is stored in subdirectories such as ``unpackaged/post/first``. CumulusCI's out-of-the-box flows that build an org, such as ``dev_org`` and ``install_prod``, always deploy metadata bundles found in ``unpackaged/post``, making it a full-fledged part of the application. Further, it's easy to include ``unpackaged/post`` metadata in customer-facing installers run via MetaDeploy.

The task ``deploy_post``, which is part of the ``config_dev``, ``config_qa``, and ``config_managed`` flows, is responsible for deploying these bundles.

Metadata should *not* be included in ``unpackaged/post`` unless it is intended to be delivered to all environments (both managed installations and unmanaged deployments). It's critical for managed package projects that this metadata include namespace tokens (see :ref:`namespace-injection`).

``unpackaged/config``: Tailoring Orgs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Projects may come with more than one supported configuration in their CumulusCI automation. For example, projects may support distinct, tailored ``dev_org``, ``qa_org``, and ``install_prod`` flows, each of which performs different setup for their specific use case. Unpackaged metadata stored in ``unpackaged/config`` is a tool to support operational needs to tailor orgs to different configurations. 

For example, a testing-oriented scratch org may wish to deploy a customized set of Page Layouts to help testers easily visualize data under test. Such page layouts could be stored in ``unpackaged/config/qa``.


Unpackaged Metadata Folder Structure
------------------------------------

All unpackaged metadata is stored in the ``unpackaged`` directory tree. Within this directory are the three top-level directories, ``unpackaged/pre``, ``unpackaged/post``, and ``unpackaged/config``.

These trees contain metadata bundles in Metadata API format: that is, a directory containing a ``package.xml`` manifest and Metadata API-format source code. CumulusCI does not support Salesforce DX format for unpackaged bundles.

.. _namespace-injection:

Namespace Injection
-------------------

Projects that build managed packages often must construct their unpackaged metadata to be deployable in multiple contexts: unmanaged deployments, such as developer orgs, unmanaged namespaced scratch orgs, and also managed contexts, such as a beta test org or a demo org created with ``install_prod``.

  Projects that are building an org implementation or a non-namespaced package do not have a namespace or a distinction between managed and unmanaged contexts. This section is relevant to projects that build namespaced packages.

Metadata located in ``unpackaged/post``, for example, is deployed after the application code in both unmanaged and managed contexts. If that metadata contains references to the application components, it must be deployable when that metadata both is (in a managed context or namespaced scratch org) and is not (in an unmanaged context) namespaced.

CumulusCI uses a strategy called *namespace injection* to support this use case. Namespace injection is very powerful, but requires care from application implementors to ensure that metadata remains deployable in all contexts.

Metadata files where a namespace needs to be conditionally applied to components for insertion into different contexts must replace the namespace with a *token*, which CumulusCI replaces with the appropriate value or an empty string:

* ``%%%NAMESPACE%%%`` is replaced with the package’s namespace in any context with a namespace (namespaced org or managed org), otherwise a blank.
* ``%%%NAMESPACED_ORG%%%`` is replaced with the package’s namespace in a namespaced org only, not in a managed installation, otherwise a blank. This supports use cases where, for example, components in one unpackaged metadata bundle must refer to components in another, and the dependency bundle acquires a namespace it would not otherwise have by being deployed into a namespaced org.
* ``%%%NAMESPACE_OR_C%%%`` is used like ``%%%NAMESPACE%%%`` but instead of a blank is replaced with ``c``, the generic namespace used in Lightning components.
* ``%%%NAMESPACED_ORG_OR_C%%%`` is used like ``%%%NAMESPACE_OR_C%%%``, but is replaced with the namespace only in a namespaced scratch org.
* ``%%%NAMESPACE_DOT%%%`` is used like ``%%%NAMESPACE%%%``, but is replaced with the namespace followed by a period (``.``) rather than two underscores. This token can be used to construct references to packaged Record Types.

Here's an example from the Nonprofit Success Pack. This metadata is stored in a subdirectory under ``unpackaged/post``, meaning it's deployed after the application metadata. It updates a Compact Layout on the ``Account`` object and references packaged metadata from the application, as well as from other managed packages. This metadata therefore requires the use of namespace tokens to represent the ``npsp`` namespace, allowing CumulusCI to automatically adapt the metadata to deploy into managed and unmanaged contexts.

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

Note that only the reference to the NPSP field ``Number_of_Household_Members__c`` is tokenized. (This field is called ``npsp__Number_of_Household_Members__c`` when installed as part of the managed package). References to NPSP's own managed package dependency, ``npo02``, are not tokenized, because this metadata is always namespaced when installed.

If this metadata were not tokenized, it would fail to deploy into an org containing NPSP as a beta or released managed package.

Note: the resolution of component references in namespaced scratch orgs and in managed installations of the same metadata are not identical. Metadata that is tokenized and can deploy cleanly in a namespaced scratch org may fail in a managed context.

Capture Unpackaged Metadata
---------------------------

CumulusCI provides tasks to easily capture changes to unpackaged metadata, just as with packaged metadata. For an introduction, see TODO: link to the dev section.

When working with unpackaged metadata, it's important to maintain awareness of some key considerations related to capturing metadata that is not part of the main application.

* Take care to separate your development between the different bundles you wish to capture. For example, if you have changes to make in the application and also in unpackaged metadata, complete the application changes first, capture them, then make the unpackaged changes and capture them. If you conflate changes to components that live in separate elements of your project, it'll be more challenging to untangle them.
* Whenever possible, build your unpackaged metadata in an org that contains a beta or released managed package. By doing so, you ensure that your metadata contains namespaces when extracted. CumulusCI makes it easy to replace namespaces with tokens when you retrieve metadata. It's much more difficult to manually tokenize metadata that's retrieved from an unmanaged org, without namespaces.

After building changes to unpackaged metadata in a managed org, retrieve it using ``retrieve_changes``, with the additional ``namespace_tokenize`` option, and use the ``path`` option to direct the retrieved metadata to your desired unpackaged directory.

For example, this command would capture metadata changes into the ``unpackaged/config/qa`` subdirectory, replacing references to the namespace ``npsp`` with the appropriate token:

.. code-block:: console

    $ cci task run retrieve_changes -o path unpackaged/config/qa -o namespace_tokenize npsp

Projects that use unpackaged metadata extensively may define capture tasks to streamline this process, such as this one:

.. code-block:: yaml

    retrieve_qa_config:
        description: Retrieves changes to QA configuration metadata
        class_path: cumulusci.tasks.salesforce.sourcetracking.RetrieveChanges
        options:
            path: unpackaged/config/qa
            namespace_tokenize: $project_config.project__package__namespace

If you're not able to build your unpackaged metadata in a managed org, you can still capture it with ``retrieve_changes``, but it will be necessary to manually insert namespace tokens to allow that metadata to be deployed in a managed or namespaced context.

Customize Config Flows
----------------------

Projects often customize new tasks that deploy ``unpackaged/config`` bundles, and harness these tasks in flows. For example, projects that use ``unpackaged/config/qa`` often define a task ``deploy_qa_config`` like this one:

.. code-block:: yaml

    deploy_qa_config:
        description: Deploys additional fields used for QA purposes only
        class_path: cumulusci.tasks.salesforce.Deploy
        options:
            path: unpackaged/config/qa
            namespace_inject: $project_config.project__package__namespace

This task is then added to relevant flows, like ``config_qa``:

.. code-block:: yaml

    config_qa:
        steps:
            3:
                task: deploy_qa_config

When deployment tasks are used in managed or namespaced contexts, it's important to use the option ``unmanaged: False`` so that CumulusCI knows to inject the namespace appropriately:

.. code-block:: yaml

    config_regression:
        steps:
            3: 
                task: deploy_qa_config
                options:
                    unmanaged: False

For more details on customizing Flows and Tasks, see TODO: link to relevant section.
