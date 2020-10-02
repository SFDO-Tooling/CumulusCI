Manage Unpackaged Configuration
===============================

Not everything that's part of an application can be part of a package.

CumulusCI implements the Product Delivery Model by offering support for complex applications - applications that may include multiple managed packages, as well as unpackaged metadata, and setup automation that configures org settings or makes surgical changes to existing configuration.

The tools used to implement that support are *unpackaged metadata* and *Metadata ETL*. 

Unpackaged metadata refers to metadata that is not delivered as part of a package, and can include both support metadata delivered to users as well as metadata that is used operationally in configuring orgs used by the product. 

Metadata ETL is a suite of tasks that support surgically altering existing metadata in an org. Metadata ETL is a powerful technique for delivering changes to unpackaged configuration in an org without risking damage by overwriting existing customizations with stored metadata. Metadata ETL is particularly relevant for delivering applications to customers safely and is often a viable alternative to using unpackaged metadata. See :ref:`metadata-etl` for more information.

Roles of Unpackaged Metadata
----------------------------

``unpackaged/pre``: Preparing an org
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Some projects need to have unpackaged metadata deployed to finish the customization of an org, *before* the project's own code and metadata are deployed. For example, a product like the Nonprofit Success Pack may need to deploy unpackaged Record Types prior to installing its own packages or metadata. ``unpackaged/pre`` is the location designed for such metadata, which is stored in subdirectories such as ``unpackaged/pre/first``.

CumulusCI's out-of-the-box flows that build an org, such as ``dev_org`` and ``install_prod``, always deploy metadata bundles found in ``unpackaged/pre`` before proceeding to the deployment of the application. Further, it's easy to include ``unpackaged/pre`` metadata in customer-facing installers run via MetaDeploy.

The task ``deploy_pre``, which is part of the ``dependencies`` flow, is responsible for deploying these bundles.

Metadata that's not intended to be delivered to all installations of the product should *not* be included in ``unpackaged/pre``.

``unpackaged/post``: Configuration after package install
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Projects often include metadata that is genuinely part of the application, but either cannot be delivered as part of a managed package or for operational reasons should not be. For example, a product that wishes to deliver ``TopicsForObjects`` metadata cannot do so as part of a managed package, because that type of metadata is not packageable.

``unpackaged/post`` is the home for metadata of this kind, which is stored in subdirectories such as ``unpackaged/post/first``. CumulusCI's out-of-the-box flows that build an org, such as ``dev_org`` and ``install_prod``, always deploy metadata bundles found in ``unpackaged/post``, making it a full-fledged part of the application. Further, it's easy to include ``unpackaged/post`` metadata in customer-facing installers run via MetaDeploy.

The task ``deploy_post``, which is part of the ``config_dev``, ``config_qa``, and ``config_managed`` flows, is responsible for deploying these bundles.

Metadata that's not intended to be delivered to all installations of the product should *not* be included in ``unpackaged/post``. It's critical for managed package projects that this metadata include namespace tokens (see :ref:`namespace-injection`).

``unpackaged/config``: Tailoring orgs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Projects may come with more than one supported configuration in their CumulusCI automation. For example, projects may support distinct, tailored ``dev_org``, ``qa_org``, and ``install_prod`` flows, each of which performs different setup for their specific use case. Unpackaged metadata stored in ``unpackaged/config`` is a tool to support operational needs to tailor orgs to different configurations. For example, a testing-oriented scratch org may wish to deploy a customized set of Page Layouts to help testers easily visualize data under test. Such page layouts could be stored in ``unpackaged/config/qa``.

Projects often customize new tasks that deploy ``unpackaged/config`` bundles. For example, projects that use ``unpackaged/config/qa`` often define a task ``deploy_qa_config`` like this one:

.. code-block:: yaml

    deploy_qa_config:
        description: Deploys additional fields used for QA purposes only
        class_path: cumulusci.tasks.salesforce.Deploy
        group: Salesforce Metadata
        options:
            path: unpackaged/config/qa
            namespace_inject: $project_config.project__package__namespace

This task is then added to relevant flows, like ``config_qa``.

For more details on customizing Flows and Tasks, see TODO: link to relevant section.

Unpackaged Metadata Folder Structure
------------------------------------

All unpackaged metadata is stored in the ``unpackaged`` directory tree. Within this directory are the three top-level directories, ``unpackaged/pre``, ``unpackaged/post``, and ``unpackaged/config``.

These trees contain metadata bundles in Metadata API format: that is, a directory containing a ``package.xml`` manifest and Metadata API-format source code. CumulusCI does not support Salesforce DX format for unpackaged bundles.

.. _namespace-injection:

Namespace Injection
-------------------

Projects that build managed packages often must construct their unpackaged metadata to be deployable in multiple contexts: unmanaged deployments, such as developer orgs, unmanaged namespaced scratch orgs, and also managed contexts, such as a beta test org or a demo org created with ``install_prod``.

  Projects that are building an org implementation (not a package with a namespace) do not need to use namespace injection.

Metadata located in ``unpackaged/post``, for example, is deployed after the application code in both unmanaged and managed contexts. If that metadata contains references to the application components, it must be deployable when that metadata both is (in a managed context or namespaced scratch org) and is not (in an unmanaged context) namespaced.

CumulusCI uses a strategy called *namespace injection* to support this use case. Namespace injection is very powerful, but requires care from application implementors to ensure that metadata remains deployable in all contexts.

Metadata files where a namespace needs to be conditionally applied to components for insertion into different contexts must replace the namespace with a *token*, which CumulusCI replaces with the appropriate value or an empty string:

* ``%%%NAMESPACE%%%`` is replaced with the package’s namespace in any context with a namespace (namespaced org or managed org), otherwise a blank.
* ``%%%NAMESPACED_ORG%%%`` is replaced with the package’s namespace in a namespaced org only, not in a managed installation, otherwise a blank. This supports use cases where, for example, components in one unpackaged metadata bundle must refer to components in another, and the dependency bundle acquires a namespace it would not otherwise have by being deployed into a namespaced org.
* ``%%%NAMESPACE_OR_C%%%`` is used like ``%%%NAMESPACE%%%`` but instead of a blank is replaced with ``c``, the generic namespace used in Lightning components.
* ``%%%NAMESPACED_ORG_OR_C%%%`` is used like ``%%%NAMESPACE_OR_C%%%``, but is replaced with the namespace only in a namespaced scratch org.
* ``%%%NAMESPACE_DOT%%%`` is used like ``%%%NAMESPACE%%%``, but is replaced with the namespace followed by a period (``.``) rather than two underscores. This token can be used to construct references to packaged Record Types.

  The resolution of component references in namespaced scratch orgs and in managed installations of the same metadaat are not identical. Metadata that is tokenized and can deploy cleanly in a namespaced scratch org may fail in a managed context.

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

Capture Unpackaged Metadata
---------------------------



Customize Config Flows
----------------------
