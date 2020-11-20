==========================================
Standard Tasks
==========================================

activate_flow
=============

**Description:** Activates Flows identified by a given list of Developer Names

**Class:** cumulusci.tasks.salesforce.activate_flow.ActivateFlow

Command Syntax
------------------------------------------

``$ cci task run activate_flow``


Options
------------------------------------------


``-o developer_names DEVELOPERNAMES``
	 *Required*

	 List of DeveloperNames to query in SOQL

add_page_layout_related_lists
=============================

**Description:** Adds specified Related List to one or more Page Layouts.

**Class:** cumulusci.tasks.metadata_etl.AddRelatedLists

Command Syntax
------------------------------------------

``$ cci task run add_page_layout_related_lists``


Options
------------------------------------------


``-o related_list RELATEDLIST``
	 *Required*

	 Name of the Related List to include

``-o fields FIELDS``
	 *Optional*

	 Array of field API names to include in the related list

``-o exclude_buttons EXCLUDEBUTTONS``
	 *Optional*

	 Array of button names to suppress from the related list

``-o custom_buttons CUSTOMBUTTONS``
	 *Optional*

	 Array of button names to add to the related list

``-o api_names APINAMES``
	 *Optional*

	 List of API names of entities to affect

``-o managed MANAGED``
	 *Optional*

	 If False, changes namespace_inject to replace tokens with a blank string

``-o namespace_inject NAMESPACEINJECT``
	 *Optional*

	 If set, the namespace tokens in files and filenames are replaced with the namespace's prefix

	 Default: $project_config.project__package__namespace

``-o api_version APIVERSION``
	 *Optional*

	 Metadata API version to use, if not project__package__api_version.

add_standard_value_set_entries
==============================

**Description:** Adds specified picklist entries to a Standard Value Set.

**Class:** cumulusci.tasks.metadata_etl.AddValueSetEntries

Command Syntax
------------------------------------------

``$ cci task run add_standard_value_set_entries``


Options
------------------------------------------


``-o entries ENTRIES``
	 *Optional*

	 Array of standardValues to insert. Each standardValue should contain the keys 'fullName', the API name of the entry, and 'label', the user-facing label. OpportunityStage entries require the additional keys 'closed', 'won', 'forecastCategory', and 'probability'; CaseStatus entries require 'closed'.

``-o api_names APINAMES``
	 *Optional*

	 List of API names of entities to affect

``-o managed MANAGED``
	 *Optional*

	 If False, changes namespace_inject to replace tokens with a blank string

``-o namespace_inject NAMESPACEINJECT``
	 *Optional*

	 If set, the namespace tokens in files and filenames are replaced with the namespace's prefix

	 Default: $project_config.project__package__namespace

``-o api_version APIVERSION``
	 *Optional*

	 Metadata API version to use, if not project__package__api_version.

add_picklist_entries
====================

**Description:** Adds specified picklist entries to a custom picklist field.

**Class:** cumulusci.tasks.metadata_etl.picklists.AddPicklistEntries

Command Syntax
------------------------------------------

``$ cci task run add_picklist_entries``


Options
------------------------------------------


``-o picklists PICKLISTS``
	 *Required*

	 List of picklists to affect, in Object__c.Field__c form.

``-o entries ENTRIES``
	 *Required*

	 Array of picklist values to insert. Each value should contain the keys 'fullName', the API name of the entry, and 'label', the user-facing label. Optionally, specify `default: True` on exactly one entry to make that value the default. Any existing values will not be affected other than setting the default (labels of existing entries are not changed).To order values, include the 'add_before' key. This will insert the new value before the existing value with the given API name, or at the end of the list if not present.

``-o record_types RECORDTYPES``
	 *Optional*

	 List of Record Type developer names for which the new values should be available. If any of the entries have `default: True`, they are also made default for these Record Types. Any Record Types not present in the target org will be ignored, and * is a wildcard. Default behavior is to do nothing.

``-o api_names APINAMES``
	 *Optional*

	 List of API names of entities to affect

``-o managed MANAGED``
	 *Optional*

	 If False, changes namespace_inject to replace tokens with a blank string

``-o namespace_inject NAMESPACEINJECT``
	 *Optional*

	 If set, the namespace tokens in files and filenames are replaced with the namespace's prefix

	 Default: $project_config.project__package__namespace

``-o api_version APIVERSION``
	 *Optional*

	 Metadata API version to use, if not project__package__api_version.

add_permission_set_perms
========================

**Description:** Adds specified Apex class access and Field-Level Security to a Permission Set.

**Class:** cumulusci.tasks.metadata_etl.AddPermissionSetPermissions

Command Syntax
------------------------------------------

``$ cci task run add_permission_set_perms``


Options
------------------------------------------


``-o field_permissions FIELDPERMISSIONS``
	 *Optional*

	 Array of fieldPermissions objects to upsert into permission_set.  Each fieldPermission requires the following attributes: 'field': API Name of the field including namespace; 'readable': boolean if field can be read; 'editable': boolean if field can be edited

``-o class_accesses CLASSACCESSES``
	 *Optional*

	 Array of classAccesses objects to upsert into permission_set.  Each classAccess requires the following attributes: 'apexClass': Name of Apex Class.  If namespaced, make sure to use the form "namespace__ApexClass"; 'enabled': boolean if the Apex Class can be accessed.

``-o api_names APINAMES``
	 *Optional*

	 List of API names of entities to affect

``-o managed MANAGED``
	 *Optional*

	 If False, changes namespace_inject to replace tokens with a blank string

``-o namespace_inject NAMESPACEINJECT``
	 *Optional*

	 If set, the namespace tokens in files and filenames are replaced with the namespace's prefix

	 Default: $project_config.project__package__namespace

``-o api_version APIVERSION``
	 *Optional*

	 Metadata API version to use, if not project__package__api_version.

assign_compact_layout
=====================

**Description:** Assigns the Compact Layout specified in the 'value' option to the Custom Objects in 'api_names' option.

**Class:** cumulusci.tasks.metadata_etl.UpdateMetadataFirstChildTextTask

Metadata ETL task to update a single child element's text within metadata XML.

If the child doesn't exist, the child is created and appended to the Metadata.   Furthermore, the ``value`` option is namespaced injected if the task is properly configured.

Example: Assign a Custom Object's Compact Layout
------------------------------------------------

Researching `CustomObject <https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/customobject.htm>`_ in the Metadata API documentation or even retrieving the CustomObject's Metadata for inspection, we see the ``compactLayoutAssignment`` Field.  We want to assign a specific Compact Layout for our Custom Object, so we write the following CumulusCI task in our project's ``cumulusci.yml``.

.. code-block::  yaml

  tasks:
      assign_compact_layout:
          class_path: cumulusci.tasks.metadata_etl.UpdateMetadataFirstChildTextTask
          options:
              managed: False
              namespace_inject: $project_config.project__package__namespace
              entity: CustomObject
              api_names: OurCustomObject__c
              tag: compactLayoutAssignment
              value: "%%%NAMESPACE%%%DifferentCompactLayout"
              # We include a namespace token so it's easy to use this task in a managed context.

Suppose the original CustomObject metadata XML looks like:

.. code-block:: xml

  <?xml version="1.0" encoding="UTF-8"?>
  <CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
      ...
      <label>Our Custom Object</label>
      <compactLayoutAssignment>OriginalCompactLayout</compactLayoutAssignment>
      ...
  </CustomObject>

After running ``cci task run assign_compact_layout``, the CustomObject metadata XML is deployed as:

.. code-block:: xml

  <?xml version="1.0" encoding="UTF-8"?>
  <CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
      ...
      <label>Our Custom Object</label>
      <compactLayoutAssignment>DifferentCompactLayout</compactLayoutAssignment>
      ...
  </CustomObject>

Command Syntax
------------------------------------------

``$ cci task run assign_compact_layout``


Options
------------------------------------------


``-o metadata_type METADATATYPE``
	 *Required*

	 Metadata Type

	 Default: CustomObject

``-o tag TAG``
	 *Required*

	 Targeted tag. The text of the first instance of this tag within the metadata entity will be updated.

	 Default: compactLayoutAssignment

``-o value VALUE``
	 *Required*

	 Desired value to set for the targeted tag's text. This value is namespace-injected.

``-o api_names APINAMES``
	 *Optional*

	 List of API names of entities to affect

``-o managed MANAGED``
	 *Optional*

	 If False, changes namespace_inject to replace tokens with a blank string

``-o namespace_inject NAMESPACEINJECT``
	 *Optional*

	 If set, the namespace tokens in files and filenames are replaced with the namespace's prefix

	 Default: $project_config.project__package__namespace

``-o api_version APIVERSION``
	 *Optional*

	 Metadata API version to use, if not project__package__api_version.

batch_apex_wait
===============

**Description:** Waits on a batch apex job to finish.

**Class:** cumulusci.tasks.apex.batch.BatchApexWait

Command Syntax
------------------------------------------

``$ cci task run batch_apex_wait``


Options
------------------------------------------


``-o class_name CLASSNAME``
	 *Required*

	 Name of the Apex class to wait for.

``-o poll_interval POLLINTERVAL``
	 *Optional*

	 Seconds to wait before polling for batch job completion. Defaults to 10 seconds.

check_sobjects_available
========================

**Description:** Runs as a preflight check to determine whether specific sObjects are available.

**Class:** cumulusci.tasks.preflight.sobjects.CheckSObjectsAvailable

Command Syntax
------------------------------------------

``$ cci task run check_sobjects_available``



check_org_wide_defaults
=======================

**Description:** Runs as a preflight check to validate Organization-Wide Defaults.

**Class:** cumulusci.tasks.preflight.sobjects.CheckSObjectOWDs

Command Syntax
------------------------------------------

``$ cci task run check_org_wide_defaults``


Options
------------------------------------------


``-o org_wide_defaults ORGWIDEDEFAULTS``
	 *Required*

	 The Organization-Wide Defaults to check, organized as a list with each element containing the keys api_name, internal_sharing_model, and external_sharing_model. NOTE: you must have External Sharing Model turned on in Sharing Settings to use the latter feature. Checking External Sharing Model when it is turned off will fail the preflight.

custom_settings_value_wait
==========================

**Description:** Waits for a specific field value on the specified custom settings object and field

**Class:** cumulusci.tasks.salesforce.custom_settings_wait.CustomSettingValueWait

Command Syntax
------------------------------------------

``$ cci task run custom_settings_value_wait``


Options
------------------------------------------


``-o object OBJECT``
	 *Required*

	 Name of the Hierarchical Custom Settings object to query. Can include the %%%NAMESPACE%%% token. 

``-o field FIELD``
	 *Required*

	 Name of the field on the Custom Settings to query. Can include the %%%NAMESPACE%%% token. 

``-o value VALUE``
	 *Required*

	 Value of the field to wait for (String, Integer or Boolean). 

``-o managed MANAGED``
	 *Optional*

	 If True, will insert the project's namespace prefix.  Defaults to False or no namespace.

``-o namespaced NAMESPACED``
	 *Optional*

	 If True, the %%%NAMESPACE%%% token will get replaced with the namespace prefix for the object and field.Defaults to False.

``-o poll_interval POLLINTERVAL``
	 *Optional*

	 Seconds to wait before polling for batch job completion. Defaults to 10 seconds.

command
=======

**Description:** Run an arbitrary command

**Class:** cumulusci.tasks.command.Command

**Example Command-line Usage:**
``cci task run command -o command "echo 'Hello command task!'"``

**Example Task to Run Command:**

..code-block:: yaml

    hello_world:
        description: Says hello world
        class_path: cumulusci.tasks.command.Command
        options:
        command: echo 'Hello World!'

Command Syntax
------------------------------------------

``$ cci task run command``


Options
------------------------------------------


``-o command COMMAND``
	 *Required*

	 The command to execute

``-o pass_env PASSENV``
	 *Required*

	 If False, the current environment variables will not be passed to the child process. Defaults to True

``-o dir DIR``
	 *Optional*

	 If provided, the directory where the command should be run from.

``-o env ENV``
	 *Optional*

	 Environment variables to set for command. Must be flat dict, either as python dict from YAML or as JSON string.

``-o interactive INTERACTIVE``
	 *Optional*

	 If True, the command will use stderr, stdout, and stdin of the main process.Defaults to False.

connected_app
=============

**Description:** Creates the Connected App needed to use persistent orgs in the CumulusCI keychain

**Class:** cumulusci.tasks.connectedapp.CreateConnectedApp

Command Syntax
------------------------------------------

``$ cci task run connected_app``


Options
------------------------------------------


``-o label LABEL``
	 *Required*

	 The label for the connected app.  Must contain only alphanumeric and underscores

	 Default: CumulusCI

``-o email EMAIL``
	 *Optional*

	 The email address to associate with the connected app.  Defaults to email address from the github service if configured.

``-o username USERNAME``
	 *Optional*

	 Create the connected app in a different org.  Defaults to the defaultdevhubusername configured in sfdx.

``-o connect CONNECT``
	 *Optional*

	 If True, the created connected app will be stored as the CumulusCI connected_app service in the keychain.

	 Default: True

``-o overwrite OVERWRITE``
	 *Optional*

	 If True, any existing connected_app service in the CumulusCI keychain will be overwritten.  Has no effect if the connect option is False.

create_community
================

**Description:** Creates a Community in the target org using the Connect API

**Class:** cumulusci.tasks.salesforce.CreateCommunity

Create a Salesforce Community via the Connect API.

Specify the `template` "VF Template" for Visualforce Tabs community,
or the name for a specific desired template

Command Syntax
------------------------------------------

``$ cci task run create_community``


Options
------------------------------------------


``-o template TEMPLATE``
	 *Required*

	 Name of the template for the community.

``-o name NAME``
	 *Required*

	 Name of the community.

``-o description DESCRIPTION``
	 *Optional*

	 Description of the community.

``-o url_path_prefix URLPATHPREFIX``
	 *Optional*

	 URL prefix for the community.

``-o retries RETRIES``
	 *Optional*

	 Number of times to retry community creation request

``-o timeout TIMEOUT``
	 *Optional*

	 Time to wait, in seconds, for the community to be created

``-o skip_existing SKIPEXISTING``
	 *Optional*

	 If True, an existing community with the same name will not raise an exception.

insert_record
=============

**Description:** Inserts a record of any sObject using the REST API

**Class:** cumulusci.tasks.salesforce.insert_record.InsertRecord

For example:

cci task run insert_record --org dev -o object PermissionSet -o values Name:HardDelete,PermissionsBulkApiHardDelete:true

Command Syntax
------------------------------------------

``$ cci task run insert_record``


Options
------------------------------------------


``-o object OBJECT``
	 *Required*

	 An sObject type to insert

``-o values VALUES``
	 *Required*

	 Field names and values in the format 'aa:bb,cc:dd'

create_package
==============

**Description:** Creates a package in the target org with the default package name for the project

**Class:** cumulusci.tasks.salesforce.CreatePackage

Command Syntax
------------------------------------------

``$ cci task run create_package``


Options
------------------------------------------


``-o package PACKAGE``
	 *Required*

	 The name of the package to create.  Defaults to project__package__name

``-o api_version APIVERSION``
	 *Required*

	 The api version to use when creating the package.  Defaults to project__package__api_version

create_managed_src
==================

**Description:** Modifies the src directory for managed deployment.  Strips //cumulusci-managed from all Apex code

**Class:** cumulusci.tasks.metadata.managed_src.CreateManagedSrc

Command Syntax
------------------------------------------

``$ cci task run create_managed_src``


Options
------------------------------------------


``-o path PATH``
	 *Required*

	 The path containing metadata to process for managed deployment

	 Default: src

``-o revert_path REVERTPATH``
	 *Required*

	 The path to copy the original metadata to for the revert call

	 Default: src.orig

create_unmanaged_ee_src
=======================

**Description:** Modifies the src directory for unmanaged deployment to an EE org

**Class:** cumulusci.tasks.metadata.ee_src.CreateUnmanagedEESrc

Command Syntax
------------------------------------------

``$ cci task run create_unmanaged_ee_src``


Options
------------------------------------------


``-o path PATH``
	 *Required*

	 The path containing metadata to process for managed deployment

	 Default: src

``-o revert_path REVERTPATH``
	 *Required*

	 The path to copy the original metadata to for the revert call

	 Default: src.orig

delete_data
===========

**Description:** Query existing data for a specific sObject and perform a Bulk API delete of all matching records.

**Class:** cumulusci.tasks.bulkdata.DeleteData

Command Syntax
------------------------------------------

``$ cci task run delete_data``


Options
------------------------------------------


``-o objects OBJECTS``
	 *Required*

	 A list of objects to delete records from in order of deletion.  If passed via command line, use a comma separated string

``-o where WHERE``
	 *Optional*

	 A SOQL where-clause (without the keyword WHERE). Only available when 'objects' is length 1.

``-o hardDelete HARDDELETE``
	 *Optional*

	 If True, perform a hard delete, bypassing the Recycle Bin. Note that this requires the Bulk API Hard Delete permission. Default: False

``-o ignore_row_errors IGNOREROWERRORS``
	 *Optional*

	 If True, allow the operation to continue even if individual rows fail to delete.

``-o inject_namespaces INJECTNAMESPACES``
	 *Optional*

	 If True, the package namespace prefix will be automatically added to objects and fields for which it is present in the org. Defaults to True.

deploy
======

**Description:** Deploys the src directory of the repository to the org

**Class:** cumulusci.tasks.salesforce.Deploy

Command Syntax
------------------------------------------

``$ cci task run deploy``


Options
------------------------------------------


``-o path PATH``
	 *Required*

	 The path to the metadata source to be deployed

	 Default: src

``-o unmanaged UNMANAGED``
	 *Optional*

	 If True, changes namespace_inject to replace tokens with a blank string

``-o namespace_inject NAMESPACEINJECT``
	 *Optional*

	 If set, the namespace tokens in files and filenames are replaced with the namespace's prefix

``-o namespace_strip NAMESPACESTRIP``
	 *Optional*

	 If set, all namespace prefixes for the namespace specified are stripped from files and filenames

``-o namespace_tokenize NAMESPACETOKENIZE``
	 *Optional*

	 If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject

``-o check_only CHECKONLY``
	 *Optional*

	 If True, performs a test deployment (validation) of components without saving the components in the target org

``-o test_level TESTLEVEL``
	 *Optional*

	 Specifies which tests are run as part of a deployment. Valid values: NoTestRun, RunLocalTests, RunAllTestsInOrg, RunSpecifiedTests.

``-o specified_tests SPECIFIEDTESTS``
	 *Optional*

	 Comma-separated list of test classes to run upon deployment. Applies only with test_level set to RunSpecifiedTests.

``-o static_resource_path STATICRESOURCEPATH``
	 *Optional*

	 The path where decompressed static resources are stored.  Any subdirectories found will be zipped and added to the staticresources directory of the build.

``-o namespaced_org NAMESPACEDORG``
	 *Optional*

	 If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.

``-o clean_meta_xml CLEANMETAXML``
	 *Optional*

	 Defaults to True which strips the <packageVersions/> element from all meta.xml files.  The packageVersion element gets added automatically by the target org and is set to whatever version is installed in the org.  To disable this, set this option to False

deploy_pre
==========

**Description:** Deploys all metadata bundles under unpackaged/pre/

**Class:** cumulusci.tasks.salesforce.DeployBundles

Command Syntax
------------------------------------------

``$ cci task run deploy_pre``


Options
------------------------------------------


``-o path PATH``
	 *Required*

	 The path to the parent directory containing the metadata bundles directories

	 Default: unpackaged/pre

``-o unmanaged UNMANAGED``
	 *Optional*

	 If True, changes namespace_inject to replace tokens with a blank string

``-o namespace_inject NAMESPACEINJECT``
	 *Optional*

	 If set, the namespace tokens in files and filenames are replaced with the namespace's prefix

``-o namespace_strip NAMESPACESTRIP``
	 *Optional*

	 If set, all namespace prefixes for the namespace specified are stripped from files and filenames

``-o namespace_tokenize NAMESPACETOKENIZE``
	 *Optional*

	 If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject

``-o check_only CHECKONLY``
	 *Optional*

	 If True, performs a test deployment (validation) of components without saving the components in the target org

``-o test_level TESTLEVEL``
	 *Optional*

	 Specifies which tests are run as part of a deployment. Valid values: NoTestRun, RunLocalTests, RunAllTestsInOrg, RunSpecifiedTests.

``-o specified_tests SPECIFIEDTESTS``
	 *Optional*

	 Comma-separated list of test classes to run upon deployment. Applies only with test_level set to RunSpecifiedTests.

``-o static_resource_path STATICRESOURCEPATH``
	 *Optional*

	 The path where decompressed static resources are stored.  Any subdirectories found will be zipped and added to the staticresources directory of the build.

``-o namespaced_org NAMESPACEDORG``
	 *Optional*

	 If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.

``-o clean_meta_xml CLEANMETAXML``
	 *Optional*

	 Defaults to True which strips the <packageVersions/> element from all meta.xml files.  The packageVersion element gets added automatically by the target org and is set to whatever version is installed in the org.  To disable this, set this option to False

deploy_post
===========

**Description:** Deploys all metadata bundles under unpackaged/post/

**Class:** cumulusci.tasks.salesforce.DeployBundles

Command Syntax
------------------------------------------

``$ cci task run deploy_post``


Options
------------------------------------------


``-o path PATH``
	 *Required*

	 The path to the parent directory containing the metadata bundles directories

	 Default: unpackaged/post

``-o unmanaged UNMANAGED``
	 *Optional*

	 If True, changes namespace_inject to replace tokens with a blank string

	 Default: True

``-o namespace_inject NAMESPACEINJECT``
	 *Optional*

	 If set, the namespace tokens in files and filenames are replaced with the namespace's prefix

	 Default: $project_config.project__package__namespace

``-o namespace_strip NAMESPACESTRIP``
	 *Optional*

	 If set, all namespace prefixes for the namespace specified are stripped from files and filenames

``-o namespace_tokenize NAMESPACETOKENIZE``
	 *Optional*

	 If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject

``-o check_only CHECKONLY``
	 *Optional*

	 If True, performs a test deployment (validation) of components without saving the components in the target org

``-o test_level TESTLEVEL``
	 *Optional*

	 Specifies which tests are run as part of a deployment. Valid values: NoTestRun, RunLocalTests, RunAllTestsInOrg, RunSpecifiedTests.

``-o specified_tests SPECIFIEDTESTS``
	 *Optional*

	 Comma-separated list of test classes to run upon deployment. Applies only with test_level set to RunSpecifiedTests.

``-o static_resource_path STATICRESOURCEPATH``
	 *Optional*

	 The path where decompressed static resources are stored.  Any subdirectories found will be zipped and added to the staticresources directory of the build.

``-o namespaced_org NAMESPACEDORG``
	 *Optional*

	 If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.

``-o clean_meta_xml CLEANMETAXML``
	 *Optional*

	 Defaults to True which strips the <packageVersions/> element from all meta.xml files.  The packageVersion element gets added automatically by the target org and is set to whatever version is installed in the org.  To disable this, set this option to False

deploy_qa_config
================

**Description:** Deploys configuration for QA.

**Class:** cumulusci.tasks.salesforce.Deploy

Command Syntax
------------------------------------------

``$ cci task run deploy_qa_config``


Options
------------------------------------------


``-o path PATH``
	 *Required*

	 The path to the metadata source to be deployed

	 Default: unpackaged/config/qa

``-o unmanaged UNMANAGED``
	 *Optional*

	 If True, changes namespace_inject to replace tokens with a blank string

	 Default: True

``-o namespace_inject NAMESPACEINJECT``
	 *Optional*

	 If set, the namespace tokens in files and filenames are replaced with the namespace's prefix

	 Default: $project_config.project__package__namespace

``-o namespace_strip NAMESPACESTRIP``
	 *Optional*

	 If set, all namespace prefixes for the namespace specified are stripped from files and filenames

``-o namespace_tokenize NAMESPACETOKENIZE``
	 *Optional*

	 If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject

``-o check_only CHECKONLY``
	 *Optional*

	 If True, performs a test deployment (validation) of components without saving the components in the target org

``-o test_level TESTLEVEL``
	 *Optional*

	 Specifies which tests are run as part of a deployment. Valid values: NoTestRun, RunLocalTests, RunAllTestsInOrg, RunSpecifiedTests.

``-o specified_tests SPECIFIEDTESTS``
	 *Optional*

	 Comma-separated list of test classes to run upon deployment. Applies only with test_level set to RunSpecifiedTests.

``-o static_resource_path STATICRESOURCEPATH``
	 *Optional*

	 The path where decompressed static resources are stored.  Any subdirectories found will be zipped and added to the staticresources directory of the build.

``-o namespaced_org NAMESPACEDORG``
	 *Optional*

	 If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.

``-o clean_meta_xml CLEANMETAXML``
	 *Optional*

	 Defaults to True which strips the <packageVersions/> element from all meta.xml files.  The packageVersion element gets added automatically by the target org and is set to whatever version is installed in the org.  To disable this, set this option to False

dx
==

**Description:** Execute an arbitrary Salesforce DX command against an org. Use the 'command' option to specify the command, such as 'force:package:install'

**Class:** cumulusci.tasks.sfdx.SFDXOrgTask

Command Syntax
------------------------------------------

``$ cci task run dx``


Options
------------------------------------------


``-o command COMMAND``
	 *Required*

	 The full command to run with the sfdx cli.

``-o extra EXTRA``
	 *Optional*

	 Append additional options to the command

dx_convert_to
=============

**Description:** Converts src directory metadata format into sfdx format under force-app

**Class:** cumulusci.tasks.sfdx.SFDXBaseTask

Command Syntax
------------------------------------------

``$ cci task run dx_convert_to``


Options
------------------------------------------


``-o command COMMAND``
	 *Required*

	 The full command to run with the sfdx cli.

	 Default: force:mdapi:convert -r src

``-o extra EXTRA``
	 *Optional*

	 Append additional options to the command

dx_convert_from
===============

**Description:** Converts force-app directory in sfdx format into metadata format under src

**Class:** cumulusci.tasks.sfdx.SFDXBaseTask

Command Syntax
------------------------------------------

``$ cci task run dx_convert_from``


Options
------------------------------------------


``-o command COMMAND``
	 *Required*

	 The full command to run with the sfdx cli.

	 Default: force:source:convert -d src

``-o extra EXTRA``
	 *Optional*

	 Append additional options to the command

dx_pull
=======

**Description:** Uses sfdx to pull from a scratch org into the force-app directory

**Class:** cumulusci.tasks.sfdx.SFDXOrgTask

Command Syntax
------------------------------------------

``$ cci task run dx_pull``


Options
------------------------------------------


``-o command COMMAND``
	 *Required*

	 The full command to run with the sfdx cli.

	 Default: force:source:pull

``-o extra EXTRA``
	 *Optional*

	 Append additional options to the command

dx_push
=======

**Description:** Uses sfdx to push the force-app directory metadata into a scratch org

**Class:** cumulusci.tasks.sfdx.SFDXOrgTask

Command Syntax
------------------------------------------

``$ cci task run dx_push``


Options
------------------------------------------


``-o command COMMAND``
	 *Required*

	 The full command to run with the sfdx cli.

	 Default: force:source:push

``-o extra EXTRA``
	 *Optional*

	 Append additional options to the command

ensure_record_types
===================

**Description:** Ensure that a default Record Type is extant on the given standard sObject (custom objects are not supported). If Record Types are already present, do nothing.

**Class:** cumulusci.tasks.salesforce.EnsureRecordTypes

Command Syntax
------------------------------------------

``$ cci task run ensure_record_types``


Options
------------------------------------------


``-o record_type_developer_name RECORDTYPEDEVELOPERNAME``
	 *Required*

	 The Developer Name of the Record Type (unique).  Must contain only alphanumeric characters and underscores.

	 Default: Default

``-o record_type_label RECORDTYPELABEL``
	 *Required*

	 The Label of the Record Type.

	 Default: Default

``-o sobject SOBJECT``
	 *Required*

	 The sObject on which to deploy the Record Type and optional Business Process.

execute_anon
============

**Description:** Execute anonymous apex via the tooling api.

**Class:** cumulusci.tasks.apex.anon.AnonymousApexTask

Use the `apex` option to run a string of anonymous Apex.
Use the `path` option to run anonymous Apex from a file.
Or use both to concatenate the string to the file contents.

Command Syntax
------------------------------------------

``$ cci task run execute_anon``


Options
------------------------------------------


``-o path PATH``
	 *Optional*

	 The path to an Apex file to run.

``-o apex APEX``
	 *Optional*

	 A string of Apex to run (after the file, if specified).

``-o managed MANAGED``
	 *Optional*

	 If True, will insert the project's namespace prefix.  Defaults to False or no namespace.

``-o namespaced NAMESPACED``
	 *Optional*

	 If True, the tokens %%%NAMESPACED_RT%%% and %%%namespaced%%% will get replaced with the namespace prefix for Record Types.

``-o param1 PARAM1``
	 *Optional*

	 Parameter to pass to the Apex. Use as %%%PARAM_1%%% in the Apex code.Defaults to an empty value.

``-o param2 PARAM2``
	 *Optional*

	 Parameter to pass to the Apex. Use as %%%PARAM_2%%% in the Apex code.Defaults to an empty value.

generate_data_dictionary
========================

**Description:** Create a data dictionary for the project in CSV format.

**Class:** cumulusci.tasks.datadictionary.GenerateDataDictionary

Generate a data dictionary for the project by walking all GitHub releases.
The data dictionary is output as two CSV files.
One, in `object_path`, includes the Object Name, Object Label, and Version Introduced,
with one row per packaged object.
The other, in `field_path`, includes Object Name, Field Name, Field Label, Field Type,
Valid Picklist Values (if any) or a Lookup referenced table (if any), Version Introduced.
Both MDAPI and SFDX format releases are supported. However, only force-app/main/default
is processed for SFDX projects.

Command Syntax
------------------------------------------

``$ cci task run generate_data_dictionary``


Options
------------------------------------------


``-o object_path OBJECTPATH``
	 *Optional*

	 Path to a CSV file to contain an sObject-level data dictionary.

``-o field_path FIELDPATH``
	 *Optional*

	 Path to a CSV file to contain an field-level data dictionary.

``-o include_dependencies INCLUDEDEPENDENCIES``
	 *Optional*

	 Process all of the GitHub dependencies of this project and include their schema in the data dictionary.

``-o additional_dependencies ADDITIONALDEPENDENCIES``
	 *Optional*

	 Include schema from additional GitHub repositories that are not explicit dependencies of this project to build a unified data dictionary. Specify as a list of dicts as in project__dependencies in cumulusci.yml. Note: only repository dependencies are supported.

generate_and_load_from_yaml
===========================

**Description:** None

**Class:** cumulusci.tasks.bulkdata.generate_and_load_data_from_yaml.GenerateAndLoadDataFromYaml

Command Syntax
------------------------------------------

``$ cci task run generate_and_load_from_yaml``


Options
------------------------------------------


``-o data_generation_task DATAGENERATIONTASK``
	 *Required*

	 Fully qualified class path of a task to generate the data. Look at cumulusci.tasks.bulkdata.tests.dummy_data_factory to learn how to write them.

``-o generator_yaml GENERATORYAML``
	 *Required*

	 A generator YAML file to use

``-o num_records NUMRECORDS``
	 *Optional*

	 How many records to generate: total number of opportunities.

``-o num_records_tablename NUMRECORDSTABLENAME``
	 *Optional*

	 A string representing which table to count records in.

``-o batch_size BATCHSIZE``
	 *Optional*

	 How many records to create and load at a time.

``-o data_generation_options DATAGENERATIONOPTIONS``
	 *Optional*

	 Options to pass to the data generator.

``-o vars VARS``
	 *Optional*

	 Pass values to override options in the format VAR1:foo,VAR2:bar

``-o replace_database REPLACEDATABASE``
	 *Optional*

	 Confirmation that it is okay to delete the data in database_url

``-o working_directory WORKINGDIRECTORY``
	 *Optional*

	 Default path for temporary / working files

``-o database_url DATABASEURL``
	 *Optional*

	 A path to put a copy of the sqlite database (for debugging)

``-o mapping MAPPING``
	 *Optional*

	 A mapping YAML file to use

``-o start_step STARTSTEP``
	 *Optional*

	 If specified, skip steps before this one in the mapping

``-o sql_path SQLPATH``
	 *Optional*

	 If specified, a database will be created from an SQL script at the provided path

``-o ignore_row_errors IGNOREROWERRORS``
	 *Optional*

	 If True, allow the load to continue even if individual rows fail to load.

``-o reset_oids RESETOIDS``
	 *Optional*

	 If True (the default), and the _sf_ids tables exist, reset them before continuing.

``-o bulk_mode BULKMODE``
	 *Optional*

	 Set to Serial to force serial mode on all jobs. Parallel is the default.

``-o inject_namespaces INJECTNAMESPACES``
	 *Optional*

	 If True, the package namespace prefix will be automatically added to objects and fields for which it is present in the org. Defaults to True.

``-o drop_missing_schema DROPMISSINGSCHEMA``
	 *Optional*

	 Set to True to skip any missing objects or fields instead of stopping with an error.

``-o generate_mapping_file GENERATEMAPPINGFILE``
	 *Optional*

	 A path to put a mapping file inferred from the generator_yaml

``-o continuation_file CONTINUATIONFILE``
	 *Optional*

	 YAML file generated by Snowfakery representing next steps for data generation

``-o generate_continuation_file GENERATECONTINUATIONFILE``
	 *Optional*

	 Path for Snowfakery to put its next continuation file

get_installed_packages
======================

**Description:** Retrieves a list of the currently installed managed package namespaces and their versions

**Class:** cumulusci.tasks.preflight.packages.GetInstalledPackages

Command Syntax
------------------------------------------

``$ cci task run get_installed_packages``



get_available_licenses
======================

**Description:** Retrieves a list of the currently available license definition keys

**Class:** cumulusci.tasks.preflight.licenses.GetAvailableLicenses

Command Syntax
------------------------------------------

``$ cci task run get_available_licenses``



get_available_permission_set_licenses
=====================================

**Description:** Retrieves a list of the currently available Permission Set License definition keys

**Class:** cumulusci.tasks.preflight.licenses.GetAvailablePermissionSetLicenses

Command Syntax
------------------------------------------

``$ cci task run get_available_permission_set_licenses``



github_parent_pr_notes
======================

**Description:** Merges the description of a child pull request to the respective parent's pull request (if one exists).

**Class:** cumulusci.tasks.release_notes.task.ParentPullRequestNotes

Aggregate change notes from child pull request(s) to its corresponding
parent's pull request.

When given the branch_name option, this task will: (1) check if the base branch
of the corresponding pull request starts with the feature branch prefix and if so (2) attempt
to query for a pull request corresponding to this parent feature branch. (3) if a pull request
isn't found, the task exits and no actions are taken.

If the build_notes_label is present on the pull request, then all notes from the
child pull request are aggregated into the parent pull request. if the build_notes_label
is not detected on the parent pull request then a link to the child pull request
is placed under the "Unaggregated Pull Requests" header.

When given the parent_branch_name option, this task will query for a corresponding pull request.
If a pull request is not found, the task exits. If a pull request is found, then all notes
from child pull requests are re-aggregated and the body of the parent is replaced entirely.

Command Syntax
------------------------------------------

``$ cci task run github_parent_pr_notes``


Options
------------------------------------------


``-o branch_name BRANCHNAME``
	 *Required*

	 Name of branch to check for parent status, and if so, reaggregate change notes from child branches.

``-o build_notes_label BUILDNOTESLABEL``
	 *Required*

	 Name of the label that indicates that change notes on parent pull requests should be reaggregated when a child branch pull request is created.

``-o force FORCE``
	 *Optional*

	 force rebuilding of change notes from child branches in the given branch.

github_clone_tag
================

**Description:** Clones a github tag under a new name.

**Class:** cumulusci.tasks.github.CloneTag

Command Syntax
------------------------------------------

``$ cci task run github_clone_tag``


Options
------------------------------------------


``-o src_tag SRCTAG``
	 *Required*

	 The source tag to clone.  Ex: beta/1.0-Beta_2

``-o tag TAG``
	 *Required*

	 The new tag to create by cloning the src tag.  Ex: release/1.0

github_master_to_feature
========================

**Description:** Merges the latest commit on the main branch into all open feature branches

**Class:** cumulusci.tasks.github.MergeBranch

Command Syntax
------------------------------------------

``$ cci task run github_master_to_feature``


Options
------------------------------------------


``-o commit COMMIT``
	 *Optional*

	 The commit to merge into feature branches.  Defaults to the current head commit.

``-o source_branch SOURCEBRANCH``
	 *Optional*

	 The source branch to merge from.  Defaults to project__git__default_branch.

``-o branch_prefix BRANCHPREFIX``
	 *Optional*

	 The prefix of branches that should receive the merge.  Defaults to project__git__prefix_feature

``-o children_only CHILDRENONLY``
	 *Optional*

	 If True, merge will only be done to child branches.  This assumes source branch is a parent feature branch.  Defaults to False

github_parent_to_children
=========================

**Description:** Merges the latest commit on a parent feature branch into all child feature branches

**Class:** cumulusci.tasks.github.MergeBranch

Command Syntax
------------------------------------------

``$ cci task run github_parent_to_children``


Options
------------------------------------------


``-o commit COMMIT``
	 *Optional*

	 The commit to merge into feature branches.  Defaults to the current head commit.

``-o source_branch SOURCEBRANCH``
	 *Optional*

	 The source branch to merge from.  Defaults to project__git__default_branch.

	 Default: $project_config.repo_branch

``-o branch_prefix BRANCHPREFIX``
	 *Optional*

	 The prefix of branches that should receive the merge.  Defaults to project__git__prefix_feature

``-o children_only CHILDRENONLY``
	 *Optional*

	 If True, merge will only be done to child branches.  This assumes source branch is a parent feature branch.  Defaults to False

	 Default: True

github_copy_subtree
===================

**Description:** Copies one or more subtrees from the project repository for a given release to a target repository, with the option to include release notes.

**Class:** cumulusci.tasks.github.publish.PublishSubtree

Command Syntax
------------------------------------------

``$ cci task run github_copy_subtree``


Options
------------------------------------------


``-o repo_url REPOURL``
	 *Required*

	 The url to the public repo

``-o branch BRANCH``
	 *Required*

	 The branch to update in the target repo

``-o version VERSION``
	 *Required*

	 The version number to release.  Also supports latest and latest_beta to look up the latest releases.

``-o include INCLUDE``
	 *Optional*

	 A list of paths from repo root to include. Directories must end with a trailing slash.

``-o create_release CREATERELEASE``
	 *Optional*

	 If True, create a release in the public repo.  Defaults to True

``-o release_body RELEASEBODY``
	 *Optional*

	 If True, the entire release body will be published to the public repo.  Defaults to False

``-o dry_run DRYRUN``
	 *Optional*

	 If True, skip creating Github data.  Defaults to False

github_pull_requests
====================

**Description:** Lists open pull requests in project Github repository

**Class:** cumulusci.tasks.github.PullRequests

Command Syntax
------------------------------------------

``$ cci task run github_pull_requests``



github_release
==============

**Description:** Creates a Github release for a given managed package version number

**Class:** cumulusci.tasks.github.CreateRelease

Command Syntax
------------------------------------------

``$ cci task run github_release``


Options
------------------------------------------


``-o version VERSION``
	 *Required*

	 The managed package version number.  Ex: 1.2

``-o message MESSAGE``
	 *Optional*

	 The message to attach to the created git tag

``-o dependencies DEPENDENCIES``
	 *Optional*

	 List of dependencies to record in the tag message.

``-o commit COMMIT``
	 *Optional*

	 Override the commit used to create the release. Defaults to the current local HEAD commit

github_release_notes
====================

**Description:** Generates release notes by parsing pull request bodies of merged pull requests between two tags

**Class:** cumulusci.tasks.release_notes.task.GithubReleaseNotes

Command Syntax
------------------------------------------

``$ cci task run github_release_notes``


Options
------------------------------------------


``-o tag TAG``
	 *Required*

	 The tag to generate release notes for. Ex: release/1.2

``-o last_tag LASTTAG``
	 *Optional*

	 Override the last release tag. This is useful to generate release notes if you skipped one or more releases.

``-o link_pr LINKPR``
	 *Optional*

	 If True, insert link to source pull request at end of each line.

``-o publish PUBLISH``
	 *Optional*

	 Publish to GitHub release if True (default=False)

``-o include_empty INCLUDEEMPTY``
	 *Optional*

	 If True, include links to PRs that have no release notes (default=False)

``-o version_id VERSIONID``
	 *Optional*

	 The package version id used by the InstallLinksParser to add install urls

github_release_report
=====================

**Description:** Parses GitHub release notes to report various info

**Class:** cumulusci.tasks.github.ReleaseReport

Command Syntax
------------------------------------------

``$ cci task run github_release_report``


Options
------------------------------------------


``-o date_start DATESTART``
	 *Optional*

	 Filter out releases created before this date (YYYY-MM-DD)

``-o date_end DATEEND``
	 *Optional*

	 Filter out releases created after this date (YYYY-MM-DD)

``-o include_beta INCLUDEBETA``
	 *Optional*

	 Include beta releases in report [default=False]

``-o print PRINT``
	 *Optional*

	 Print info to screen as JSON [default=False]

install_managed
===============

**Description:** Install the latest managed production release

**Class:** cumulusci.tasks.salesforce.InstallPackageVersion

Command Syntax
------------------------------------------

``$ cci task run install_managed``


Options
------------------------------------------


``-o namespace NAMESPACE``
	 *Required*

	 The namespace of the package to install.  Defaults to project__package__namespace

``-o version VERSION``
	 *Required*

	 The version of the package to install.  "latest" and "latest_beta" can be used to trigger lookup via Github Releases on the repository.

	 Default: latest

``-o name NAME``
	 *Optional*

	 The name of the package to install.  Defaults to project__package__name_managed

``-o activateRSS ACTIVATERSS``
	 *Optional*

	 If True, preserve the isActive state of Remote Site Settings and Content Security Policy in the package. Default: False.

	 Default: True

``-o password PASSWORD``
	 *Optional*

	 The package password. Optional.

``-o retries RETRIES``
	 *Optional*

	 Number of retries (default=5)

``-o retry_interval RETRYINTERVAL``
	 *Optional*

	 Number of seconds to wait before the next retry (default=5),

``-o retry_interval_add RETRYINTERVALADD``
	 *Optional*

	 Number of seconds to add before each retry (default=30),

``-o security_type SECURITYTYPE``
	 *Optional*

	 Which users to install package for (FULL = all users, NONE = admins only)

install_managed_beta
====================

**Description:** Installs the latest managed beta release

**Class:** cumulusci.tasks.salesforce.InstallPackageVersion

Command Syntax
------------------------------------------

``$ cci task run install_managed_beta``


Options
------------------------------------------


``-o namespace NAMESPACE``
	 *Required*

	 The namespace of the package to install.  Defaults to project__package__namespace

``-o version VERSION``
	 *Required*

	 The version of the package to install.  "latest" and "latest_beta" can be used to trigger lookup via Github Releases on the repository.

	 Default: latest_beta

``-o name NAME``
	 *Optional*

	 The name of the package to install.  Defaults to project__package__name_managed

``-o activateRSS ACTIVATERSS``
	 *Optional*

	 If True, preserve the isActive state of Remote Site Settings and Content Security Policy in the package. Default: False.

	 Default: True

``-o password PASSWORD``
	 *Optional*

	 The package password. Optional.

``-o retries RETRIES``
	 *Optional*

	 Number of retries (default=5)

``-o retry_interval RETRYINTERVAL``
	 *Optional*

	 Number of seconds to wait before the next retry (default=5),

``-o retry_interval_add RETRYINTERVALADD``
	 *Optional*

	 Number of seconds to add before each retry (default=30),

``-o security_type SECURITYTYPE``
	 *Optional*

	 Which users to install package for (FULL = all users, NONE = admins only)

list_communities
================

**Description:** Lists Communities for the current org using the Connect API.

**Class:** cumulusci.tasks.salesforce.ListCommunities

Lists Communities for the current org via the Connect API.

Command Syntax
------------------------------------------

``$ cci task run list_communities``



list_community_templates
========================

**Description:** Prints the Community Templates available to the current org

**Class:** cumulusci.tasks.salesforce.ListCommunityTemplates

Lists Salesforce Community templates available for the current org via the Connect API.

Command Syntax
------------------------------------------

``$ cci task run list_community_templates``



list_metadata_types
===================

**Description:** Prints the metadata types in a project

**Class:** cumulusci.tasks.util.ListMetadataTypes

Command Syntax
------------------------------------------

``$ cci task run list_metadata_types``


Options
------------------------------------------


``-o package_xml PACKAGEXML``
	 *Optional*

	 The project package.xml file. Defaults to <project_root>/src/package.xml

meta_xml_apiversion
===================

**Description:** Set the API version in ``*meta.xml`` files

**Class:** cumulusci.tasks.metaxml.UpdateApi

Command Syntax
------------------------------------------

``$ cci task run meta_xml_apiversion``


Options
------------------------------------------


``-o version VERSION``
	 *Required*

	 API version number e.g. 37.0

``-o dir DIR``
	 *Optional*

	 Base directory to search for ``*-meta.xml`` files

meta_xml_dependencies
=====================

**Description:** Set the version for dependent packages

**Class:** cumulusci.tasks.metaxml.UpdateDependencies

Command Syntax
------------------------------------------

``$ cci task run meta_xml_dependencies``


Options
------------------------------------------


``-o dir DIR``
	 *Optional*

	 Base directory to search for ``*-meta.xml`` files

metadeploy_publish
==================

**Description:** Publish a release to the MetaDeploy web installer

**Class:** cumulusci.tasks.metadeploy.Publish

Command Syntax
------------------------------------------

``$ cci task run metadeploy_publish``


Options
------------------------------------------


``-o tag TAG``
	 *Optional*

	 Name of the git tag to publish

``-o commit COMMIT``
	 *Optional*

	 Commit hash to publish

``-o plan PLAN``
	 *Optional*

	 Name of the plan(s) to publish. This refers to the `plans` section of cumulusci.yml. By default, all plans will be published.

``-o dry_run DRYRUN``
	 *Optional*

	 If True, print steps without publishing.

``-o publish PUBLISH``
	 *Optional*

	 If True, set is_listed to True on the version. Default: False

``-o labels_path LABELSPATH``
	 *Optional*

	 Path to a folder containing translations.

org_settings
============

**Description:** Apply org settings from a scratch org definition file

**Class:** cumulusci.tasks.salesforce.org_settings.DeployOrgSettings

Command Syntax
------------------------------------------

``$ cci task run org_settings``


Options
------------------------------------------


``-o definition_file DEFINITIONFILE``
	 *Optional*

	 sfdx scratch org definition file

``-o api_version APIVERSION``
	 *Optional*

	 API version used to deploy the settings

publish_community
=================

**Description:** Publishes a Community in the target org using the Connect API

**Class:** cumulusci.tasks.salesforce.PublishCommunity

Publish a Salesforce Community via the Connect API. Warning: This does not work with the Community Template 'VF Template' due to an existing bug in the API.

Command Syntax
------------------------------------------

``$ cci task run publish_community``


Options
------------------------------------------


``-o name NAME``
	 *Optional*

	 The name of the Community to publish.

``-o community_id COMMUNITYID``
	 *Optional*

	 The id of the Community to publish.

push_all
========

**Description:** Schedules a push upgrade of a package version to all subscribers

**Class:** cumulusci.tasks.push.tasks.SchedulePushOrgQuery

Command Syntax
------------------------------------------

``$ cci task run push_all``


Options
------------------------------------------


``-o version VERSION``
	 *Required*

	 The managed package version to push

``-o subscriber_where SUBSCRIBERWHERE``
	 *Optional*

	 A SOQL style WHERE clause for filtering PackageSubscriber objects. Ex: OrgType = 'Sandbox'

``-o min_version MINVERSION``
	 *Optional*

	 If set, no subscriber with a version lower than min_version will be selected for push

``-o namespace NAMESPACE``
	 *Optional*

	 The managed package namespace to push. Defaults to project__package__namespace.

``-o start_time STARTTIME``
	 *Optional*

	 Set the start time (UTC) to queue a future push. Ex: 2016-10-19T10:00

push_list
=========

**Description:** Schedules a push upgrade of a package version to all orgs listed in the specified file

**Class:** cumulusci.tasks.push.tasks.SchedulePushOrgList

Command Syntax
------------------------------------------

``$ cci task run push_list``


Options
------------------------------------------


``-o orgs ORGS``
	 *Required*

	 The path to a file containing one OrgID per line.

``-o version VERSION``
	 *Required*

	 The managed package version to push

``-o namespace NAMESPACE``
	 *Optional*

	 The managed package namespace to push. Defaults to project__package__namespace.

``-o start_time STARTTIME``
	 *Optional*

	 Set the start time (UTC) to queue a future push. Ex: 2016-10-19T10:00

``-o batch_size BATCHSIZE``
	 *Optional*

	 Break pull requests into batches of this many orgs. Defaults to 200.

push_qa
=======

**Description:** Schedules a push upgrade of a package version to all orgs listed in push/orgs_qa.txt

**Class:** cumulusci.tasks.push.tasks.SchedulePushOrgList

Command Syntax
------------------------------------------

``$ cci task run push_qa``


Options
------------------------------------------


``-o orgs ORGS``
	 *Required*

	 The path to a file containing one OrgID per line.

	 Default: push/orgs_qa.txt

``-o version VERSION``
	 *Required*

	 The managed package version to push

``-o namespace NAMESPACE``
	 *Optional*

	 The managed package namespace to push. Defaults to project__package__namespace.

``-o start_time STARTTIME``
	 *Optional*

	 Set the start time (UTC) to queue a future push. Ex: 2016-10-19T10:00

``-o batch_size BATCHSIZE``
	 *Optional*

	 Break pull requests into batches of this many orgs. Defaults to 200.

push_sandbox
============

**Description:** Schedules a push upgrade of a package version to all subscribers

**Class:** cumulusci.tasks.push.tasks.SchedulePushOrgQuery

Command Syntax
------------------------------------------

``$ cci task run push_sandbox``


Options
------------------------------------------


``-o version VERSION``
	 *Required*

	 The managed package version to push

``-o subscriber_where SUBSCRIBERWHERE``
	 *Optional*

	 A SOQL style WHERE clause for filtering PackageSubscriber objects. Ex: OrgType = 'Sandbox'

	 Default: OrgType = 'Sandbox'

``-o min_version MINVERSION``
	 *Optional*

	 If set, no subscriber with a version lower than min_version will be selected for push

``-o namespace NAMESPACE``
	 *Optional*

	 The managed package namespace to push. Defaults to project__package__namespace.

``-o start_time STARTTIME``
	 *Optional*

	 Set the start time (UTC) to queue a future push. Ex: 2016-10-19T10:00

push_trial
==========

**Description:** Schedules a push upgrade of a package version to Trialforce Template orgs listed in push/orgs_trial.txt

**Class:** cumulusci.tasks.push.tasks.SchedulePushOrgList

Command Syntax
------------------------------------------

``$ cci task run push_trial``


Options
------------------------------------------


``-o orgs ORGS``
	 *Required*

	 The path to a file containing one OrgID per line.

	 Default: push/orgs_trial.txt

``-o version VERSION``
	 *Required*

	 The managed package version to push

``-o namespace NAMESPACE``
	 *Optional*

	 The managed package namespace to push. Defaults to project__package__namespace.

``-o start_time STARTTIME``
	 *Optional*

	 Set the start time (UTC) to queue a future push. Ex: 2016-10-19T10:00

``-o batch_size BATCHSIZE``
	 *Optional*

	 Break pull requests into batches of this many orgs. Defaults to 200.

push_failure_report
===================

**Description:** Produce a CSV report of the failed and otherwise anomalous push jobs.

**Class:** cumulusci.tasks.push.pushfails.ReportPushFailures

Command Syntax
------------------------------------------

``$ cci task run push_failure_report``


Options
------------------------------------------


``-o request_id REQUESTID``
	 *Required*

	 PackagePushRequest ID for the request you need to report on.

``-o result_file RESULTFILE``
	 *Optional*

	 Path to write a CSV file with the results. Defaults to 'push_fails.csv'.

``-o ignore_errors IGNOREERRORS``
	 *Optional*

	 List of ErrorTitle and ErrorType values to omit from the report

	 Default: ['Salesforce Subscription Expired', 'Package Uninstalled']

query
=====

**Description:** Queries the connected org

**Class:** cumulusci.tasks.salesforce.SOQLQuery

Command Syntax
------------------------------------------

``$ cci task run query``


Options
------------------------------------------


``-o object OBJECT``
	 *Required*

	 The object to query

``-o query QUERY``
	 *Required*

	 A valid bulk SOQL query for the object

``-o result_file RESULTFILE``
	 *Required*

	 The name of the csv file to write the results to

retrieve_packaged
=================

**Description:** Retrieves the packaged metadata from the org

**Class:** cumulusci.tasks.salesforce.RetrievePackaged

Command Syntax
------------------------------------------

``$ cci task run retrieve_packaged``


Options
------------------------------------------


``-o path PATH``
	 *Required*

	 The path to write the retrieved metadata

	 Default: packaged

``-o package PACKAGE``
	 *Required*

	 The package name to retrieve.  Defaults to project__package__name

``-o unmanaged UNMANAGED``
	 *Optional*

	 If True, changes namespace_inject to replace tokens with a blank string

``-o namespace_inject NAMESPACEINJECT``
	 *Optional*

	 If set, the namespace tokens in files and filenames are replaced with the namespace's prefix

``-o namespace_strip NAMESPACESTRIP``
	 *Optional*

	 If set, all namespace prefixes for the namespace specified are stripped from files and filenames

``-o namespace_tokenize NAMESPACETOKENIZE``
	 *Optional*

	 If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject

``-o namespaced_org NAMESPACEDORG``
	 *Optional*

	 If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.

``-o api_version APIVERSION``
	 *Optional*

	 Override the default api version for the retrieve. Defaults to project__package__api_version

retrieve_src
============

**Description:** Retrieves the packaged metadata into the src directory

**Class:** cumulusci.tasks.salesforce.RetrievePackaged

Command Syntax
------------------------------------------

``$ cci task run retrieve_src``


Options
------------------------------------------


``-o path PATH``
	 *Required*

	 The path to write the retrieved metadata

	 Default: src

``-o package PACKAGE``
	 *Required*

	 The package name to retrieve.  Defaults to project__package__name

``-o unmanaged UNMANAGED``
	 *Optional*

	 If True, changes namespace_inject to replace tokens with a blank string

``-o namespace_inject NAMESPACEINJECT``
	 *Optional*

	 If set, the namespace tokens in files and filenames are replaced with the namespace's prefix

``-o namespace_strip NAMESPACESTRIP``
	 *Optional*

	 If set, all namespace prefixes for the namespace specified are stripped from files and filenames

``-o namespace_tokenize NAMESPACETOKENIZE``
	 *Optional*

	 If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject

``-o namespaced_org NAMESPACEDORG``
	 *Optional*

	 If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.

``-o api_version APIVERSION``
	 *Optional*

	 Override the default api version for the retrieve. Defaults to project__package__api_version

retrieve_unpackaged
===================

**Description:** Retrieve the contents of a package.xml file.

**Class:** cumulusci.tasks.salesforce.RetrieveUnpackaged

Command Syntax
------------------------------------------

``$ cci task run retrieve_unpackaged``


Options
------------------------------------------


``-o path PATH``
	 *Required*

	 The path to write the retrieved metadata

``-o package_xml PACKAGEXML``
	 *Required*

	 The path to a package.xml manifest to use for the retrieve.

``-o unmanaged UNMANAGED``
	 *Optional*

	 If True, changes namespace_inject to replace tokens with a blank string

``-o namespace_inject NAMESPACEINJECT``
	 *Optional*

	 If set, the namespace tokens in files and filenames are replaced with the namespace's prefix

``-o namespace_strip NAMESPACESTRIP``
	 *Optional*

	 If set, all namespace prefixes for the namespace specified are stripped from files and filenames

``-o namespace_tokenize NAMESPACETOKENIZE``
	 *Optional*

	 If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject

``-o namespaced_org NAMESPACEDORG``
	 *Optional*

	 If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.

``-o api_version APIVERSION``
	 *Optional*

	 Override the default api version for the retrieve. Defaults to project__package__api_version

list_changes
============

**Description:** List the changes from a scratch org

**Class:** cumulusci.tasks.salesforce.sourcetracking.ListChanges

Command Syntax
------------------------------------------

``$ cci task run list_changes``


Options
------------------------------------------


``-o include INCLUDE``
	 *Optional*

	 A comma-separated list of strings. Components will be included if one of these strings is part of either the metadata type or name. Example: ``-o include CustomField,Admin`` matches both ``CustomField: Favorite_Color__c`` and ``Profile: Admin``

``-o types TYPES``
	 *Optional*

	 A comma-separated list of metadata types to include.

``-o exclude EXCLUDE``
	 *Optional*

	 Exclude changed components matching this string.

``-o snapshot SNAPSHOT``
	 *Optional*

	 If True, all matching items will be set to be ignored at their current revision number.  This will exclude them from the results unless a new edit is made.

retrieve_changes
================

**Description:** Retrieve changed components from a scratch org

**Class:** cumulusci.tasks.salesforce.sourcetracking.RetrieveChanges

Command Syntax
------------------------------------------

``$ cci task run retrieve_changes``


Options
------------------------------------------


``-o include INCLUDE``
	 *Optional*

	 A comma-separated list of strings. Components will be included if one of these strings is part of either the metadata type or name. Example: ``-o include CustomField,Admin`` matches both ``CustomField: Favorite_Color__c`` and ``Profile: Admin``

``-o types TYPES``
	 *Optional*

	 A comma-separated list of metadata types to include.

``-o exclude EXCLUDE``
	 *Optional*

	 Exclude changed components matching this string.

``-o snapshot SNAPSHOT``
	 *Optional*

	 If True, all matching items will be set to be ignored at their current revision number.  This will exclude them from the results unless a new edit is made.

``-o path PATH``
	 *Optional*

	 The path to write the retrieved metadata

``-o api_version APIVERSION``
	 *Optional*

	 Override the default api version for the retrieve. Defaults to project__package__api_version

``-o namespace_tokenize NAMESPACETOKENIZE``
	 *Optional*

	 If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject

retrieve_qa_config
==================

**Description:** Retrieves the current changes in the scratch org into unpackaged/config/qa

**Class:** cumulusci.tasks.salesforce.sourcetracking.RetrieveChanges

Command Syntax
------------------------------------------

``$ cci task run retrieve_qa_config``


Options
------------------------------------------


``-o include INCLUDE``
	 *Optional*

	 A comma-separated list of strings. Components will be included if one of these strings is part of either the metadata type or name. Example: ``-o include CustomField,Admin`` matches both ``CustomField: Favorite_Color__c`` and ``Profile: Admin``

``-o types TYPES``
	 *Optional*

	 A comma-separated list of metadata types to include.

``-o exclude EXCLUDE``
	 *Optional*

	 Exclude changed components matching this string.

``-o snapshot SNAPSHOT``
	 *Optional*

	 If True, all matching items will be set to be ignored at their current revision number.  This will exclude them from the results unless a new edit is made.

``-o path PATH``
	 *Optional*

	 The path to write the retrieved metadata

	 Default: unpackaged/config/qa

``-o api_version APIVERSION``
	 *Optional*

	 Override the default api version for the retrieve. Defaults to project__package__api_version

``-o namespace_tokenize NAMESPACETOKENIZE``
	 *Optional*

	 If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject

	 Default: $project_config.project__package__namespace

set_field_help_text
===================

**Description:** Sets specified fields' Help Text values.

**Class:** cumulusci.tasks.metadata_etl.help_text.SetFieldHelpText

Command Syntax
------------------------------------------

``$ cci task run set_field_help_text``


Options
------------------------------------------


``-o fields FIELDS``
	 *Required*

	 List of object fields to affect, in Object__c.Field__c form.

``-o overwrite OVERWRITE``
	 *Optional*

	 If set to True, overwrite any differing Help Text found on the field. By default, Help Text is set only if it is blank.

``-o api_names APINAMES``
	 *Optional*

	 List of API names of entities to affect

``-o managed MANAGED``
	 *Optional*

	 If False, changes namespace_inject to replace tokens with a blank string

``-o namespace_inject NAMESPACEINJECT``
	 *Optional*

	 If set, the namespace tokens in files and filenames are replaced with the namespace's prefix

	 Default: $project_config.project__package__namespace

``-o api_version APIVERSION``
	 *Optional*

	 Metadata API version to use, if not project__package__api_version.

snapshot_changes
================

**Description:** Tell SFDX source tracking to ignore previous changes in a scratch org

**Class:** cumulusci.tasks.salesforce.sourcetracking.SnapshotChanges

Command Syntax
------------------------------------------

``$ cci task run snapshot_changes``



revert_managed_src
==================

**Description:** Reverts the changes from create_managed_src

**Class:** cumulusci.tasks.metadata.managed_src.RevertManagedSrc

Command Syntax
------------------------------------------

``$ cci task run revert_managed_src``


Options
------------------------------------------


``-o path PATH``
	 *Required*

	 The path containing metadata to process for managed deployment

	 Default: src

``-o revert_path REVERTPATH``
	 *Required*

	 The path to copy the original metadata to for the revert call

	 Default: src.orig

revert_unmanaged_ee_src
=======================

**Description:** Reverts the changes from create_unmanaged_ee_src

**Class:** cumulusci.tasks.metadata.ee_src.RevertUnmanagedEESrc

Command Syntax
------------------------------------------

``$ cci task run revert_unmanaged_ee_src``


Options
------------------------------------------


``-o path PATH``
	 *Required*

	 The path containing metadata to process for managed deployment

	 Default: src

``-o revert_path REVERTPATH``
	 *Required*

	 The path to copy the original metadata to for the revert call

	 Default: src.orig

robot
=====

**Description:** Runs a Robot Framework test from a .robot file

**Class:** cumulusci.tasks.robotframework.Robot

Command Syntax
------------------------------------------

``$ cci task run robot``


Options
------------------------------------------


``-o suites SUITES``
	 *Required*

	 Paths to test case files/directories to be executed similarly as when running the robot command on the command line.  Defaults to "tests" to run all tests in the tests directory

	 Default: tests

``-o test TEST``
	 *Optional*

	 Run only tests matching name patterns.  Can be comma separated and use robot wildcards like *

``-o include INCLUDE``
	 *Optional*

	 Includes tests with a given tag

``-o exclude EXCLUDE``
	 *Optional*

	 Excludes tests with a given tag

``-o vars VARS``
	 *Optional*

	 Pass values to override variables in the format VAR1:foo,VAR2:bar

``-o xunit XUNIT``
	 *Optional*

	 Set an XUnit format output file for test results

``-o options OPTIONS``
	 *Optional*

	 A dictionary of options to robot.run method.  See docs here for format.  NOTE: There is no cci CLI support for this option since it requires a dictionary.  Use this option in the cumulusci.yml when defining custom tasks where you can easily create a dictionary in yaml.

``-o name NAME``
	 *Optional*

	 Sets the name of the top level test suite

``-o pdb PDB``
	 *Optional*

	 If true, run the Python debugger when tests fail.

``-o verbose VERBOSE``
	 *Optional*

	 If true, log each keyword as it runs.

``-o debug DEBUG``
	 *Optional*

	 If true, enable the `breakpoint` keyword to enable the robot debugger

``-o processes PROCESSES``
	 *Optional*

	 *experimental* Number of processes to use for running tests in parallel. If this value is set to a number larger than 1 the tests will run using the open source tool pabot rather than robotframework. For example, -o parallel 2 will run half of the tests in one process and half in another. If not provided, all tests will run in a single process using the standard robot test runner.

robot_libdoc
============

**Description:** Generates documentation for project keyword files

**Class:** cumulusci.tasks.robotframework.RobotLibDoc

Command Syntax
------------------------------------------

``$ cci task run robot_libdoc``


Options
------------------------------------------


``-o path PATH``
	 *Required*

	 The path to one or more keyword libraries to be documented. The path can be single a python file, a .robot file, a python module (eg: cumulusci.robotframework.Salesforce) or a comma separated list of any of those. Glob patterns are supported for filenames (eg: ``robot/SAL/doc/*PageObject.py``). The order of the files will be preserved in the generated documentation. The result of pattern expansion will be sorted

``-o output OUTPUT``
	 *Required*

	 The output file where the documentation will be written

	 Default: Keywords.html

``-o title TITLE``
	 *Optional*

	 A string to use as the title of the generated output

	 Default: $project_config.project__package__name

robot_lint
==========

**Description:** Static analysis tool for robot framework files

**Class:** cumulusci.tasks.robotframework.RobotLint

The robot_lint task performs static analysis on one or more .robot
and .resource files. Each line is parsed, and the result passed through
a series of rules. Rules can issue warnings or errors about each line.

If any errors are reported, the task will exit with a non-zero status.

When a rule has been violated, a line will appear on the output in
the following format:

*<severity>*: *<line>*, *<character>*: *<description>* (*<name>*)

- *<severity>* will be either W for warning or E for error
- *<line>* is the line number where the rule was triggered
- *<character>* is the character where the rule was triggered,
  or 0 if the rule applies to the whole line
- *<description>* is a short description of the issue
- *<name>* is the name of the rule that raised the issue

Note: the rule name can be used with the ignore, warning, error,
and configure options.

Some rules are configurable, and can be configured with the
`configure` option. This option takes a list of values in the form
*<rule>*:*<value>*,*<rule>*:*<value>*,etc.  For example, to set
the line length for the LineTooLong rule you can use '-o configure
LineTooLong:80'. If a rule is configurable, it will show the
configuration options in the documentation for that rule

The filename will be printed once before any errors or warnings
for that file. The filename is preceeded by `+`

Example Output::

    + example.robot
    W: 2, 0: No suite documentation (RequireSuiteDocumentation)
    E: 30, 0: No testcase documentation (RequireTestDocumentation)

To see a list of all configured rules, set the 'list' option to True:

    cci task run robot_lint -o list True


Command Syntax
------------------------------------------

``$ cci task run robot_lint``


Options
------------------------------------------


``-o configure CONFIGURE``
	 *Optional*

	 List of rule configuration values, in the form of rule:args.

``-o ignore IGNORE``
	 *Optional*

	 List of rules to ignore. Use 'all' to ignore all rules

``-o error ERROR``
	 *Optional*

	 List of rules to treat as errors. Use 'all' to affect all rules.

``-o warning WARNING``
	 *Optional*

	 List of rules to treat as warnings. Use 'all' to affect all rules.

``-o list LIST``
	 *Optional*

	 If option is True, print a list of known rules instead of processing files.

``-o path PATH``
	 *Optional*

	 The path to one or more files or folders. If the path includes wildcard characters, they will be expanded. If not provided, the default will be to process all files under robot/<project name>

robot_testdoc
=============

**Description:** Generates html documentation of your Robot test suite and writes to tests/test_suite.

**Class:** cumulusci.tasks.robotframework.RobotTestDoc

Command Syntax
------------------------------------------

``$ cci task run robot_testdoc``


Options
------------------------------------------


``-o path PATH``
	 *Required*

	 The path containing .robot test files

	 Default: tests

``-o output OUTPUT``
	 *Required*

	 The output html file where the documentation will be written

	 Default: tests/test_suites.html

run_tests
=========

**Description:** Runs all apex tests

**Class:** cumulusci.tasks.apex.testrunner.RunApexTests

Command Syntax
------------------------------------------

``$ cci task run run_tests``


Options
------------------------------------------


``-o test_name_match TESTNAMEMATCH``
	 *Required*

	 Pattern to find Apex test classes to run ("%" is wildcard).  Defaults to project__test__name_match from project config. Comma-separated list for multiple patterns.

``-o test_name_exclude TESTNAMEEXCLUDE``
	 *Optional*

	 Query to find Apex test classes to exclude ("%" is wildcard).  Defaults to project__test__name_exclude from project config. Comma-separated list for multiple patterns.

``-o namespace NAMESPACE``
	 *Optional*

	 Salesforce project namespace.  Defaults to project__package__namespace

``-o managed MANAGED``
	 *Optional*

	 If True, search for tests in the namespace only.  Defaults to False

``-o poll_interval POLLINTERVAL``
	 *Optional*

	 Seconds to wait between polling for Apex test results.

``-o junit_output JUNITOUTPUT``
	 *Optional*

	 File name for JUnit output.  Defaults to test_results.xml

``-o json_output JSONOUTPUT``
	 *Optional*

	 File name for json output.  Defaults to test_results.json

``-o retry_failures RETRYFAILURES``
	 *Optional*

	 A list of regular expression patterns to match against test failures. If failures match, the failing tests are retried in serial mode.

``-o retry_always RETRYALWAYS``
	 *Optional*

	 By default, all failures must match retry_failures to perform a retry. Set retry_always to True to retry all failed tests if any failure matches.

``-o required_org_code_coverage_percent REQUIREDORGCODECOVERAGEPERCENT``
	 *Optional*

	 Require at least X percent code coverage across the org following the test run.

``-o verbose VERBOSE``
	 *Optional*

	 By default, only failures get detailed output. Set verbose to True to see all passed test methods.

set_duplicate_rule_status
=========================

**Description:** Sets the active status of Duplicate Rules.

**Class:** cumulusci.tasks.metadata_etl.SetDuplicateRuleStatus

Command Syntax
------------------------------------------

``$ cci task run set_duplicate_rule_status``


Options
------------------------------------------


``-o active ACTIVE``
	 *Required*

	 Boolean value, set the Duplicate Rule to either active or inactive

``-o api_names APINAMES``
	 *Optional*

	 List of API names of entities to affect

``-o managed MANAGED``
	 *Optional*

	 If False, changes namespace_inject to replace tokens with a blank string

``-o namespace_inject NAMESPACEINJECT``
	 *Optional*

	 If set, the namespace tokens in files and filenames are replaced with the namespace's prefix

	 Default: $project_config.project__package__namespace

``-o api_version APIVERSION``
	 *Optional*

	 Metadata API version to use, if not project__package__api_version.

set_organization_wide_defaults
==============================

**Description:** Sets the Organization-Wide Defaults for specific sObjects, and waits for sharing recalculation to complete.

**Class:** cumulusci.tasks.metadata_etl.SetOrgWideDefaults

Command Syntax
------------------------------------------

``$ cci task run set_organization_wide_defaults``


Options
------------------------------------------


``-o org_wide_defaults ORGWIDEDEFAULTS``
	 *Required*

	 The target Organization-Wide Defaults, organized as a list with each element containing the keys api_name, internal_sharing_model, and external_sharing_model. NOTE: you must have External Sharing Model turned on in Sharing Settings to use the latter feature.

``-o timeout TIMEOUT``
	 *Optional*

	 The max amount of time to wait in seconds

``-o api_names APINAMES``
	 *Optional*

	 List of API names of entities to affect

``-o managed MANAGED``
	 *Optional*

	 If False, changes namespace_inject to replace tokens with a blank string

``-o namespace_inject NAMESPACEINJECT``
	 *Optional*

	 If set, the namespace tokens in files and filenames are replaced with the namespace's prefix

	 Default: $project_config.project__package__namespace

``-o api_version APIVERSION``
	 *Optional*

	 Metadata API version to use, if not project__package__api_version.

uninstall_managed
=================

**Description:** Uninstalls the managed version of the package

**Class:** cumulusci.tasks.salesforce.UninstallPackage

Command Syntax
------------------------------------------

``$ cci task run uninstall_managed``


Options
------------------------------------------


``-o namespace NAMESPACE``
	 *Required*

	 The namespace of the package to uninstall.  Defaults to project__package__namespace

``-o purge_on_delete PURGEONDELETE``
	 *Required*

	 Sets the purgeOnDelete option for the deployment.  Defaults to True

uninstall_packaged
==================

**Description:** Uninstalls all deleteable metadata in the package in the target org

**Class:** cumulusci.tasks.salesforce.UninstallPackaged

Command Syntax
------------------------------------------

``$ cci task run uninstall_packaged``


Options
------------------------------------------


``-o package PACKAGE``
	 *Required*

	 The package name to uninstall.  All metadata from the package will be retrieved and a custom destructiveChanges.xml package will be constructed and deployed to delete all deleteable metadata from the package.  Defaults to project__package__name

``-o purge_on_delete PURGEONDELETE``
	 *Required*

	 Sets the purgeOnDelete option for the deployment.  Defaults to True

uninstall_packaged_incremental
==============================

**Description:** Deletes any metadata from the package in the target org not in the local workspace

**Class:** cumulusci.tasks.salesforce.UninstallPackagedIncremental

Command Syntax
------------------------------------------

``$ cci task run uninstall_packaged_incremental``


Options
------------------------------------------


``-o path PATH``
	 *Required*

	 The local path to compare to the retrieved packaged metadata from the org.  Defaults to src

``-o package PACKAGE``
	 *Required*

	 The package name to uninstall.  All metadata from the package will be retrieved and a custom destructiveChanges.xml package will be constructed and deployed to delete all deleteable metadata from the package.  Defaults to project__package__name

``-o purge_on_delete PURGEONDELETE``
	 *Required*

	 Sets the purgeOnDelete option for the deployment.  Defaults to True

``-o ignore IGNORE``
	 *Optional*

	 Components to ignore in the org and not try to delete. Mapping of component type to a list of member names.

``-o ignore_types IGNORETYPES``
	 *Optional*

	 List of component types to ignore in the org and not try to delete. Defaults to ['RecordType']

uninstall_src
=============

**Description:** Uninstalls all metadata in the local src directory

**Class:** cumulusci.tasks.salesforce.UninstallLocal

Command Syntax
------------------------------------------

``$ cci task run uninstall_src``


Options
------------------------------------------


``-o path PATH``
	 *Required*

	 The path to the metadata source to be deployed

	 Default: src

``-o unmanaged UNMANAGED``
	 *Optional*

	 If True, changes namespace_inject to replace tokens with a blank string

``-o namespace_inject NAMESPACEINJECT``
	 *Optional*

	 If set, the namespace tokens in files and filenames are replaced with the namespace's prefix

``-o namespace_strip NAMESPACESTRIP``
	 *Optional*

	 If set, all namespace prefixes for the namespace specified are stripped from files and filenames

``-o namespace_tokenize NAMESPACETOKENIZE``
	 *Optional*

	 If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject

``-o check_only CHECKONLY``
	 *Optional*

	 If True, performs a test deployment (validation) of components without saving the components in the target org

``-o test_level TESTLEVEL``
	 *Optional*

	 Specifies which tests are run as part of a deployment. Valid values: NoTestRun, RunLocalTests, RunAllTestsInOrg, RunSpecifiedTests.

``-o specified_tests SPECIFIEDTESTS``
	 *Optional*

	 Comma-separated list of test classes to run upon deployment. Applies only with test_level set to RunSpecifiedTests.

``-o static_resource_path STATICRESOURCEPATH``
	 *Optional*

	 The path where decompressed static resources are stored.  Any subdirectories found will be zipped and added to the staticresources directory of the build.

``-o namespaced_org NAMESPACEDORG``
	 *Optional*

	 If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.

``-o clean_meta_xml CLEANMETAXML``
	 *Optional*

	 Defaults to True which strips the <packageVersions/> element from all meta.xml files.  The packageVersion element gets added automatically by the target org and is set to whatever version is installed in the org.  To disable this, set this option to False

``-o purge_on_delete PURGEONDELETE``
	 *Optional*

	 Sets the purgeOnDelete option for the deployment. Defaults to True

uninstall_pre
=============

**Description:** Uninstalls the unpackaged/pre bundles

**Class:** cumulusci.tasks.salesforce.UninstallLocalBundles

Command Syntax
------------------------------------------

``$ cci task run uninstall_pre``


Options
------------------------------------------


``-o path PATH``
	 *Required*

	 The path to the metadata source to be deployed

	 Default: unpackaged/pre

``-o unmanaged UNMANAGED``
	 *Optional*

	 If True, changes namespace_inject to replace tokens with a blank string

``-o namespace_inject NAMESPACEINJECT``
	 *Optional*

	 If set, the namespace tokens in files and filenames are replaced with the namespace's prefix

``-o namespace_strip NAMESPACESTRIP``
	 *Optional*

	 If set, all namespace prefixes for the namespace specified are stripped from files and filenames

``-o namespace_tokenize NAMESPACETOKENIZE``
	 *Optional*

	 If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject

``-o check_only CHECKONLY``
	 *Optional*

	 If True, performs a test deployment (validation) of components without saving the components in the target org

``-o test_level TESTLEVEL``
	 *Optional*

	 Specifies which tests are run as part of a deployment. Valid values: NoTestRun, RunLocalTests, RunAllTestsInOrg, RunSpecifiedTests.

``-o specified_tests SPECIFIEDTESTS``
	 *Optional*

	 Comma-separated list of test classes to run upon deployment. Applies only with test_level set to RunSpecifiedTests.

``-o static_resource_path STATICRESOURCEPATH``
	 *Optional*

	 The path where decompressed static resources are stored.  Any subdirectories found will be zipped and added to the staticresources directory of the build.

``-o namespaced_org NAMESPACEDORG``
	 *Optional*

	 If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.

``-o clean_meta_xml CLEANMETAXML``
	 *Optional*

	 Defaults to True which strips the <packageVersions/> element from all meta.xml files.  The packageVersion element gets added automatically by the target org and is set to whatever version is installed in the org.  To disable this, set this option to False

``-o purge_on_delete PURGEONDELETE``
	 *Optional*

	 Sets the purgeOnDelete option for the deployment. Defaults to True

uninstall_post
==============

**Description:** Uninstalls the unpackaged/post bundles

**Class:** cumulusci.tasks.salesforce.UninstallLocalNamespacedBundles

Command Syntax
------------------------------------------

``$ cci task run uninstall_post``


Options
------------------------------------------


``-o path PATH``
	 *Required*

	 The path to a directory containing the metadata bundles (subdirectories) to uninstall

	 Default: unpackaged/post

``-o filename_token FILENAMETOKEN``
	 *Required*

	 The path to the parent directory containing the metadata bundles directories

	 Default: ___NAMESPACE___

``-o purge_on_delete PURGEONDELETE``
	 *Required*

	 Sets the purgeOnDelete option for the deployment.  Defaults to True

``-o managed MANAGED``
	 *Optional*

	 If True, will insert the actual namespace prefix.  Defaults to False or no namespace

``-o namespace NAMESPACE``
	 *Optional*

	 The namespace to replace the token with if in managed mode. Defaults to project__package__namespace

unschedule_apex
===============

**Description:** Unschedule all scheduled apex jobs (CronTriggers).

**Class:** cumulusci.tasks.apex.anon.AnonymousApexTask

Use the `apex` option to run a string of anonymous Apex.
Use the `path` option to run anonymous Apex from a file.
Or use both to concatenate the string to the file contents.

Command Syntax
------------------------------------------

``$ cci task run unschedule_apex``


Options
------------------------------------------


``-o path PATH``
	 *Optional*

	 The path to an Apex file to run.

``-o apex APEX``
	 *Optional*

	 A string of Apex to run (after the file, if specified).

	 Default: for (CronTrigger t : [SELECT Id FROM CronTrigger]) { System.abortJob(t.Id); }

``-o managed MANAGED``
	 *Optional*

	 If True, will insert the project's namespace prefix.  Defaults to False or no namespace.

``-o namespaced NAMESPACED``
	 *Optional*

	 If True, the tokens %%%NAMESPACED_RT%%% and %%%namespaced%%% will get replaced with the namespace prefix for Record Types.

``-o param1 PARAM1``
	 *Optional*

	 Parameter to pass to the Apex. Use as %%%PARAM_1%%% in the Apex code.Defaults to an empty value.

``-o param2 PARAM2``
	 *Optional*

	 Parameter to pass to the Apex. Use as %%%PARAM_2%%% in the Apex code.Defaults to an empty value.

update_admin_profile
====================

**Description:** Retrieves, edits, and redeploys the Admin.profile with full FLS perms for all objects/fields

**Class:** cumulusci.tasks.salesforce.ProfileGrantAllAccess

Command Syntax
------------------------------------------

``$ cci task run update_admin_profile``


Options
------------------------------------------


``-o package_xml PACKAGEXML``
	 *Optional*

	 Override the default package.xml file for retrieving the Admin.profile and all objects and classes that need to be included by providing a path to your custom package.xml

``-o record_types RECORDTYPES``
	 *Optional*

	 A list of dictionaries containing the required key `record_type` with a value specifying the record type in format <object>.<developer_name>.  Record type names can use the token strings {managed} and {namespaced_org} for namespace prefix injection as needed.  By default, all listed record types will be set to visible and not default.  Use the additional keys `visible`, `default`, and `person_account_default` set to true/false to override.  NOTE: Setting record_types is only supported in cumulusci.yml, command line override is not supported.

``-o managed MANAGED``
	 *Optional*

	 If True, uses the namespace prefix where appropriate.  Use if running against an org with the managed package installed.  Defaults to False

``-o namespaced_org NAMESPACEDORG``
	 *Optional*

	 If True, attempts to prefix all unmanaged metadata references with the namespace prefix for deployment to the packaging org or a namespaced scratch org.  Defaults to False

``-o namespace_inject NAMESPACEINJECT``
	 *Optional*

	 If set, the namespace tokens in files and filenames are replaced with the namespace's prefix. Defaults to project__package__namespace

``-o profile_name PROFILENAME``
	 *Optional*

	 Name of the Profile to target for updates (deprecated; use api_names to target multiple profiles).

``-o include_packaged_objects INCLUDEPACKAGEDOBJECTS``
	 *Optional*

	 Automatically include objects from all installed managed packages. Defaults to True in projects that require CumulusCI 3.9.0 and greater that don't use a custom package.xml, otherwise False.

``-o api_names APINAMES``
	 *Optional*

	 List of API names of Profiles to affect

update_dependencies
===================

**Description:** Installs all dependencies in project__dependencies into the target org

**Class:** cumulusci.tasks.salesforce.UpdateDependencies

Command Syntax
------------------------------------------

``$ cci task run update_dependencies``


Options
------------------------------------------


``-o dependencies DEPENDENCIES``
	 *Optional*

	 List of dependencies to update. Defaults to project__dependencies. Each dependency is a dict with either 'github' set to a github repository URL or 'namespace' set to a Salesforce package namespace. Github dependencies may include 'tag' to install a particular git ref. Package dependencies may include 'version' to install a particular version.

``-o ignore_dependencies IGNOREDEPENDENCIES``
	 *Optional*

	 List of dependencies to be ignored, including if they are present as transitive dependencies. Dependencies can be specified using the 'github' or 'namespace' keys (all other keys are not used). Note that this can cause installations to fail if required prerequisites are not available.

``-o namespaced_org NAMESPACEDORG``
	 *Optional*

	 If True, the changes namespace token injection on any dependencies so tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.

``-o purge_on_delete PURGEONDELETE``
	 *Optional*

	 Sets the purgeOnDelete option for the deployment. Defaults to True

``-o include_beta INCLUDEBETA``
	 *Optional*

	 Install the most recent release, even if beta. Defaults to False.

``-o allow_newer ALLOWNEWER``
	 *Optional*

	 If the org already has a newer release, use it. Defaults to True.

``-o allow_uninstalls ALLOWUNINSTALLS``
	 *Optional*

	 Allow uninstalling a beta release or newer final release in order to install the requested version. Defaults to False. Warning: Enabling this may destroy data.

``-o security_type SECURITYTYPE``
	 *Optional*

	 Which users to install packages for (FULL = all users, NONE = admins only)

update_metadata_first_child_text
================================

**Description:** Updates the text of the first child of Metadata with matching tag.  Adds a child for tag if it does not exist.

**Class:** cumulusci.tasks.metadata_etl.UpdateMetadataFirstChildTextTask

Metadata ETL task to update a single child element's text within metadata XML.

If the child doesn't exist, the child is created and appended to the Metadata.   Furthermore, the ``value`` option is namespaced injected if the task is properly configured.

Example: Assign a Custom Object's Compact Layout
------------------------------------------------

Researching `CustomObject <https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/customobject.htm>`_ in the Metadata API documentation or even retrieving the CustomObject's Metadata for inspection, we see the ``compactLayoutAssignment`` Field.  We want to assign a specific Compact Layout for our Custom Object, so we write the following CumulusCI task in our project's ``cumulusci.yml``.

.. code-block::  yaml

  tasks:
      assign_compact_layout:
          class_path: cumulusci.tasks.metadata_etl.UpdateMetadataFirstChildTextTask
          options:
              managed: False
              namespace_inject: $project_config.project__package__namespace
              entity: CustomObject
              api_names: OurCustomObject__c
              tag: compactLayoutAssignment
              value: "%%%NAMESPACE%%%DifferentCompactLayout"
              # We include a namespace token so it's easy to use this task in a managed context.

Suppose the original CustomObject metadata XML looks like:

.. code-block:: xml

  <?xml version="1.0" encoding="UTF-8"?>
  <CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
      ...
      <label>Our Custom Object</label>
      <compactLayoutAssignment>OriginalCompactLayout</compactLayoutAssignment>
      ...
  </CustomObject>

After running ``cci task run assign_compact_layout``, the CustomObject metadata XML is deployed as:

.. code-block:: xml

  <?xml version="1.0" encoding="UTF-8"?>
  <CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
      ...
      <label>Our Custom Object</label>
      <compactLayoutAssignment>DifferentCompactLayout</compactLayoutAssignment>
      ...
  </CustomObject>

Command Syntax
------------------------------------------

``$ cci task run update_metadata_first_child_text``


Options
------------------------------------------


``-o metadata_type METADATATYPE``
	 *Required*

	 Metadata Type

``-o tag TAG``
	 *Required*

	 Targeted tag. The text of the first instance of this tag within the metadata entity will be updated.

``-o value VALUE``
	 *Required*

	 Desired value to set for the targeted tag's text. This value is namespace-injected.

``-o api_names APINAMES``
	 *Optional*

	 List of API names of entities to affect

``-o managed MANAGED``
	 *Optional*

	 If False, changes namespace_inject to replace tokens with a blank string

``-o namespace_inject NAMESPACEINJECT``
	 *Optional*

	 If set, the namespace tokens in files and filenames are replaced with the namespace's prefix

	 Default: $project_config.project__package__namespace

``-o api_version APIVERSION``
	 *Optional*

	 Metadata API version to use, if not project__package__api_version.

update_package_xml
==================

**Description:** Updates src/package.xml with metadata in src/

**Class:** cumulusci.tasks.metadata.package.UpdatePackageXml

Command Syntax
------------------------------------------

``$ cci task run update_package_xml``


Options
------------------------------------------


``-o path PATH``
	 *Required*

	 The path to a folder of metadata to build the package.xml from

	 Default: src

``-o output OUTPUT``
	 *Optional*

	 The output file, defaults to <path>/package.xml

``-o package_name PACKAGENAME``
	 *Optional*

	 If set, overrides the package name inserted into the <fullName> element

``-o managed MANAGED``
	 *Optional*

	 If True, generate a package.xml for deployment to the managed package packaging org

``-o delete DELETE``
	 *Optional*

	 If True, generate a package.xml for use as a destructiveChanges.xml file for deleting metadata

upload_beta
===========

**Description:** Uploads a beta release of the metadata currently in the packaging org

**Class:** cumulusci.tasks.salesforce.PackageUpload

Command Syntax
------------------------------------------

``$ cci task run upload_beta``


Options
------------------------------------------


``-o name NAME``
	 *Required*

	 The name of the package version.

``-o production PRODUCTION``
	 *Optional*

	 If True, uploads a production release.  Defaults to uploading a beta

``-o description DESCRIPTION``
	 *Optional*

	 A description of the package and what this version contains.

``-o password PASSWORD``
	 *Optional*

	 An optional password for sharing the package privately with anyone who has the password. Don't enter a password if you want to make the package available to anyone on AppExchange and share your package publicly.

``-o post_install_url POSTINSTALLURL``
	 *Optional*

	 The fully-qualified URL of the post-installation instructions. Instructions are shown as a link after installation and are available from the package detail view.

``-o release_notes_url RELEASENOTESURL``
	 *Optional*

	 The fully-qualified URL of the package release notes. Release notes are shown as a link during the installation process and are available from the package detail view after installation.

``-o namespace NAMESPACE``
	 *Optional*

	 The namespace of the package.  Defaults to project__package__namespace

upload_production
=================

**Description:** Uploads a production release of the metadata currently in the packaging org

**Class:** cumulusci.tasks.salesforce.PackageUpload

Command Syntax
------------------------------------------

``$ cci task run upload_production``


Options
------------------------------------------


``-o name NAME``
	 *Required*

	 The name of the package version.

	 Default: Release

``-o production PRODUCTION``
	 *Optional*

	 If True, uploads a production release.  Defaults to uploading a beta

	 Default: True

``-o description DESCRIPTION``
	 *Optional*

	 A description of the package and what this version contains.

``-o password PASSWORD``
	 *Optional*

	 An optional password for sharing the package privately with anyone who has the password. Don't enter a password if you want to make the package available to anyone on AppExchange and share your package publicly.

``-o post_install_url POSTINSTALLURL``
	 *Optional*

	 The fully-qualified URL of the post-installation instructions. Instructions are shown as a link after installation and are available from the package detail view.

``-o release_notes_url RELEASENOTESURL``
	 *Optional*

	 The fully-qualified URL of the package release notes. Release notes are shown as a link during the installation process and are available from the package detail view after installation.

``-o namespace NAMESPACE``
	 *Optional*

	 The namespace of the package.  Defaults to project__package__namespace

util_sleep
==========

**Description:** Sleeps for N seconds

**Class:** cumulusci.tasks.util.Sleep

Command Syntax
------------------------------------------

``$ cci task run util_sleep``


Options
------------------------------------------


``-o seconds SECONDS``
	 *Required*

	 The number of seconds to sleep

	 Default: 5

log
===

**Description:** Log a line at the info level.

**Class:** cumulusci.tasks.util.LogLine

Command Syntax
------------------------------------------

``$ cci task run log``


Options
------------------------------------------


``-o level LEVEL``
	 *Required*

	 The logger level to use

	 Default: info

``-o line LINE``
	 *Required*

	 A formatstring like line to log

``-o format_vars FORMATVARS``
	 *Optional*

	 A Dict of format vars

generate_dataset_mapping
========================

**Description:** Create a mapping for extracting data from an org.

**Class:** cumulusci.tasks.bulkdata.GenerateMapping

Generate a mapping file for use with the `extract_dataset` and `load_dataset` tasks.
This task will examine the schema in the specified org and attempt to infer a
mapping suitable for extracting data in packaged and custom objects as well as
customized standard objects.

Mappings must be serializable, and hence must resolve reference cycles - situations
where Object A refers to B, and B also refers to A. Mapping generation will stop
and request user input to resolve such cycles by identifying the correct load order.
If you would rather the mapping generator break such a cycle randomly, set the
`break_cycles` option to `auto`.

Alternately, specify the `ignore` option with the name of one of the
lookup fields to suppress it and break the cycle. `ignore` can be specified as a list in
`cumulusci.yml` or as a comma-separated string at the command line.

In most cases, the mapping generated will need minor tweaking by the user. Note
that the mapping omits features that are not currently well supported by the
`extract_dataset` and `load_dataset` tasks, such as references to
the `User` object.

Command Syntax
------------------------------------------

``$ cci task run generate_dataset_mapping``


Options
------------------------------------------


``-o path PATH``
	 *Required*

	 Location to write the mapping file

	 Default: datasets/mapping.yml

``-o namespace_prefix NAMESPACEPREFIX``
	 *Optional*

	 The namespace prefix to use

	 Default: $project_config.project__package__namespace

``-o ignore IGNORE``
	 *Optional*

	 Object API names, or fields in Object.Field format, to ignore

``-o break_cycles BREAKCYCLES``
	 *Optional*

	 If the generator is unsure of the order to load, what to do? Set to `ask` (the default) to allow the user to choose or `auto` to pick randomly.

``-o include INCLUDE``
	 *Optional*

	 Object names to include even if they might not otherwise be included.

``-o strip_namespace STRIPNAMESPACE``
	 *Optional*

	 If True, CumulusCI removes the project's namespace where found in fields  and objects to support automatic namespace injection. On by default.

extract_dataset
===============

**Description:** Extract a sample dataset using the bulk API.

**Class:** cumulusci.tasks.bulkdata.ExtractData

Command Syntax
------------------------------------------

``$ cci task run extract_dataset``


Options
------------------------------------------


``-o mapping MAPPING``
	 *Required*

	 The path to a yaml file containing mappings of the database fields to Salesforce object fields

	 Default: datasets/mapping.yml

``-o database_url DATABASEURL``
	 *Optional*

	 A DATABASE_URL where the query output should be written

``-o sql_path SQLPATH``
	 *Optional*

	 If set, an SQL script will be generated at the path provided This is useful for keeping data in the repository and allowing diffs.

	 Default: datasets/sample.sql

``-o inject_namespaces INJECTNAMESPACES``
	 *Optional*

	 If True, the package namespace prefix will be automatically added to objects and fields for which it is present in the org. Defaults to True.

``-o drop_missing_schema DROPMISSINGSCHEMA``
	 *Optional*

	 Set to True to skip any missing objects or fields instead of stopping with an error.

load_dataset
============

**Description:** Load a sample dataset using the bulk API.

**Class:** cumulusci.tasks.bulkdata.LoadData

Command Syntax
------------------------------------------

``$ cci task run load_dataset``


Options
------------------------------------------


``-o database_url DATABASEURL``
	 *Optional*

	 The database url to a database containing the test data to load

``-o mapping MAPPING``
	 *Optional*

	 The path to a yaml file containing mappings of the database fields to Salesforce object fields

	 Default: datasets/mapping.yml

``-o start_step STARTSTEP``
	 *Optional*

	 If specified, skip steps before this one in the mapping

``-o sql_path SQLPATH``
	 *Optional*

	 If specified, a database will be created from an SQL script at the provided path

	 Default: datasets/sample.sql

``-o ignore_row_errors IGNOREROWERRORS``
	 *Optional*

	 If True, allow the load to continue even if individual rows fail to load.

``-o reset_oids RESETOIDS``
	 *Optional*

	 If True (the default), and the _sf_ids tables exist, reset them before continuing.

``-o bulk_mode BULKMODE``
	 *Optional*

	 Set to Serial to force serial mode on all jobs. Parallel is the default.

``-o inject_namespaces INJECTNAMESPACES``
	 *Optional*

	 If True, the package namespace prefix will be automatically added to objects and fields for which it is present in the org. Defaults to True.

``-o drop_missing_schema DROPMISSINGSCHEMA``
	 *Optional*

	 Set to True to skip any missing objects or fields instead of stopping with an error.

load_custom_settings
====================

**Description:** Load Custom Settings specified in a YAML file to the target org

**Class:** cumulusci.tasks.salesforce.LoadCustomSettings

Command Syntax
------------------------------------------

``$ cci task run load_custom_settings``


Options
------------------------------------------


``-o settings_path SETTINGSPATH``
	 *Required*

	 The path to a YAML settings file

remove_metadata_xml_elements
============================

**Description:** Remove specified XML elements from one or more metadata files

**Class:** cumulusci.tasks.metadata.modify.RemoveElementsXPath

Command Syntax
------------------------------------------

``$ cci task run remove_metadata_xml_elements``


Options
------------------------------------------


``-o xpath XPATH``
	 *Optional*

	 An XPath specification of elements to remove. Supports the re: regexp function namespace. As in re:match(text(), '.*__c')Use ns: to refer to the Salesforce namespace for metadata elements.for example: ./ns:Layout/ns:relatedLists (one-level) or //ns:relatedLists (recursive)Many advanced examples are available here: https://github.com/SalesforceFoundation/NPSP/blob/26b585409720e2004f5b7785a56e57498796619f/cumulusci.yml#L342

``-o path PATH``
	 *Optional*

	 A path to the files to change. Supports wildcards including ** for directory recursion. More info on the details: https://www.poftut.com/python-glob-function-to-match-path-directory-file-names-with-examples/ https://www.tutorialspoint.com/How-to-use-Glob-function-to-find-files-recursively-in-Python 

``-o elements ELEMENTS``
	 *Optional*

	 A list of dictionaries containing path and xpath keys. Multiple dictionaries can be passed in the list to run multiple removal queries in the same task. This parameter is intended for usages invoked as part of a cumulusci.yml .

``-o chdir CHDIR``
	 *Optional*

	 Change the current directory before running the replace

disable_tdtm_trigger_handlers
=============================

**Description:** Disable specified TDTM trigger handlers

**Class:** cumulusci.tasks.salesforce.trigger_handlers.SetTDTMHandlerStatus

Command Syntax
------------------------------------------

``$ cci task run disable_tdtm_trigger_handlers``


Options
------------------------------------------


``-o handlers HANDLERS``
	 *Optional*

	 List of Trigger Handlers (by Class, Object, or 'Class:Object') to affect (defaults to all handlers).

``-o namespace NAMESPACE``
	 *Optional*

	 The namespace of the Trigger Handler object ('eda' or 'npsp'). The task will apply the namespace if needed.

``-o active ACTIVE``
	 *Optional*

	 True or False to activate or deactivate trigger handlers.

``-o restore_file RESTOREFILE``
	 *Optional*

	 Path to the state file to store the current trigger handler state.

	 Default: trigger_status.yml

``-o restore RESTORE``
	 *Optional*

	 If True, restore the state of Trigger Handlers to that stored in the restore file.

restore_tdtm_trigger_handlers
=============================

**Description:** Restore status of TDTM trigger handlers

**Class:** cumulusci.tasks.salesforce.trigger_handlers.SetTDTMHandlerStatus

Command Syntax
------------------------------------------

``$ cci task run restore_tdtm_trigger_handlers``


Options
------------------------------------------


``-o handlers HANDLERS``
	 *Optional*

	 List of Trigger Handlers (by Class, Object, or 'Class:Object') to affect (defaults to all handlers).

``-o namespace NAMESPACE``
	 *Optional*

	 The namespace of the Trigger Handler object ('eda' or 'npsp'). The task will apply the namespace if needed.

``-o active ACTIVE``
	 *Optional*

	 True or False to activate or deactivate trigger handlers.

``-o restore_file RESTOREFILE``
	 *Optional*

	 Path to the state file to store the current trigger handler state.

	 Default: trigger_status.yml

``-o restore RESTORE``
	 *Optional*

	 If True, restore the state of Trigger Handlers to that stored in the restore file.

	 Default: True

