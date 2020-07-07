==========================================
Tasks Reference
==========================================

**activate_flow**
==========================================

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

**add_page_layout_related_lists**
==========================================

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

**add_standard_value_set_entries**
==========================================

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

**add_picklist_entries**
==========================================

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

	 Array of picklist values to insert. Each value should contain the keys 'fullName', the API name of the entry, and 'label', the user-facing label. Optionally, specify `default: True` on exactly one entry to make that value the default. Any existing values will not be affected other than setting the default (labels of existing entries are not changed).
To order values, include the 'add_before' key. This will insert the new value before the existing value with the given API name, or at the end of the list if not present.

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

**add_permission_set_perms**
==========================================

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

**batch_apex_wait**
==========================================

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

**check_communities_enabled**
==========================================

**Description:** Runs as a preflight check to determine whether Communities are enabled.

**Class:** cumulusci.tasks.preflight.sobjects.CheckSObjectsAvailable

Command Syntax
------------------------------------------

``$ cci task run check_communities_enabled``


Options
------------------------------------------


``-o sobjects SOBJECTS``
	 *Required*

	 A list of sObjects whose presence needs to be verified.

	 Default: Network

**check_sobjects_available**
==========================================

**Description:** Runs as a preflight check to determine whether specific sObjects are available.

**Class:** cumulusci.tasks.preflight.sobjects.CheckSObjectsAvailable

Command Syntax
------------------------------------------

``$ cci task run check_sobjects_available``


Options
------------------------------------------


``-o sobjects SOBJECTS``
	 *Required*

	 A list of sObjects whose presence needs to be verified.

Error: module 'cumulusci.tasks.preflight.sobjects' has no attribute 'CheckSobjectOWDs'
Run this command for more information about debugging errors: cci error --help
