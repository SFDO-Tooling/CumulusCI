---
title: Tasks Reference
---

# **activate_flow**

**Description:** Activates Flows identified by a given list of Developer
Names

**Class:** cumulusci.tasks.salesforce.activate_flow.ActivateFlow

## Command Syntax

`$ cci task run activate_flow`

## Options

`--developer_names DEVELOPERNAMES`

: _Required_

    List of DeveloperNames to query in SOQL

# **add_page_layout_related_lists**

**Description:** Adds specified Related List to one or more Page
Layouts.

**Class:** cumulusci.tasks.metadata_etl.AddRelatedLists

## Command Syntax

`$ cci task run add_page_layout_related_lists`

## Options

`--related_list RELATEDLIST`

: _Required_

    Name of the Related List to include

`--fields FIELDS`

: _Optional_

    Array of field API names to include in the related list

`--exclude_buttons EXCLUDEBUTTONS`

: _Optional_

    Array of button names to suppress from the related list

`--custom_buttons CUSTOMBUTTONS`

: _Optional_

    Array of button names to add to the related list

`--api_names APINAMES`

: _Optional_

    List of API names of entities to affect

`--managed MANAGED`

: _Optional_

    If False, changes namespace_inject to replace tokens with a blank
    string

`--namespace_inject NAMESPACEINJECT`

: _Optional_

    If set, the namespace tokens in files and filenames are replaced
    with the namespace\'s prefix

    Default: \$project_config.project\_\_package\_\_namespace

`--api_version APIVERSION`

: _Optional_

    Metadata API version to use, if not
    project\_\_package\_\_api_version.

# **add_page_layout_fields**

**Description:** Adds specified Fields or Visualforce Pages to a Page
Layout.

**Class:** cumulusci.tasks.metadata_etl.layouts.AddFieldsToPageLayout

Inserts the listed fields or Visualforce pages into page layouts
specified by API name.

If the targeted item already exists, the layout metadata is not
modified.

You may supply a single position option, or multiple options for both
pages and fields. The first option to to be matched will be used.

Task option details:

-   fields:

    > -   api_name: \[field API name\]
    >
    > -   required: Boolean (default False)
    >
    > -   read_only: Boolean (default False, not compatible with
    >     required)
    >
    > -   position: (Optional: A list of single or multiple position
    >     options.)
    >
    >     > -   relative: \[before \| after \| top \| bottom\]
    >     > -   field: \[api_name\] (Use with relative: before, after)
    >     > -   section: \[index\] (Use with relative: top, bottom)
    >     > -   column: \[first \| last\] (Use with relative: top,
    >     >     bottom)

-   pages:

    > -   api_name: \[Visualforce Page API name\]
    >
    > -   height: int (Optional. Default: 200)
    >
    > -   show_label: Boolean (Optional. Default: False)
    >
    > -   show_scrollbars: Boolean (Optional. Default: False)
    >
    > -   width: 0-100% (Optional. Default: 100%)
    >
    > -   position: (Optional: A list of single or multiple position
    >     options.)
    >
    >     > -   relative: \[before \| after \| top \| bottom\]
    >     > -   field: \[api_name\] (Use with relative: before, after)
    >     > -   section: \[index\] (Use with relative: top, bottom)
    >     > -   column: \[first \| last\] (Use with relative: top,
    >     >     bottom)

## Command Syntax

`$ cci task run add_page_layout_fields`

## Options

`--fields FIELDS`

: _Optional_

    List of fields. See task info for structure.

`--pages PAGES`

: _Optional_

    List of Visualforce Pages. See task info for structure.

`--api_names APINAMES`

: _Optional_

    List of API names of entities to affect

`--managed MANAGED`

: _Optional_

    If False, changes namespace_inject to replace tokens with a blank
    string

`--namespace_inject NAMESPACEINJECT`

: _Optional_

    If set, the namespace tokens in files and filenames are replaced
    with the namespace\'s prefix

`--api_version APIVERSION`

: _Optional_

    Metadata API version to use, if not
    project\_\_package\_\_api_version.

# **add_standard_value_set_entries**

**Description:** Adds specified picklist entries to a Standard Value
Set.

**Class:** cumulusci.tasks.metadata_etl.AddValueSetEntries

## Command Syntax

`$ cci task run add_standard_value_set_entries`

## Options

`--api_names APINAMES`

: _Required_

    List of API names of StandardValueSets to affect, such as
    \'OpportunityStage\', \'AccountType\', \'CaseStatus\',
    \'LeadStatus\'

`--entries ENTRIES`

: _Required_

    Array of standardValues to insert. Each standardValue should contain
    the keys \'fullName\', the API name of the entry, and \'label\', the
    user-facing label. OpportunityStage entries require the additional
    keys \'closed\', \'won\', \'forecastCategory\', and \'probability\';
    CaseStatus entries require \'closed\'; LeadStatus entries require
    \'converted\'.

`--managed MANAGED`

: _Optional_

    If False, changes namespace_inject to replace tokens with a blank
    string

`--namespace_inject NAMESPACEINJECT`

: _Optional_

    If set, the namespace tokens in files and filenames are replaced
    with the namespace\'s prefix

    Default: \$project_config.project\_\_package\_\_namespace

`--api_version APIVERSION`

: _Optional_

    Metadata API version to use, if not
    project\_\_package\_\_api_version.

# **add_picklist_entries**

**Description:** Adds specified picklist entries to a custom picklist
field.

**Class:** cumulusci.tasks.metadata_etl.picklists.AddPicklistEntries

## Command Syntax

`$ cci task run add_picklist_entries`

## Options

`--picklists PICKLISTS`

: _Required_

    List of picklists to affect, in Object\_\_c.Field\_\_c form.

`--entries ENTRIES`

: _Required_

    Array of picklist values to insert. Each value should contain the
    keys \'fullName\', the API name of the entry, and \'label\', the
    user-facing label. Optionally, specify [default: True]{.title-ref}
    on exactly one entry to make that value the default. Any existing
    values will not be affected other than setting the default (labels
    of existing entries are not changed). To order values, include the
    \'add_before\' key. This will insert the new value before the
    existing value with the given API name, or at the end of the list if
    not present.

`--record_types RECORDTYPES`

: _Optional_

    List of Record Type developer names for which the new values should
    be available. If any of the entries have [default:
    True]{.title-ref}, they are also made default for these Record
    Types. Any Record Types not present in the target org will be
    ignored, and \* is a wildcard. Default behavior is to do nothing.

`--api_names APINAMES`

: _Optional_

    List of API names of entities to affect

`--managed MANAGED`

: _Optional_

    If False, changes namespace_inject to replace tokens with a blank
    string

`--namespace_inject NAMESPACEINJECT`

: _Optional_

    If set, the namespace tokens in files and filenames are replaced
    with the namespace\'s prefix

    Default: \$project_config.project\_\_package\_\_namespace

`--api_version APIVERSION`

: _Optional_

    Metadata API version to use, if not
    project\_\_package\_\_api_version.

# **add_fields_to_field_set**

**Description:** Adds specified fields to a given field set.

**Class:** cumulusci.tasks.metadata_etl.field_sets.AddFieldsToFieldSet

## Command Syntax

`$ cci task run add_fields_to_field_set`

## Options

`--field_set FIELDSET`

: _Required_

    Name of field set to affect, in Object\_\_c.FieldSetName form.

`--fields FIELDS`

: _Required_

    Array of field API names to add to the field set. Can include
    related fields using AccountId.Name or Lookup\_\_r.CustomField\_\_c
    style syntax.

`--api_names APINAMES`

: _Optional_

    List of API names of entities to affect

`--managed MANAGED`

: _Optional_

    If False, changes namespace_inject to replace tokens with a blank
    string

`--namespace_inject NAMESPACEINJECT`

: _Optional_

    If set, the namespace tokens in files and filenames are replaced
    with the namespace\'s prefix

`--api_version APIVERSION`

: _Optional_

    Metadata API version to use, if not
    project\_\_package\_\_api_version.

# **add_permission_set_perms**

**Description:** Adds specified Apex class access and Field-Level
Security to a Permission Set.

**Class:** cumulusci.tasks.metadata_etl.AddPermissionSetPermissions

## Command Syntax

`$ cci task run add_permission_set_perms`

## Options

`--field_permissions FIELDPERMISSIONS`

: _Optional_

    Array of fieldPermissions objects to upsert into permission_set.
    Each fieldPermission requires the following attributes: \'field\':
    API Name of the field including namespace; \'readable\': boolean if
    field can be read; \'editable\': boolean if field can be edited

`--class_accesses CLASSACCESSES`

: _Optional_

    Array of classAccesses objects to upsert into permission_set. Each
    classAccess requires the following attributes: \'apexClass\': Name
    of Apex Class. If namespaced, make sure to use the form
    \"namespace\_\_ApexClass\"; \'enabled\': boolean if the Apex Class
    can be accessed.

`--api_names APINAMES`

: _Optional_

    List of API names of entities to affect

`--managed MANAGED`

: _Optional_

    If False, changes namespace_inject to replace tokens with a blank
    string

`--namespace_inject NAMESPACEINJECT`

: _Optional_

    If set, the namespace tokens in files and filenames are replaced
    with the namespace\'s prefix

    Default: \$project_config.project\_\_package\_\_namespace

`--api_version APIVERSION`

: _Optional_

    Metadata API version to use, if not
    project\_\_package\_\_api_version.

# **add_record_action_list_item**

**Description:** Adds the specified \'Record\' context Lightning
button/action to the provided page layout.

**Class:**
cumulusci.tasks.metadata_etl.layouts.AddRecordPlatformActionListItem

Inserts the targeted lightning button/action into specified layout\'s
PlatformActionList with a \'Record\' actionListContext. - If the
targeted lightning button/action already exists, the layout metadata is
not modified. - If there is no \'Record\' context PlatformActionList, we
will generate one and add the specified action

Task definition example:

> dev_inject_apply_quick_action_into_account_layout: group: \"Demo
> config and storytelling\" description: Adds an Apply Quick Action
> button to the beggining of the button list on the Experiences Account
> Layout. class_path: tasks.layouts.InsertRecordPlatformActionListItem
> options: api_names: \"Account-%%%NAMESPACE%%%Experiences Account
> Layout\" action_name: \"Account.Apply\" action_type: QuickAction
> place_first: True

Reference Documentation:
<https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_layouts.htm#PlatformActionList>

## Command Syntax

`$ cci task run add_record_action_list_item`

## Options

`--action_type ACTIONTYPE`

: _Required_

    platformActionListItems.actionType like \'QuickAction\' or
    \'CustomButton\'

`--action_name ACTIONNAME`

: _Required_

    platformActionListItems.actionName. The API name for the action to
    be added.

`--place_first PLACEFIRST`

: _Optional_

    When \'True\' the specified Record platformActionListItem will be
    inserted before any existing on the layout. Default is \'False\'

`--api_names APINAMES`

: _Optional_

    List of API names of entities to affect

`--managed MANAGED`

: _Optional_

    If False, changes namespace_inject to replace tokens with a blank
    string

`--namespace_inject NAMESPACEINJECT`

: _Optional_

    If set, the namespace tokens in files and filenames are replaced
    with the namespace\'s prefix

`--api_version APIVERSION`

: _Optional_

    Metadata API version to use, if not
    project\_\_package\_\_api_version.

# **assign_compact_layout**

**Description:** Assigns the Compact Layout specified in the \'value\'
option to the Custom Objects in \'api_names\' option.

**Class:** cumulusci.tasks.metadata_etl.UpdateMetadataFirstChildTextTask

Metadata ETL task to update a single child element\'s text within
metadata XML.

If the child doesn\'t exist, the child is created and appended to the
Metadata. Furthermore, the `value` option is namespaced injected if the
task is properly configured.

## Example: Assign a Custom Object\'s Compact Layout

Researching
[CustomObject](https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/customobject.htm)
in the Metadata API documentation or even retrieving the CustomObject\'s
Metadata for inspection, we see the `compactLayoutAssignment` Field. We
want to assign a specific Compact Layout for our Custom Object, so we
write the following CumulusCI task in our project\'s `cumulusci.yml`.

```yaml
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
```

Suppose the original CustomObject metadata XML looks like:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    ...
    <label>Our Custom Object</label>
    <compactLayoutAssignment>OriginalCompactLayout</compactLayoutAssignment>
    ...
</CustomObject>
```

After running `cci task run assign_compact_layout`, the CustomObject
metadata XML is deployed as:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    ...
    <label>Our Custom Object</label>
    <compactLayoutAssignment>DifferentCompactLayout</compactLayoutAssignment>
    ...
</CustomObject>
```

## Command Syntax

`$ cci task run assign_compact_layout`

## Options

`--metadata_type METADATATYPE`

: _Required_

    Metadata Type

    Default: CustomObject

`--tag TAG`

: _Required_

    Targeted tag. The text of the first instance of this tag within the
    metadata entity will be updated.

    Default: compactLayoutAssignment

`--value VALUE`

: _Required_

    Desired value to set for the targeted tag\'s text. This value is
    namespace-injected.

`--api_names APINAMES`

: _Optional_

    List of API names of entities to affect

`--managed MANAGED`

: _Optional_

    If False, changes namespace_inject to replace tokens with a blank
    string

`--namespace_inject NAMESPACEINJECT`

: _Optional_

    If set, the namespace tokens in files and filenames are replaced
    with the namespace\'s prefix

    Default: \$project_config.project\_\_package\_\_namespace

`--api_version APIVERSION`

: _Optional_

    Metadata API version to use, if not
    project\_\_package\_\_api_version.

# **assign_permission_sets**

**Description:** Assigns specified Permission Sets to the current user,
if not already assigned.

**Class:**
cumulusci.tasks.salesforce.users.permsets.AssignPermissionSets

Assigns Permission Sets whose Names are in `api_names` to either the
default org user or the user whose Alias is `user_alias`. This task
skips assigning Permission Sets that are already assigned.

## Command Syntax

`$ cci task run assign_permission_sets`

## Options

`--api_names APINAMES`

: _Required_

    API Names of desired Permission Sets, separated by commas.

`--user_alias USERALIAS`

: _Optional_

    Target user aliases, separated by commas. Defaults to the current
    running user.

# **assign_permission_set_groups**

**Description:** Assigns specified Permission Set Groups to the current
user, if not already assigned.

**Class:**
cumulusci.tasks.salesforce.users.permsets.AssignPermissionSetGroups

Assigns Permission Set Groups whose Developer Names are in `api_names`
to either the default org user or the user whose Alias is `user_alias`.
This task skips assigning Permission Set Groups that are already
assigned.

## Command Syntax

`$ cci task run assign_permission_set_groups`

## Options

`--api_names APINAMES`

: _Required_

    API Developer Names of desired Permission Set Groups, separated by
    commas.

`--user_alias USERALIAS`

: _Optional_

    Alias of target user (if not the current running user, the default).

# **assign_permission_set_licenses**

**Description:** Assigns specified Permission Set Licenses to the
current user, if not already assigned.

**Class:**
cumulusci.tasks.salesforce.users.permsets.AssignPermissionSetLicenses

Assigns Permission Set Licenses whose Developer Names are in `api_names`
to either the default org user or the user whose Alias is `user_alias`.
This task skips assigning Permission Set Licenses that are already
assigned.

Permission Set Licenses are usually associated with a Permission Set,
and assigning the Permission Set usually assigns the associated
Permission Set License automatically. However, in non-namespaced
developer scratch orgs, assigning the associated Permission Set may not
automatically assign the Permission Set License, and this task will
ensure the Permission Set Licenses are assigned.

## Command Syntax

`$ cci task run assign_permission_set_licenses`

## Options

`--api_names APINAMES`

: _Required_

    API Developer Names of desired Permission Set Licenses, separated by
    commas.

`--user_alias USERALIAS`

: _Optional_

    Alias of target user (if not the current running user, the default).

# **batch_apex_wait**

**Description:** Waits on a batch apex or queueable apex job to finish.

**Class:** cumulusci.tasks.apex.batch.BatchApexWait

## Command Syntax

`$ cci task run batch_apex_wait`

## Options

`--class_name CLASSNAME`

: _Required_

    Name of the Apex class to wait for.

`--poll_interval POLLINTERVAL`

: _Optional_

    Seconds to wait before polling for batch or queueable job
    completion. Defaults to 10 seconds.

# **check_my_domain_active**

**Description:** Runs as a preflight check to determine whether My
Domain is active.

**Class:** cumulusci.tasks.preflight.settings.CheckMyDomainActive

## Command Syntax

`$ cci task run check_my_domain_active`

# **check_sobjects_available**

**Description:** Runs as a preflight check to determine whether specific
sObjects are available.

**Class:** cumulusci.tasks.preflight.sobjects.CheckSObjectsAvailable

As a MetaDeploy preflight check, validates that an sObject is present in
the schema.

> The task can be used as a preflight check thus:
>
>     3:
>         task: insert_sobject_records
>         checks:
>             - when: "'ContentNote' not in tasks.check_sobjects_available()"
>               action: error
>               message: "Enhanced Notes are not turned on."

## Command Syntax

`$ cci task run check_sobjects_available`

# **check_sobject_permissions**

**Description:** Runs as a preflight check to determine whether specific
sObjects are permissioned as desired (options are required).

**Class:** cumulusci.tasks.preflight.sobjects.CheckSObjectPerms

As a MetaDeploy preflight check, validates that an sObject\'s
permissions are in the expected state.

> For example, specify:
>
>     check_sobject_permissions:
>         options:
>             Account:
>                 createable: True
>                 updateable: False
>             Contact:
>                 createable: False
>
> to validate that the Account object is createable but not updateable,
> and the Contact object is not createable. The output is True if all
> sObjects and permissions are present and matching the specification.
>
> Given the above configuration, the task can be used as a preflight
> check in a MetaDeploy plan:
>
>     3:
>         task: insert_sobject_records
>         checks:
>             - when: "not tasks.check_sobject_permissions()"
>               action: error
>               message: "sObject permissions are not configured correctly."

## Command Syntax

`$ cci task run check_sobject_permissions`

## Options

`--permissions PERMISSIONS`

: _Required_

    The object permissions to check. Each key should be an sObject API
    name, whose value is a map of describe keys, such as
    [queryable]{.title-ref} and [createable]{.title-ref}, to their
    desired values (True or False). The output is True if all sObjects
    and permissions are present and matching the specification. See the
    task documentation for examples.

# **check_advanced_currency_management**

**Description:** Runs as a preflight check to determine whether Advanced
Currency Management is active (True result means the feature is active).

**Class:** cumulusci.tasks.preflight.sobjects.CheckSObjectPerms

As a MetaDeploy preflight check, validates that an sObject\'s
permissions are in the expected state.

> For example, specify:
>
>     check_sobject_permissions:
>         options:
>             Account:
>                 createable: True
>                 updateable: False
>             Contact:
>                 createable: False
>
> to validate that the Account object is createable but not updateable,
> and the Contact object is not createable. The output is True if all
> sObjects and permissions are present and matching the specification.
>
> Given the above configuration, the task can be used as a preflight
> check in a MetaDeploy plan:
>
>     3:
>         task: insert_sobject_records
>         checks:
>             - when: "not tasks.check_sobject_permissions()"
>               action: error
>               message: "sObject permissions are not configured correctly."

## Command Syntax

`$ cci task run check_advanced_currency_management`

## Options

`--permissions PERMISSIONS`

: _Required_

    The object permissions to check. Each key should be an sObject API
    name, whose value is a map of describe keys, such as
    [queryable]{.title-ref} and [createable]{.title-ref}, to their
    desired values (True or False). The output is True if all sObjects
    and permissions are present and matching the specification. See the
    task documentation for examples.

    Default: {\'DatedConversionRate\': {\'createable\': True}}

# **check_org_wide_defaults**

**Description:** Runs as a preflight check to validate Organization-Wide
Defaults.

**Class:** cumulusci.tasks.preflight.sobjects.CheckSObjectOWDs

As a MetaDeploy preflight check, validates that an sObject\'s Org-Wide
Defaults are in the expected state.

> For example, specify:
>
>     check_org_wide_defaults:
>         options:
>             org_wide_defaults:
>                 - api_name: Account
>                   internal_sharing_model: Private
>                   external_sharing_model: Private
>                 - api_name: Contact
>                   internal_sharing_model: Private
>
> to validate that the Account object has Private internal and external
> OWDs, and Contact a Private internal model. The output is True if all
> sObjects and permissions are present and matching the specification.
>
> Given the above configuration, the task can be used as a preflight
> check in a MetaDeploy plan:
>
>     3:
>         task: insert_sobject_records
>         checks:
>             - when: "not tasks.check_org_wide_defaults()"
>               action: error
>               message: "Org-Wide Defaults are not configured correctly."

## Command Syntax

`$ cci task run check_org_wide_defaults`

## Options

`--org_wide_defaults ORGWIDEDEFAULTS`

: _Required_

    The Organization-Wide Defaults to check, organized as a list with
    each element containing the keys api_name, internal_sharing_model,
    and external_sharing_model. NOTE: you must have External Sharing
    Model turned on in Sharing Settings to use the latter feature.
    Checking External Sharing Model when it is turned off will fail the
    preflight.

# **check_org_settings_value**

**Description:** Runs as a preflight check to validate organization
settings.

**Class:** cumulusci.tasks.preflight.settings.CheckSettingsValue

## Command Syntax

`$ cci task run check_org_settings_value`

## Options

`--settings_type SETTINGSTYPE`

: _Required_

    The API name of the Settings entity to be checked, such as
    ChatterSettings.

`--settings_field SETTINGSFIELD`

: _Required_

    The API name of the field on the Settings entity to check.

`--value VALUE`

: _Required_

    The value to check for

`--treat_missing_as_failure TREATMISSINGASFAILURE`

: _Optional_

    If True, treat a missing Settings entity as a preflight failure,
    instead of raising an exception. Defaults to False.

# **check_chatter_enabled**

**Description:** Runs as a preflight check to validate Chatter is
enabled.

**Class:** cumulusci.tasks.preflight.settings.CheckSettingsValue

## Command Syntax

`$ cci task run check_chatter_enabled`

## Options

`--settings_type SETTINGSTYPE`

: _Required_

    The API name of the Settings entity to be checked, such as
    ChatterSettings.

    Default: ChatterSettings

`--settings_field SETTINGSFIELD`

: _Required_

    The API name of the field on the Settings entity to check.

    Default: IsChatterEnabled

`--value VALUE`

: _Required_

    The value to check for

    Default: True

`--treat_missing_as_failure TREATMISSINGASFAILURE`

: _Optional_

    If True, treat a missing Settings entity as a preflight failure,
    instead of raising an exception. Defaults to False.

# **check_enhanced_notes_enabled**

**Description:** Preflight check to validate that Enhanced Notes are
enabled.

**Class:** cumulusci.tasks.preflight.settings.CheckSettingsValue

## Command Syntax

`$ cci task run check_enhanced_notes_enabled`

## Options

`--settings_type SETTINGSTYPE`

: _Required_

    The API name of the Settings entity to be checked, such as
    ChatterSettings.

    Default: EnhancedNotesSettings

`--settings_field SETTINGSFIELD`

: _Required_

    The API name of the field on the Settings entity to check.

    Default: IsEnhancedNotesEnabled

`--value VALUE`

: _Required_

    The value to check for

    Default: True

`--treat_missing_as_failure TREATMISSINGASFAILURE`

: _Optional_

    If True, treat a missing Settings entity as a preflight failure,
    instead of raising an exception. Defaults to False.

# **custom_settings_value_wait**

**Description:** Waits for a specific field value on the specified
custom settings object and field

**Class:**
cumulusci.tasks.salesforce.custom_settings_wait.CustomSettingValueWait

## Command Syntax

`$ cci task run custom_settings_value_wait`

## Options

`--object OBJECT`

: _Required_

    Name of the Hierarchical Custom Settings object to query. Can
    include the %%%NAMESPACE%%% token.

`--field FIELD`

: _Required_

    Name of the field on the Custom Settings to query. Can include the
    %%%NAMESPACE%%% token.

`--value VALUE`

: _Required_

    Value of the field to wait for (String, Integer or Boolean).

`--managed MANAGED`

: _Optional_

    If True, will insert the project\'s namespace prefix. Defaults to
    False or no namespace.

`--namespaced NAMESPACED`

: _Optional_

    If True, the %%%NAMESPACE%%% token will get replaced with the
    namespace prefix for the object and field.Defaults to False.

`--poll_interval POLLINTERVAL`

: _Optional_

    Seconds to wait before polling for batch job completion. Defaults to
    10 seconds.

# **command**

**Description:** Run an arbitrary command

**Class:** cumulusci.tasks.command.Command

**Example Command-line Usage:**
`cci task run command -o command "echo 'Hello command task!'"`

**Example Task to Run Command:**

```yaml
hello_world:
    description: Says hello world
    class_path: cumulusci.tasks.command.Command
    options:
        command: echo 'Hello World!'
```

## Command Syntax

`$ cci task run command`

## Options

`--command COMMAND`

: _Required_

    The command to execute

`--pass_env PASSENV`

: _Required_

    If False, the current environment variables will not be passed to
    the child process. Defaults to True

`--dir DIR`

: _Optional_

    If provided, the directory where the command should be run from.

`--env ENV`

: _Optional_

    Environment variables to set for command. Must be flat dict, either
    as python dict from YAML or as JSON string.

`--interactive INTERACTIVE`

: _Optional_

    If True, the command will use stderr, stdout, and stdin of the main
    process.Defaults to False.

# **composite_request**

**Description:** Execute a series of REST API requests in a single call

**Class:** cumulusci.tasks.salesforce.composite.CompositeApi

This task is a wrapper for Composite REST API calls. Given a list of
JSON files (one request body per file), POST each and process the
returned composite result. Files are processed in the order given by the
`data_files` option.

In addition, this task will process the request body and replace
namespace (`%%%NAMESPACE%%%`) and user ID (`%%%USERID%%%`) tokens. To
avoid username collisions, use the `randomize_username` option to
replace the top-level domains in any `Username` field with a random
string.

When the top-level `allOrNone` property for the request is set to true a
SalesforceException is raised if an error is returned for any
subrequest, otherwise partial successes will not raise an exception.

## Example Task Definition

```yaml
tasks:
    example_composite_request:
        class_path: cumulusci.tasks.salesforce.composite.CompositeApi
        options:
            data_files:
                - "datasets/composite/users.json"
                - "datasets/composite/setup_objects.json"
```

## Command Syntax

`$ cci task run composite_request`

## Options

`--data_files DATAFILES`

: _Required_

    A list of paths, where each path is a JSON file containing a
    composite request body.

`--managed MANAGED`

: _Optional_

    If True, replaces namespace tokens with the namespace prefix.

`--namespaced NAMESPACED`

: _Optional_

    If True, replaces namespace tokens with the namespace prefix.

`--randomize_username RANDOMIZEUSERNAME`

: _Optional_

    If True, randomize the TLD for any \'Username\' fields.

# **create_community**

**Description:** Creates a Community in the target org using the Connect
API

**Class:** cumulusci.tasks.salesforce.CreateCommunity

Create a Salesforce Community via the Connect API.

Specify the [template]{.title-ref} \"VF Template\" for Visualforce Tabs
community, or the name for a specific desired template

## Command Syntax

`$ cci task run create_community`

## Options

`--template TEMPLATE`

: _Required_

    Name of the template for the community.

`--name NAME`

: _Required_

    Name of the community.

`--description DESCRIPTION`

: _Optional_

    Description of the community.

`--url_path_prefix URLPATHPREFIX`

: _Optional_

    URL prefix for the community.

`--retries RETRIES`

: _Optional_

    Number of times to retry community creation request

`--timeout TIMEOUT`

: _Optional_

    Time to wait, in seconds, for the community to be created

`--skip_existing SKIPEXISTING`

: _Optional_

    If True, an existing community with the same name will not raise an
    exception.

# **connected_app**

**Description:** Creates the Connected App needed to use persistent orgs
in the CumulusCI keychain

**Class:** cumulusci.tasks.connectedapp.CreateConnectedApp

## Command Syntax

`$ cci task run connected_app`

## Options

`--label LABEL`

: _Required_

    The label for the connected app. Must contain only alphanumeric and
    underscores

    Default: CumulusCI

`--email EMAIL`

: _Optional_

    The email address to associate with the connected app. Defaults to
    email address from the github service if configured.

`--username USERNAME`

: _Optional_

    Create the connected app in a different org. Defaults to the
    defaultdevhubusername configured in sfdx.

`--connect CONNECT`

: _Optional_

    If True, the created connected app will be stored as the CumulusCI
    connected_app service in the keychain.

    Default: True

`--overwrite OVERWRITE`

: _Optional_

    If True, any existing connected_app service in the CumulusCI
    keychain will be overwritten. Has no effect if the connect option is
    False.

# **create_network_member_groups**

**Description:** Creates NetworkMemberGroup records which grant access
to an Experience Site (Community) for specified Profiles or Permission
Sets

**Class:**
cumulusci.tasks.salesforce.network_member_group.CreateNetworkMemberGroups

## Command Syntax

`$ cci task run create_network_member_groups`

## Options

`--network_name NETWORKNAME`

: _Required_

    Name of Network to add NetworkMemberGroup children records.

`--profile_names PROFILENAMES`

: _Optional_

    List of Profile Names to add as NetworkMemberGroups for this
    Network.

`--permission_set_names PERMISSIONSETNAMES`

: _Optional_

    List of PermissionSet Names to add as NetworkMemberGroups for this
    Network.

# **insert_record**

**Description:** Inserts a record of any sObject using the REST API

**Class:** cumulusci.tasks.salesforce.insert_record.InsertRecord

For example:

cci task run insert_record \--org dev -o object PermissionSet -o values
Name:HardDelete,PermissionsBulkApiHardDelete:true

## Command Syntax

`$ cci task run insert_record`

## Options

`--object OBJECT`

: _Required_

    An sObject type to insert

`--values VALUES`

: _Required_

    Field names and values in the format \'aa:bb,cc:dd\', or a YAML dict
    in cumulusci.yml.

`--tooling TOOLING`

: _Optional_

    If True, use the Tooling API instead of REST API.

# **create_package**

**Description:** Creates a package in the target org with the default
package name for the project

**Class:** cumulusci.tasks.salesforce.CreatePackage

## Command Syntax

`$ cci task run create_package`

## Options

`--package PACKAGE`

: _Required_

    The name of the package to create. Defaults to
    project\_\_package\_\_name

`--api_version APIVERSION`

: _Required_

    The api version to use when creating the package. Defaults to
    project\_\_package\_\_api_version

# **create_package_version**

**Description:** Uploads a 2nd-generation package (2GP) version

**Class:** cumulusci.tasks.create_package_version.CreatePackageVersion

## Command Syntax

`$ cci task run create_package_version`

## Options

`--package_type PACKAGETYPE`

: _Required_

    Package type (Unlocked or Managed)

`--package_name PACKAGENAME`

: _Optional_

    Name of package

`--namespace NAMESPACE`

: _Optional_

    Package namespace

`--version_name VERSIONNAME`

: _Optional_

    Version name

`--version_base VERSIONBASE`

: _Optional_

    The version number to use as a base before incrementing. Optional;
    defaults to the highest existing version number of this package. Can
    be set to `latest_github_release` to use the version of the most
    recent release published to GitHub.

`--version_type VERSIONTYPE`

: _Optional_

    The part of the version number to increment. Options are major,
    minor, patch, build. Defaults to build

`--skip_validation SKIPVALIDATION`

: _Optional_

    If true, skip validation of the package version. Default: false.
    Skipping validation creates packages more quickly, but they cannot
    be promoted for release.

`--org_dependent ORGDEPENDENT`

: _Optional_

    If true, create an org-dependent unlocked package. Default: false.

`--post_install_script POSTINSTALLSCRIPT`

: _Optional_

    Post-install script (for managed packages)

`--uninstall_script UNINSTALLSCRIPT`

: _Optional_

    Uninstall script (for managed packages)

`--force_upload FORCEUPLOAD`

: _Optional_

    If true, force creating a new package version even if one with the
    same contents already exists

`--static_resource_path STATICRESOURCEPATH`

: _Optional_

    The path where decompressed static resources are stored. Any
    subdirectories found will be zipped and added to the staticresources
    directory of the build.

`--ancestor_id ANCESTORID`

: _Optional_

    The 04t Id to use for the ancestor of this package. Optional;
    defaults to no ancestor specified. Can be set to
    `latest_github_release` to use the most recent production version
    published to GitHub.

`--resolution_strategy RESOLUTIONSTRATEGY`

: _Optional_

    The name of a sequence of resolution_strategy (from
    project\_\_dependency_resolutions) to apply to dynamic dependencies.
    Defaults to \'production\'.

`--create_unlocked_dependency_packages CREATEUNLOCKEDDEPENDENCYPACKAGES`

: _Optional_

    If True, create unlocked packages for unpackaged metadata in this
    project and dependencies. Defaults to False.

# **create_managed_src**

**Description:** Modifies the src directory for managed deployment.
Strips //cumulusci-managed from all Apex code

**Class:** cumulusci.tasks.metadata.managed_src.CreateManagedSrc

Apex classes which use the \@deprecated annotation can comment it out
using //cumulusci-managed so that it can be deployed as part of
unmanaged metadata, where this annotation is not allowed. This task is
for use when deploying to a packaging org to remove the comment so that
the annotation takes effect.

## Command Syntax

`$ cci task run create_managed_src`

## Options

`--path PATH`

: _Required_

    The path containing metadata to process for managed deployment

    Default: src

`--revert_path REVERTPATH`

: _Required_

    The path to copy the original metadata to for the revert call

    Default: src.orig

# **create_permission_set**

**Description:** Creates a Permission Set with specified User
Permissions and assigns it to the running user.

**Class:**
cumulusci.tasks.salesforce.create_permission_sets.CreatePermissionSet

## Command Syntax

`$ cci task run create_permission_set`

## Options

`--api_name APINAME`

: _Required_

    API name of generated Permission Set

`--user_permissions USERPERMISSIONS`

: _Required_

    List of User Permissions to include in the Permission Set.

`--label LABEL`

: _Optional_

    Label of generated Permission Set

# **create_bulk_data_permission_set**

**Description:** Creates a Permission Set with the Hard Delete and Set
Audit Fields user permissions. NOTE: the org setting to allow Set Audit
Fields must be turned on.

**Class:**
cumulusci.tasks.salesforce.create_permission_sets.CreatePermissionSet

## Command Syntax

`$ cci task run create_bulk_data_permission_set`

## Options

`--api_name APINAME`

: _Required_

    API name of generated Permission Set

    Default: CumulusCI_Bulk_Data

`--user_permissions USERPERMISSIONS`

: _Required_

    List of User Permissions to include in the Permission Set.

    Default: \[\'PermissionsBulkApiHardDelete\',
    \'PermissionsCreateAuditFields\'\]

`--label LABEL`

: _Optional_

    Label of generated Permission Set

    Default: CumulusCI Bulk Data

# **create_unmanaged_ee_src**

**Description:** Modifies the src directory for unmanaged deployment to
an EE org

**Class:** cumulusci.tasks.metadata.ee_src.CreateUnmanagedEESrc

## Command Syntax

`$ cci task run create_unmanaged_ee_src`

## Options

`--path PATH`

: _Required_

    The path containing metadata to process for managed deployment

    Default: src

`--revert_path REVERTPATH`

: _Required_

    The path to copy the original metadata to for the revert call

    Default: src.orig

# **create_blank_profile**

**Description:** Creates a blank profile, or a profile with no
permissions

**Class:** cumulusci.tasks.salesforce.profiles.CreateBlankProfile

## Command Syntax

`$ cci task run create_blank_profile`

## Options

`--name NAME`

: _Required_

    The name of the the new profile

`--license LICENSE`

: _Optional_

    The name of the salesforce license to use in the profile, defaults
    to \'Salesforce\'

    Default: Salesforce

`--license_id LICENSEID`

: _Optional_

    The ID of the salesforce license to use in the profile.

`--description DESCRIPTION`

: _Optional_

    The description of the the new profile

# **delete_data**

**Description:** Query existing data for a specific sObject and perform
a Bulk API delete of all matching records.

**Class:** cumulusci.tasks.bulkdata.DeleteData

## Command Syntax

`$ cci task run delete_data`

## Options

`--objects OBJECTS`

: _Required_

    A list of objects to delete records from in order of deletion. If
    passed via command line, use a comma separated string

`--where WHERE`

: _Optional_

    A SOQL where-clause (without the keyword WHERE). Only available when
    \'objects\' is length 1.

`--hardDelete HARDDELETE`

: _Optional_

    If True, perform a hard delete, bypassing the Recycle Bin. Note that
    this requires the Bulk API Hard Delete permission. Default: False

`--ignore_row_errors IGNOREROWERRORS`

: _Optional_

    If True, allow the operation to continue even if individual rows
    fail to delete.

`--inject_namespaces INJECTNAMESPACES`

: _Optional_

    If True, the package namespace prefix will be automatically added to
    (or removed from) objects and fields based on the name used in the
    org. Defaults to True.

`--api API`

: _Optional_

    The desired Salesforce API to use, which may be \'rest\', \'bulk\',
    or \'smart\' to auto-select based on record volume. The default is
    \'smart\'.

# **deploy**

**Description:** Deploys the src directory of the repository to the org

**Class:** cumulusci.tasks.salesforce.Deploy

## Command Syntax

`$ cci task run deploy`

## Options

`--path PATH`

: _Required_

    The path to the metadata source to be deployed

    Default: src

`--unmanaged UNMANAGED`

: _Optional_

    If True, changes namespace_inject to replace tokens with a blank
    string

`--namespace_inject NAMESPACEINJECT`

: _Optional_

    If set, the namespace tokens in files and filenames are replaced
    with the namespace\'s prefix

`--namespace_strip NAMESPACESTRIP`

: _Optional_

    If set, all namespace prefixes for the namespace specified are
    stripped from files and filenames

`--check_only CHECKONLY`

: _Optional_

    If True, performs a test deployment (validation) of components
    without saving the components in the target org

`--test_level TESTLEVEL`

: _Optional_

    Specifies which tests are run as part of a deployment. Valid values:
    NoTestRun, RunLocalTests, RunAllTestsInOrg, RunSpecifiedTests.

`--specified_tests SPECIFIEDTESTS`

: _Optional_

    Comma-separated list of test classes to run upon deployment. Applies
    only with test_level set to RunSpecifiedTests.

`--static_resource_path STATICRESOURCEPATH`

: _Optional_

    The path where decompressed static resources are stored. Any
    subdirectories found will be zipped and added to the staticresources
    directory of the build.

`--namespaced_org NAMESPACEDORG`

: _Optional_

    If True, the tokens %%%NAMESPACED_ORG%%% and
    \_\_\_NAMESPACED_ORG\_\_\_ will get replaced with the namespace. The
    default is false causing those tokens to get stripped and replaced
    with an empty string. Set this if deploying to a namespaced scratch
    org or packaging org.

`--clean_meta_xml CLEANMETAXML`

: _Optional_

    Defaults to True which strips the \<packageVersions/\> element from
    all meta.xml files. The packageVersion element gets added
    automatically by the target org and is set to whatever version is
    installed in the org. To disable this, set this option to False

# **deploy_marketing_cloud_package**

**Description:** Deploys a package zip file to a Marketing Cloud Tenant
via the Marketing Cloud Package Manager API.

**Class:**
cumulusci.tasks.marketing_cloud.deploy.MarketingCloudDeployTask

## Command Syntax

`$ cci task run deploy_marketing_cloud_package`

## Options

`--package_zip_file PACKAGEZIPFILE`

: _Required_

    Path to the package zipfile that will be deployed.

`--custom_inputs CUSTOMINPUTS`

: _Optional_

    Specify custom inputs to the deployment task. Takes a mapping from
    input key to input value (e.g.
    \'companyName:Acme,companyWebsite:<https://www.salesforce.org:8080>\').

`--name NAME`

: _Optional_

    The name to give to this particular deploy call. Defaults to a
    universally unique identifier.

`--endpoint ENDPOINT`

: _Optional_

    Override the default endpoint for the Marketing Cloud package
    manager API (optional)

# **marketing_cloud_create_subscriber_attribute**

**Description:** Creates a Subscriber Attribute via the Marketing Cloud
SOAP API.

**Class:** cumulusci.tasks.marketing_cloud.api.CreateSubscriberAttribute

## Command Syntax

`$ cci task run marketing_cloud_create_subscriber_attribute`

## Options

`--attribute_name ATTRIBUTENAME`

: _Required_

    The name of the Subscriber Attribute to deploy via the Marketing
    Cloud API.

# **marketing_cloud_create_user**

**Description:** Creates a new User via the Marketing Cloud SOAP API.

**Class:** cumulusci.tasks.marketing_cloud.api.CreateUser

## Command Syntax

`$ cci task run marketing_cloud_create_user`

## Options

`--parent_bu_mid PARENTBUMID`

: _Required_

    Specify the MID for Parent BU.

`--default_bu_mid DEFAULTBUMID`

: _Required_

    Set MID for BU to use as default (can be same as the parent).

`--user_email USEREMAIL`

: _Required_

    Set the User\'s email.

`--user_password USERPASSWORD`

: _Required_

    Set the User\'s password.

`--user_username USERUSERNAME`

: _Required_

    Set the User\'s username. Not the same as their name.

`--external_key EXTERNALKEY`

: _Optional_

    Set the User\'s external key.

`--user_name USERNAME`

: _Optional_

    Set the User\'s name. Not the same as their username.

`--role_id ROLEID`

: _Optional_

    Assign a Role to the new User, specified as an ID. IDs for system
    defined roles located here:
    <https://developer.salesforce.com/docs/atlas.en-us.noversion.mc-apis.meta/mc-apis/setting_user_permissions_via_the_web_services_api.htm>

# **marketing_cloud_update_user_role**

**Description:** Assigns a Role to an existing User via the Marketing
Cloud SOAP API.

**Class:** cumulusci.tasks.marketing_cloud.api.UpdateUserRole

## Command Syntax

`$ cci task run marketing_cloud_update_user_role`

## Options

`--account_mid ACCOUNTMID`

: _Required_

    Specify the Account MID.

`--user_email USEREMAIL`

: _Required_

    Specify the User\'s email.

`--user_password USERPASSWORD`

: _Required_

    Specify the User\'s password.

`--role_id ROLEID`

: _Required_

    Assign a Role to the User, specified as an ID. IDs for system
    defined roles located here:
    <https://developer.salesforce.com/docs/atlas.en-us.noversion.mc-apis.meta/mc-apis/setting_user_permissions_via_the_web_services_api.htm>

`--external_key EXTERNALKEY`

: _Optional_

    Specify the User\'s external key.

`--user_name USERNAME`

: _Optional_

    Specify the User\'s name. Not the same as their username.

# **deploy_pre**

**Description:** Deploys all metadata bundles under unpackaged/pre/

**Class:** cumulusci.tasks.salesforce.DeployBundles

## Command Syntax

`$ cci task run deploy_pre`

## Options

`--path PATH`

: _Required_

    The path to the parent directory containing the metadata bundles
    directories

    Default: unpackaged/pre

`--unmanaged UNMANAGED`

: _Optional_

    If True, changes namespace_inject to replace tokens with a blank
    string

`--namespace_inject NAMESPACEINJECT`

: _Optional_

    If set, the namespace tokens in files and filenames are replaced
    with the namespace\'s prefix

`--namespace_strip NAMESPACESTRIP`

: _Optional_

    If set, all namespace prefixes for the namespace specified are
    stripped from files and filenames

`--check_only CHECKONLY`

: _Optional_

    If True, performs a test deployment (validation) of components
    without saving the components in the target org

`--test_level TESTLEVEL`

: _Optional_

    Specifies which tests are run as part of a deployment. Valid values:
    NoTestRun, RunLocalTests, RunAllTestsInOrg, RunSpecifiedTests.

`--specified_tests SPECIFIEDTESTS`

: _Optional_

    Comma-separated list of test classes to run upon deployment. Applies
    only with test_level set to RunSpecifiedTests.

`--static_resource_path STATICRESOURCEPATH`

: _Optional_

    The path where decompressed static resources are stored. Any
    subdirectories found will be zipped and added to the staticresources
    directory of the build.

`--namespaced_org NAMESPACEDORG`

: _Optional_

    If True, the tokens %%%NAMESPACED_ORG%%% and
    \_\_\_NAMESPACED_ORG\_\_\_ will get replaced with the namespace. The
    default is false causing those tokens to get stripped and replaced
    with an empty string. Set this if deploying to a namespaced scratch
    org or packaging org.

`--clean_meta_xml CLEANMETAXML`

: _Optional_

    Defaults to True which strips the \<packageVersions/\> element from
    all meta.xml files. The packageVersion element gets added
    automatically by the target org and is set to whatever version is
    installed in the org. To disable this, set this option to False

# **deploy_post**

**Description:** Deploys all metadata bundles under unpackaged/post/

**Class:** cumulusci.tasks.salesforce.DeployBundles

## Command Syntax

`$ cci task run deploy_post`

## Options

`--path PATH`

: _Required_

    The path to the parent directory containing the metadata bundles
    directories

    Default: unpackaged/post

`--unmanaged UNMANAGED`

: _Optional_

    If True, changes namespace_inject to replace tokens with a blank
    string

`--namespace_inject NAMESPACEINJECT`

: _Optional_

    If set, the namespace tokens in files and filenames are replaced
    with the namespace\'s prefix

`--namespace_strip NAMESPACESTRIP`

: _Optional_

    If set, all namespace prefixes for the namespace specified are
    stripped from files and filenames

`--check_only CHECKONLY`

: _Optional_

    If True, performs a test deployment (validation) of components
    without saving the components in the target org

`--test_level TESTLEVEL`

: _Optional_

    Specifies which tests are run as part of a deployment. Valid values:
    NoTestRun, RunLocalTests, RunAllTestsInOrg, RunSpecifiedTests.

`--specified_tests SPECIFIEDTESTS`

: _Optional_

    Comma-separated list of test classes to run upon deployment. Applies
    only with test_level set to RunSpecifiedTests.

`--static_resource_path STATICRESOURCEPATH`

: _Optional_

    The path where decompressed static resources are stored. Any
    subdirectories found will be zipped and added to the staticresources
    directory of the build.

`--namespaced_org NAMESPACEDORG`

: _Optional_

    If True, the tokens %%%NAMESPACED_ORG%%% and
    \_\_\_NAMESPACED_ORG\_\_\_ will get replaced with the namespace. The
    default is false causing those tokens to get stripped and replaced
    with an empty string. Set this if deploying to a namespaced scratch
    org or packaging org.

`--clean_meta_xml CLEANMETAXML`

: _Optional_

    Defaults to True which strips the \<packageVersions/\> element from
    all meta.xml files. The packageVersion element gets added
    automatically by the target org and is set to whatever version is
    installed in the org. To disable this, set this option to False

# **deploy_qa_config**

**Description:** Deploys configuration for QA.

**Class:** cumulusci.tasks.salesforce.Deploy

## Command Syntax

`$ cci task run deploy_qa_config`

## Options

`--path PATH`

: _Required_

    The path to the metadata source to be deployed

    Default: unpackaged/config/qa

`--unmanaged UNMANAGED`

: _Optional_

    If True, changes namespace_inject to replace tokens with a blank
    string

`--namespace_inject NAMESPACEINJECT`

: _Optional_

    If set, the namespace tokens in files and filenames are replaced
    with the namespace\'s prefix

`--namespace_strip NAMESPACESTRIP`

: _Optional_

    If set, all namespace prefixes for the namespace specified are
    stripped from files and filenames

`--check_only CHECKONLY`

: _Optional_

    If True, performs a test deployment (validation) of components
    without saving the components in the target org

`--test_level TESTLEVEL`

: _Optional_

    Specifies which tests are run as part of a deployment. Valid values:
    NoTestRun, RunLocalTests, RunAllTestsInOrg, RunSpecifiedTests.

`--specified_tests SPECIFIEDTESTS`

: _Optional_

    Comma-separated list of test classes to run upon deployment. Applies
    only with test_level set to RunSpecifiedTests.

`--static_resource_path STATICRESOURCEPATH`

: _Optional_

    The path where decompressed static resources are stored. Any
    subdirectories found will be zipped and added to the staticresources
    directory of the build.

`--namespaced_org NAMESPACEDORG`

: _Optional_

    If True, the tokens %%%NAMESPACED_ORG%%% and
    \_\_\_NAMESPACED_ORG\_\_\_ will get replaced with the namespace. The
    default is false causing those tokens to get stripped and replaced
    with an empty string. Set this if deploying to a namespaced scratch
    org or packaging org.

`--clean_meta_xml CLEANMETAXML`

: _Optional_

    Defaults to True which strips the \<packageVersions/\> element from
    all meta.xml files. The packageVersion element gets added
    automatically by the target org and is set to whatever version is
    installed in the org. To disable this, set this option to False

# **dx**

**Description:** Execute an arbitrary Salesforce DX command against an
org. Use the \'command\' option to specify the command, such as
\'force:package:install\'

**Class:** cumulusci.tasks.sfdx.SFDXOrgTask

## Command Syntax

`$ cci task run dx`

## Options

`--command COMMAND`

: _Required_

    The full command to run with the sfdx cli.

`--extra EXTRA`

: _Optional_

    Append additional options to the command

# **dx_convert_to**

**Description:** Converts src directory metadata format into sfdx format
under force-app

**Class:** cumulusci.tasks.sfdx.SFDXBaseTask

## Command Syntax

`$ cci task run dx_convert_to`

## Options

`--command COMMAND`

: _Required_

    The full command to run with the sfdx cli.

    Default: force:mdapi:convert -r src

`--extra EXTRA`

: _Optional_

    Append additional options to the command

# **dx_convert_from**

**Description:** Converts force-app directory in sfdx format into
metadata format under src

**Class:** cumulusci.tasks.sfdx.SFDXBaseTask

## Command Syntax

`$ cci task run dx_convert_from`

## Options

`--command COMMAND`

: _Required_

    The full command to run with the sfdx cli.

    Default: force:source:convert -d src

`--extra EXTRA`

: _Optional_

    Append additional options to the command

# **dx_pull**

**Description:** Uses sfdx to pull from a scratch org into the force-app
directory

**Class:** cumulusci.tasks.sfdx.SFDXOrgTask

## Command Syntax

`$ cci task run dx_pull`

## Options

`--command COMMAND`

: _Required_

    The full command to run with the sfdx cli.

    Default: force:source:pull

`--extra EXTRA`

: _Optional_

    Append additional options to the command

# **dx_push**

**Description:** Uses sfdx to push the force-app directory metadata into
a scratch org

**Class:** cumulusci.tasks.sfdx.SFDXOrgTask

## Command Syntax

`$ cci task run dx_push`

## Options

`--command COMMAND`

: _Required_

    The full command to run with the sfdx cli.

    Default: force:source:push

`--extra EXTRA`

: _Optional_

    Append additional options to the command

# **enable_einstein_prediction**

**Description:** Enable an Einstein Prediction Builder prediction.

**Class:** cumulusci.tasks.salesforce.enable_prediction.EnablePrediction

This task updates the state of Einstein Prediction Builder predictions
from \'Draft\' to \'Enabled\' by posting to the Tooling API.

cci task run enable_prediction \--org dev -o api_names
Example_Prediction_v0

## Command Syntax

`$ cci task run enable_einstein_prediction`

## Options

`--api_names APINAMES`

: _Required_

    List of API names of the MLPredictionDefinitions.

`--managed MANAGED`

: _Optional_

    If False, changes namespace_inject to replace tokens with a blank
    string

`--namespaced_org NAMESPACEDORG`

: _Optional_

    If False, changes namespace_inject to replace namespaced-org tokens
    with a blank string

`--namespace_inject NAMESPACEINJECT`

: _Optional_

    If set, the namespace tokens in files and filenames are replaced
    with the namespace\'s prefix

# **ensure_record_types**

**Description:** Ensure that a default Record Type is extant on the
given standard sObject (custom objects are not supported). If Record
Types are already present, do nothing.

**Class:** cumulusci.tasks.salesforce.EnsureRecordTypes

## Command Syntax

`$ cci task run ensure_record_types`

## Options

`--record_type_developer_name RECORDTYPEDEVELOPERNAME`

: _Required_

    The Developer Name of the Record Type (unique). Must contain only
    alphanumeric characters and underscores.

    Default: Default

`--record_type_label RECORDTYPELABEL`

: _Required_

    The Label of the Record Type.

    Default: Default

`--sobject SOBJECT`

: _Required_

    The sObject on which to deploy the Record Type and optional Business
    Process.

`--record_type_description RECORDTYPEDESCRIPTION`

: _Optional_

    The Description of the Record Type. Only uses the first 255
    characters.

`--force_create FORCECREATE`

: _Optional_

    If true, the Record Type will be created even if a default Record
    Type already exists on this sObject. Defaults to False.

# **execute_anon**

**Description:** Execute anonymous apex via the tooling api.

**Class:** cumulusci.tasks.apex.anon.AnonymousApexTask

Use the [apex]{.title-ref} option to run a string of anonymous Apex. Use
the [path]{.title-ref} option to run anonymous Apex from a file. Or use
both to concatenate the string to the file contents.

## Command Syntax

`$ cci task run execute_anon`

## Options

`--path PATH`

: _Optional_

    The path to an Apex file to run.

`--apex APEX`

: _Optional_

    A string of Apex to run (after the file, if specified).

`--managed MANAGED`

: _Optional_

    If True, will insert the project\'s namespace prefix. Defaults to
    False or no namespace.

`--namespaced NAMESPACED`

: _Optional_

    If True, the tokens %%%NAMESPACED_RT%%% and %%%namespaced%%% will
    get replaced with the namespace prefix for Record Types.

`--param1 PARAM1`

: _Optional_

    Parameter to pass to the Apex. Use as %%%PARAM_1%%% in the Apex
    code. Defaults to an empty value.

`--param2 PARAM2`

: _Optional_

    Parameter to pass to the Apex. Use as %%%PARAM_2%%% in the Apex
    code. Defaults to an empty value.

# **generate_data_dictionary**

**Description:** Create a data dictionary for the project in CSV format.

**Class:** cumulusci.tasks.datadictionary.GenerateDataDictionary

Generate a data dictionary for the project by walking all GitHub
releases. The data dictionary is output as two CSV files. One, in
[object_path]{.title-ref}, includes

-   Object Label
-   Object API Name
-   Object Description
-   Version Introduced

with one row per packaged object.

The other, in [field_path]{.title-ref}, includes

-   Object Label
-   Object API Name
-   Field Label
-   Field API Name
-   Field Type
-   Valid Picklist Values
-   Help Text
-   Field Description
-   Version Introduced
-   Version Picklist Values Last Changed
-   Version Help Text Last Changed

Both MDAPI and SFDX format releases are supported.

## Command Syntax

`$ cci task run generate_data_dictionary`

## Options

`--object_path OBJECTPATH`

: _Optional_

    Path to a CSV file to contain an sObject-level data dictionary.

`--field_path FIELDPATH`

: _Optional_

    Path to a CSV file to contain an field-level data dictionary.

`--include_dependencies INCLUDEDEPENDENCIES`

: _Optional_

    Process all of the GitHub dependencies of this project and include
    their schema in the data dictionary.

`--additional_dependencies ADDITIONALDEPENDENCIES`

: _Optional_

    Include schema from additional GitHub repositories that are not
    explicit dependencies of this project to build a unified data
    dictionary. Specify as a list of dicts as in project\_\_dependencies
    in cumulusci.yml. Note: only repository dependencies are supported.

`--include_prerelease INCLUDEPRERELEASE`

: _Optional_

    Treat the current branch as containing prerelease schema, and
    included it as Prerelease in the data dictionary. NOTE: this option
    cannot be used with [additional_dependencies]{.title-ref} or
    [include_dependencies]{.title-ref}.

`--include_protected_schema INCLUDEPROTECTEDSCHEMA`

: _Optional_

    Include Custom Objects, Custom Settings, and Custom Metadata Types
    that are marked as Protected. Defaults to False.

# **generate_and_load_from_yaml**

**Description:** None

**Class:**
cumulusci.tasks.bulkdata.generate_and_load_data_from_yaml.GenerateAndLoadDataFromYaml

## Command Syntax

`$ cci task run generate_and_load_from_yaml`

## Options

`--data_generation_task DATAGENERATIONTASK`

: _Required_

    Fully qualified class path of a task to generate the data. Look at
    cumulusci.tasks.bulkdata.tests.dummy_data_factory to learn how to
    write them.

`--generator_yaml GENERATORYAML`

: _Required_

    A Snowfakery recipe file to use

`--num_records NUMRECORDS`

: _Optional_

    Target number of records. You will get at least this many records,
    but may get more. The recipe will always execute to completion, so
    if it creates 3 records per execution and you ask for 5, you will
    get 6.

`--num_records_tablename NUMRECORDSTABLENAME`

: _Optional_

    A string representing which table determines when the recipe
    execution is done.

`--batch_size BATCHSIZE`

: _Optional_

    How many records to create and load at a time.

`--data_generation_options DATAGENERATIONOPTIONS`

: _Optional_

    Options to pass to the data generator.

`--vars VARS`

: _Optional_

    Pass values to override options in the format VAR1:foo,VAR2:bar

`--replace_database REPLACEDATABASE`

: _Optional_

    Confirmation that it is okay to delete the data in database_url

`--working_directory WORKINGDIRECTORY`

: _Optional_

    Default path for temporary / working files

`--database_url DATABASEURL`

: _Optional_

    A path to put a copy of the sqlite database (for debugging)

`--mapping MAPPING`

: _Optional_

    A mapping YAML file to use

`--start_step STARTSTEP`

: _Optional_

    If specified, skip steps before this one in the mapping

`--sql_path SQLPATH`

: _Optional_

    If specified, a database will be created from an SQL script at the
    provided path

`--ignore_row_errors IGNOREROWERRORS`

: _Optional_

    If True, allow the load to continue even if individual rows fail to
    load.

`--reset_oids RESETOIDS`

: _Optional_

    If True (the default), and the \_sf_ids tables exist, reset them
    before continuing.

`--bulk_mode BULKMODE`

: _Optional_

    Set to Serial to force serial mode on all jobs. Parallel is the
    default.

`--inject_namespaces INJECTNAMESPACES`

: _Optional_

    If True, the package namespace prefix will be automatically added to
    (or removed from) objects and fields based on the name used in the
    org. Defaults to True.

`--drop_missing_schema DROPMISSINGSCHEMA`

: _Optional_

    Set to True to skip any missing objects or fields instead of
    stopping with an error.

`--set_recently_viewed SETRECENTLYVIEWED`

: _Optional_

    By default, the first 1000 records inserted via the Bulk API will be
    set as recently viewed. If fewer than 1000 records are inserted,
    existing objects of the same type being inserted will also be set as
    recently viewed.

`--generate_mapping_file GENERATEMAPPINGFILE`

: _Optional_

    A path to put a mapping file inferred from the generator_yaml

`--continuation_file CONTINUATIONFILE`

: _Optional_

    YAML file generated by Snowfakery representing next steps for data
    generation

`--generate_continuation_file GENERATECONTINUATIONFILE`

: _Optional_

    Path for Snowfakery to put its next continuation file

`--loading_rules LOADINGRULES`

: _Optional_

    Path to .load.yml file containing rules to use to load the file.
    Defaults to \<recipename\>.load.yml . Multiple files can be comma
    separated.

# **get_installed_packages**

**Description:** Retrieves a list of the currently installed managed
package namespaces and their versions

**Class:** cumulusci.tasks.preflight.packages.GetInstalledPackages

## Command Syntax

`$ cci task run get_installed_packages`

# **get_available_licenses**

**Description:** Retrieves a list of the currently available license
definition keys

**Class:** cumulusci.tasks.preflight.licenses.GetAvailableLicenses

## Command Syntax

`$ cci task run get_available_licenses`

# **get_available_permission_set_licenses**

**Description:** Retrieves a list of the currently available Permission
Set License definition keys

**Class:**
cumulusci.tasks.preflight.licenses.GetAvailablePermissionSetLicenses

## Command Syntax

`$ cci task run get_available_permission_set_licenses`

# **get_assigned_permission_sets**

**Description:** Retrieves a list of the names of any permission sets
assigned to the running user.

**Class:**
cumulusci.tasks.preflight.permsets.GetPermissionSetAssignments

## Command Syntax

`$ cci task run get_assigned_permission_sets`

# **get_available_permission_sets**

**Description:** Retrieves a list of the currently available Permission
Sets

**Class:** cumulusci.tasks.preflight.licenses.GetAvailablePermissionSets

## Command Syntax

`$ cci task run get_available_permission_sets`

# **get_existing_record_types**

**Description:** Retrieves all Record Types in the org as a dict, with
sObject names as keys and lists of Developer Names as values.

**Class:** cumulusci.tasks.preflight.recordtypes.CheckSObjectRecordTypes

## Command Syntax

`$ cci task run get_existing_record_types`

# **get_existing_sites**

**Description:** Retrieves a list of any existing Experience Cloud site
names in the org.

**Class:** cumulusci.tasks.salesforce.ListCommunities

Lists Communities for the current org via the Connect API.

## Command Syntax

`$ cci task run get_existing_sites`

# **github_parent_pr_notes**

**Description:** Merges the description of a child pull request to the
respective parent\'s pull request (if one exists).

**Class:** cumulusci.tasks.release_notes.task.ParentPullRequestNotes

Aggregate change notes from child pull request(s) to a corresponding
parent pull request.

When given the branch_name option, this task will: (1) check if the base
branch of the corresponding pull request starts with the feature branch
prefix and if so (2) attempt to query for a pull request corresponding
to this parent feature branch. (3) if a pull request isn\'t found, the
task exits and no actions are taken.

If the build_notes_label is present on the pull request, then all notes
from the child pull request are aggregated into the parent pull request.
if the build_notes_label is not detected on the parent pull request then
a link to the child pull request is placed under the \"Unaggregated Pull
Requests\" header.

If you have a pull request on branch feature/myFeature that you would
like to rebuild notes for use the branch_name and force options: cci
task run github_parent_pr_notes \--branch-name feature/myFeature
\--force True

## Command Syntax

`$ cci task run github_parent_pr_notes`

## Options

`--branch_name BRANCHNAME`

: _Required_

    Name of branch to check for parent status, and if so, reaggregate
    change notes from child branches.

`--build_notes_label BUILDNOTESLABEL`

: _Required_

    Name of the label that indicates that change notes on parent pull
    requests should be reaggregated when a child branch pull request is
    created.

`--force FORCE`

: _Optional_

    force rebuilding of change notes from child branches in the given
    branch.

# **github_clone_tag**

**Description:** Clones a github tag under a new name.

**Class:** cumulusci.tasks.github.CloneTag

## Command Syntax

`$ cci task run github_clone_tag`

## Options

`--src_tag SRCTAG`

: _Required_

    The source tag to clone. Ex: beta/1.0-Beta_2

`--tag TAG`

: _Required_

    The new tag to create by cloning the src tag. Ex: release/1.0

# **github_automerge_main**

**Description:** Merges the latest commit on the main branch into all
open feature branches

**Class:** cumulusci.tasks.github.MergeBranch

Merges the most recent commit on the current branch into other branches
depending on the value of source_branch.

If source_branch is a branch that does not start with the specified
branch_prefix, then the commit will be merged to all branches that begin
with branch_prefix and are not themselves child branches (i.e. branches
don\'t contain \'\_\_\' in their name).

If source_branch begins with branch_prefix, then the commit is merged to
all child branches of source_branch.

## Command Syntax

`$ cci task run github_automerge_main`

## Options

`--commit COMMIT`

: _Optional_

    The commit to merge into feature branches. Defaults to the current
    head commit.

`--source_branch SOURCEBRANCH`

: _Optional_

    The source branch to merge from. Defaults to
    project\_\_git\_\_default_branch.

`--branch_prefix BRANCHPREFIX`

: _Optional_

    A list of prefixes of branches that should receive the merge.
    Defaults to project\_\_git\_\_prefix_feature

`--skip_future_releases SKIPFUTURERELEASES`

: _Optional_

    If true, then exclude branches that start with the branch prefix if
    they are not for the lowest release number. Defaults to True.

`--update_future_releases UPDATEFUTURERELEASES`

: _Optional_

    If true, then include release branches that are not the lowest
    release number even if they are not child branches. Defaults to
    False.

# **github_automerge_feature**

**Description:** Merges the latest commit on a source branch to all
child branches.

**Class:** cumulusci.tasks.github.MergeBranch

Merges the most recent commit on the current branch into other branches
depending on the value of source_branch.

If source_branch is a branch that does not start with the specified
branch_prefix, then the commit will be merged to all branches that begin
with branch_prefix and are not themselves child branches (i.e. branches
don\'t contain \'\_\_\' in their name).

If source_branch begins with branch_prefix, then the commit is merged to
all child branches of source_branch.

## Command Syntax

`$ cci task run github_automerge_feature`

## Options

`--commit COMMIT`

: _Optional_

    The commit to merge into feature branches. Defaults to the current
    head commit.

`--source_branch SOURCEBRANCH`

: _Optional_

    The source branch to merge from. Defaults to
    project\_\_git\_\_default_branch.

    Default: \$project_config.repo_branch

`--branch_prefix BRANCHPREFIX`

: _Optional_

    A list of prefixes of branches that should receive the merge.
    Defaults to project\_\_git\_\_prefix_feature

`--skip_future_releases SKIPFUTURERELEASES`

: _Optional_

    If true, then exclude branches that start with the branch prefix if
    they are not for the lowest release number. Defaults to True.

`--update_future_releases UPDATEFUTURERELEASES`

: _Optional_

    If true, then include release branches that are not the lowest
    release number even if they are not child branches. Defaults to
    False.

# **github_copy_subtree**

**Description:** Copies one or more subtrees from the project repository
for a given release to a target repository, with the option to include
release notes.

**Class:** cumulusci.tasks.github.publish.PublishSubtree

## Command Syntax

`$ cci task run github_copy_subtree`

## Options

`--repo_url REPOURL`

: _Required_

    The url to the public repo

`--branch BRANCH`

: _Required_

    The branch to update in the target repo

`--version VERSION`

: _Optional_

    (Deprecated \>= 3.42.0) Only the values of \'latest\' and
    \'latest_beta\' are acceptable. Required if \'ref\' or \'tag_name\'
    is not set. This will override tag_name if it is provided.

`--tag_name TAGNAME`

: _Optional_

    The name of the tag that should be associated with this release.
    Values of \'latest\' and \'latest_beta\' are also allowed. Required
    if \'ref\' or \'version\' is not set.

`--ref REF`

: _Optional_

    The git reference to publish. Takes precedence over \'version\' and
    \'tag_name\'. Required if \'tag_name\' is not set.

`--include INCLUDE`

: _Optional_

    A list of paths from repo root to include. Directories must end with
    a trailing slash.

`--renames RENAMES`

: _Optional_

    A list of paths to rename in the target repo, given as
    [local:]{.title-ref} [target:]{.title-ref} pairs.

`--create_release CREATERELEASE`

: _Optional_

    If True, create a release in the public repo. Defaults to False

`--release_body RELEASEBODY`

: _Optional_

    If True, the entire release body will be published to the public
    repo. Defaults to False

`--dry_run DRYRUN`

: _Optional_

    If True, skip creating Github data. Defaults to False

# **github_package_data**

**Description:** Look up 2gp package dependencies for a version id
recorded in a commit status.

**Class:**
cumulusci.tasks.github.commit_status.GetPackageDataFromCommitStatus

## Command Syntax

`$ cci task run github_package_data`

## Options

`--context CONTEXT`

: _Required_

    Name of the commit status context

`--version_id VERSIONID`

: _Optional_

    Package version id

# **github_pull_requests**

**Description:** Lists open pull requests in project Github repository

**Class:** cumulusci.tasks.github.PullRequests

## Command Syntax

`$ cci task run github_pull_requests`

# **github_release**

**Description:** Creates a Github release for a given managed package
version number

**Class:** cumulusci.tasks.github.CreateRelease

## Command Syntax

`$ cci task run github_release`

## Options

`--version VERSION`

: _Required_

    The managed package version number. Ex: 1.2

`--package_type PACKAGETYPE`

: _Required_

    The package type of the project (either 1GP or 2GP)

`--tag_prefix TAGPREFIX`

: _Required_

    The prefix to use for the release tag created in github.

`--version_id VERSIONID`

: _Optional_

    The SubscriberPackageVersionId (04t) associated with this release.

`--message MESSAGE`

: _Optional_

    The message to attach to the created git tag

`--dependencies DEPENDENCIES`

: _Optional_

    List of dependencies to record in the tag message.

`--commit COMMIT`

: _Optional_

    Override the commit used to create the release. Defaults to the
    current local HEAD commit

`--resolution_strategy RESOLUTIONSTRATEGY`

: _Optional_

    The name of a sequence of resolution_strategy (from
    project\_\_dependency_resolutions) to apply to dynamic dependencies.
    Defaults to \'production\'.

# **gather_release_notes**

**Description:** Generates release notes by getting the latest release
of each repository

**Class:** cumulusci.tasks.release_notes.task.AllGithubReleaseNotes

## Command Syntax

`$ cci task run gather_release_notes`

## Options

`--repos REPOS`

: _Required_

    The list of owner, repo key pairs for which to generate release
    notes. Ex: \'owner\': SalesforceFoundation \'repo\': \'NPSP\'

# **github_release_notes**

**Description:** Generates release notes by parsing pull request bodies
of merged pull requests between two tags

**Class:** cumulusci.tasks.release_notes.task.GithubReleaseNotes

## Command Syntax

`$ cci task run github_release_notes`

## Options

`--tag TAG`

: _Required_

    The tag to generate release notes for. Ex: release/1.2

`--last_tag LASTTAG`

: _Optional_

    Override the last release tag. This is useful to generate release
    notes if you skipped one or more releases.

`--link_pr LINKPR`

: _Optional_

    If True, insert link to source pull request at end of each line.

`--publish PUBLISH`

: _Optional_

    Publish to GitHub release if True (default=False)

`--include_empty INCLUDEEMPTY`

: _Optional_

    If True, include links to PRs that have no release notes
    (default=False)

`--version_id VERSIONID`

: _Optional_

    The package version id used by the InstallLinksParser to add install
    urls

`--trial_info TRIALINFO`

: _Optional_

    If True, Includes trialforce template text for this product.

`--sandbox_date SANDBOXDATE`

: _Optional_

    The date of the sandbox release in ISO format (Will default to None)

`--production_date PRODUCTIONDATE`

: _Optional_

    The date of the production release in ISO format (Will default to
    None)

# **github_release_report**

**Description:** Parses GitHub release notes to report various info

**Class:** cumulusci.tasks.github.ReleaseReport

## Command Syntax

`$ cci task run github_release_report`

## Options

`--date_start DATESTART`

: _Optional_

    Filter out releases created before this date (YYYY-MM-DD)

`--date_end DATEEND`

: _Optional_

    Filter out releases created after this date (YYYY-MM-DD)

`--include_beta INCLUDEBETA`

: _Optional_

    Include beta releases in report \[default=False\]

`--print PRINT`

: _Optional_

    Print info to screen as JSON \[default=False\]

# **install_managed**

**Description:** Install the latest managed production release

**Class:** cumulusci.tasks.salesforce.InstallPackageVersion

## Command Syntax

`$ cci task run install_managed`

## Options

`--namespace NAMESPACE`

: _Required_

    The namespace of the package to install. Defaults to
    project\_\_package\_\_namespace

`--version VERSION`

: _Required_

    The version of the package to install. \"latest\" and
    \"latest_beta\" can be used to trigger lookup via Github Releases on
    the repository.

    Default: latest

`--name NAME`

: _Optional_

    The name of the package to install. Defaults to
    project\_\_package\_\_name_managed

`--version_number VERSIONNUMBER`

: _Optional_

    If installing a package using an 04t version Id, display this
    version number to the user and in logs. Has no effect otherwise.

`--activateRSS ACTIVATERSS`

: _Optional_

    Deprecated. Use activate_remote_site_settings instead.

`--retries RETRIES`

: _Optional_

    Number of retries (default=5)

`--retry_interval RETRYINTERVAL`

: _Optional_

    Number of seconds to wait before the next retry (default=5),

`--retry_interval_add RETRYINTERVALADD`

: _Optional_

    Number of seconds to add before each retry (default=30),

`--security_type SECURITYTYPE`

: _Optional_

    Which Profiles to install packages for (FULL = all profiles, NONE =
    admins only, PUSH = no profiles, CUSTOM = custom profiles). Defaults
    to FULL.

`--name_conflict_resolution NAMECONFLICTRESOLUTION`

: _Optional_

    Specify how to resolve name conflicts when installing an Unlocked
    Package. Available values are Block and RenameMetadata. Defaults to
    Block.

`--activate_remote_site_settings ACTIVATEREMOTESITESETTINGS`

: _Optional_

    Activate Remote Site Settings when installing a package. Defaults to
    True.

`--password PASSWORD`

: _Optional_

    The installation key for the managed package.

# **install_managed_beta**

**Description:** Installs the latest managed beta release

**Class:** cumulusci.tasks.salesforce.InstallPackageVersion

## Command Syntax

`$ cci task run install_managed_beta`

## Options

`--namespace NAMESPACE`

: _Required_

    The namespace of the package to install. Defaults to
    project\_\_package\_\_namespace

`--version VERSION`

: _Required_

    The version of the package to install. \"latest\" and
    \"latest_beta\" can be used to trigger lookup via Github Releases on
    the repository.

    Default: latest_beta

`--name NAME`

: _Optional_

    The name of the package to install. Defaults to
    project\_\_package\_\_name_managed

`--version_number VERSIONNUMBER`

: _Optional_

    If installing a package using an 04t version Id, display this
    version number to the user and in logs. Has no effect otherwise.

`--activateRSS ACTIVATERSS`

: _Optional_

    Deprecated. Use activate_remote_site_settings instead.

`--retries RETRIES`

: _Optional_

    Number of retries (default=5)

`--retry_interval RETRYINTERVAL`

: _Optional_

    Number of seconds to wait before the next retry (default=5),

`--retry_interval_add RETRYINTERVALADD`

: _Optional_

    Number of seconds to add before each retry (default=30),

`--security_type SECURITYTYPE`

: _Optional_

    Which Profiles to install packages for (FULL = all profiles, NONE =
    admins only, PUSH = no profiles, CUSTOM = custom profiles). Defaults
    to FULL.

`--name_conflict_resolution NAMECONFLICTRESOLUTION`

: _Optional_

    Specify how to resolve name conflicts when installing an Unlocked
    Package. Available values are Block and RenameMetadata. Defaults to
    Block.

`--activate_remote_site_settings ACTIVATEREMOTESITESETTINGS`

: _Optional_

    Activate Remote Site Settings when installing a package. Defaults to
    True.

`--password PASSWORD`

: _Optional_

    The installation key for the managed package.

# **list_communities**

**Description:** Lists Communities for the current org using the Connect
API.

**Class:** cumulusci.tasks.salesforce.ListCommunities

Lists Communities for the current org via the Connect API.

## Command Syntax

`$ cci task run list_communities`

# **list_community_templates**

**Description:** Prints the Community Templates available to the current
org

**Class:** cumulusci.tasks.salesforce.ListCommunityTemplates

Lists Salesforce Community templates available for the current org via
the Connect API.

## Command Syntax

`$ cci task run list_community_templates`

# **list_metadata_types**

**Description:** Prints the metadata types in a project

**Class:** cumulusci.tasks.util.ListMetadataTypes

## Command Syntax

`$ cci task run list_metadata_types`

## Options

`--package_xml PACKAGEXML`

: _Optional_

    The project package.xml file. Defaults to
    \<project_root\>/src/package.xml

# **meta_xml_apiversion**

**Description:** Set the API version in `*meta.xml` files

**Class:** cumulusci.tasks.metaxml.UpdateApi

## Command Syntax

`$ cci task run meta_xml_apiversion`

## Options

`--version VERSION`

: _Required_

    API version number e.g. 37.0

`--dir DIR`

: _Optional_

    Base directory to search for `*-meta.xml` files

# **meta_xml_dependencies**

**Description:** Set the version for dependent packages

**Class:** cumulusci.tasks.metaxml.UpdateDependencies

## Command Syntax

`$ cci task run meta_xml_dependencies`

## Options

`--dir DIR`

: _Optional_

    Base directory to search for `*-meta.xml` files

# **metadeploy_publish**

**Description:** Publish a release to the MetaDeploy web installer

**Class:** cumulusci.tasks.metadeploy.Publish

## Command Syntax

`$ cci task run metadeploy_publish`

## Options

`--tag TAG`

: _Optional_

    Name of the git tag to publish

`--commit COMMIT`

: _Optional_

    Commit hash to publish

`--plan PLAN`

: _Optional_

    Name of the plan(s) to publish. This refers to the
    [plans]{.title-ref} section of cumulusci.yml. By default, all plans
    will be published.

`--dry_run DRYRUN`

: _Optional_

    If True, print steps without publishing.

`--publish PUBLISH`

: _Optional_

    If True, set is_listed to True on the version. Default: False

`--labels_path LABELSPATH`

: _Optional_

    Path to a folder containing translations.

# **org_settings**

**Description:** Apply org settings from a scratch org definition file
or dict

**Class:** cumulusci.tasks.salesforce.org_settings.DeployOrgSettings

## Command Syntax

`$ cci task run org_settings`

## Options

`--definition_file DEFINITIONFILE`

: _Optional_

    sfdx scratch org definition file

`--settings SETTINGS`

: _Optional_

    A dict of settings to apply

`--api_version APIVERSION`

: _Optional_

    API version used to deploy the settings

# **promote_package_version**

**Description:** Promote a 2gp package so that it can be installed in a
production org

**Class:**
cumulusci.tasks.salesforce.promote_package_version.PromotePackageVersion

Promote a Second Generation package (managed or unlocked).

: Lists any 1GP dependencies that are detected, as well as any
dependency packages that have not been promoted. Once promoted, the
2GP package can be installed into production orgs.

## Command Syntax

`$ cci task run promote_package_version`

## Options

`--version_id VERSIONID`

: _Optional_

    The SubscriberPackageVersion (04t) Id for the target package.

`--promote_dependencies PROMOTEDEPENDENCIES`

: _Optional_

    Automatically promote any unpromoted versions of dependency 2GP
    packages that are detected.

# **publish_community**

**Description:** Publishes a Community in the target org using the
Connect API

**Class:** cumulusci.tasks.salesforce.PublishCommunity

Publish a Salesforce Community via the Connect API. Warning: This does
not work with the Community Template \'VF Template\' due to an existing
bug in the API.

## Command Syntax

`$ cci task run publish_community`

## Options

`--name NAME`

: _Optional_

    The name of the Community to publish.

`--community_id COMMUNITYID`

: _Optional_

    The id of the Community to publish.

# **push_all**

**Description:** Schedules a push upgrade of a package version to all
subscribers

**Class:** cumulusci.tasks.push.tasks.SchedulePushOrgQuery

## Command Syntax

`$ cci task run push_all`

## Options

`--version VERSION`

: _Required_

    The managed package version to push

`--subscriber_where SUBSCRIBERWHERE`

: _Optional_

    A SOQL style WHERE clause for filtering PackageSubscriber objects.
    Ex: OrgType = \'Sandbox\'

`--min_version MINVERSION`

: _Optional_

    If set, no subscriber with a version lower than min_version will be
    selected for push

`--metadata_package_id METADATAPACKAGEID`

: _Optional_

    The MetadataPackageId (ID prefix [033]{.title-ref}) to push.

`--namespace NAMESPACE`

: _Optional_

    The managed package namespace to push. Defaults to
    project\_\_package\_\_namespace.

`--start_time STARTTIME`

: _Optional_

    Set the start time (ISO-8601) to queue a future push. (Ex:
    2021-01-01T06:00Z or 2021-01-01T06:00-08:00) Times with no timezone
    will be interpreted as UTC.

`--dry_run DRYRUN`

: _Optional_

    If True, log how many orgs were selected but skip creating a
    PackagePushRequest. Defaults to False

# **push_list**

**Description:** Schedules a push upgrade of a package version to all
orgs listed in the specified file

**Class:** cumulusci.tasks.push.tasks.SchedulePushOrgList

## Command Syntax

`$ cci task run push_list`

## Options

`--csv CSV`

: _Optional_

    The path to a CSV file to read.

`--csv_field_name CSVFIELDNAME`

: _Optional_

    The CSV field name that contains organization IDs. Defaults to
    \'OrganizationID\'

`--orgs ORGS`

: _Optional_

    The path to a file containing one OrgID per line.

`--version VERSION`

: _Optional_

    The managed package version to push

`--version_id VERSIONID`

: _Optional_

    The MetadataPackageVersionId (ID prefix [04t]{.title-ref}) to push

`--metadata_package_id METADATAPACKAGEID`

: _Optional_

    The MetadataPackageId (ID prefix [033]{.title-ref}) to push.

`--namespace NAMESPACE`

: _Optional_

    The managed package namespace to push. Defaults to
    project\_\_package\_\_namespace.

`--start_time STARTTIME`

: _Optional_

    Set the start time (ISO-8601) to queue a future push. (Ex:
    2021-01-01T06:00Z or 2021-01-01T06:00-08:00) Times with no timezone
    will be interpreted as UTC.

`--batch_size BATCHSIZE`

: _Optional_

    Break pull requests into batches of this many orgs. Defaults to 200.

# **push_qa**

**Description:** Schedules a push upgrade of a package version to all
orgs listed in push/orgs_qa.txt

**Class:** cumulusci.tasks.push.tasks.SchedulePushOrgList

## Command Syntax

`$ cci task run push_qa`

## Options

`--csv CSV`

: _Optional_

    The path to a CSV file to read.

`--csv_field_name CSVFIELDNAME`

: _Optional_

    The CSV field name that contains organization IDs. Defaults to
    \'OrganizationID\'

`--orgs ORGS`

: _Optional_

    The path to a file containing one OrgID per line.

    Default: push/orgs_qa.txt

`--version VERSION`

: _Optional_

    The managed package version to push

`--version_id VERSIONID`

: _Optional_

    The MetadataPackageVersionId (ID prefix [04t]{.title-ref}) to push

`--metadata_package_id METADATAPACKAGEID`

: _Optional_

    The MetadataPackageId (ID prefix [033]{.title-ref}) to push.

`--namespace NAMESPACE`

: _Optional_

    The managed package namespace to push. Defaults to
    project\_\_package\_\_namespace.

`--start_time STARTTIME`

: _Optional_

    Set the start time (ISO-8601) to queue a future push. (Ex:
    2021-01-01T06:00Z or 2021-01-01T06:00-08:00) Times with no timezone
    will be interpreted as UTC.

`--batch_size BATCHSIZE`

: _Optional_

    Break pull requests into batches of this many orgs. Defaults to 200.

# **push_sandbox**

**Description:** Schedules a push upgrade of a package version to
sandbox orgs

**Class:** cumulusci.tasks.push.tasks.SchedulePushOrgQuery

## Command Syntax

`$ cci task run push_sandbox`

## Options

`--version VERSION`

: _Required_

    The managed package version to push

`--subscriber_where SUBSCRIBERWHERE`

: _Optional_

    A SOQL style WHERE clause for filtering PackageSubscriber objects.
    Ex: OrgType = \'Sandbox\'

    Default: OrgType = \'Sandbox\'

`--min_version MINVERSION`

: _Optional_

    If set, no subscriber with a version lower than min_version will be
    selected for push

`--metadata_package_id METADATAPACKAGEID`

: _Optional_

    The MetadataPackageId (ID prefix [033]{.title-ref}) to push.

`--namespace NAMESPACE`

: _Optional_

    The managed package namespace to push. Defaults to
    project\_\_package\_\_namespace.

`--start_time STARTTIME`

: _Optional_

    Set the start time (ISO-8601) to queue a future push. (Ex:
    2021-01-01T06:00Z or 2021-01-01T06:00-08:00) Times with no timezone
    will be interpreted as UTC.

`--dry_run DRYRUN`

: _Optional_

    If True, log how many orgs were selected but skip creating a
    PackagePushRequest. Defaults to False

# **push_trial**

**Description:** Schedules a push upgrade of a package version to
Trialforce Template orgs listed in push/orgs_trial.txt

**Class:** cumulusci.tasks.push.tasks.SchedulePushOrgList

## Command Syntax

`$ cci task run push_trial`

## Options

`--csv CSV`

: _Optional_

    The path to a CSV file to read.

`--csv_field_name CSVFIELDNAME`

: _Optional_

    The CSV field name that contains organization IDs. Defaults to
    \'OrganizationID\'

`--orgs ORGS`

: _Optional_

    The path to a file containing one OrgID per line.

    Default: push/orgs_trial.txt

`--version VERSION`

: _Optional_

    The managed package version to push

`--version_id VERSIONID`

: _Optional_

    The MetadataPackageVersionId (ID prefix [04t]{.title-ref}) to push

`--metadata_package_id METADATAPACKAGEID`

: _Optional_

    The MetadataPackageId (ID prefix [033]{.title-ref}) to push.

`--namespace NAMESPACE`

: _Optional_

    The managed package namespace to push. Defaults to
    project\_\_package\_\_namespace.

`--start_time STARTTIME`

: _Optional_

    Set the start time (ISO-8601) to queue a future push. (Ex:
    2021-01-01T06:00Z or 2021-01-01T06:00-08:00) Times with no timezone
    will be interpreted as UTC.

`--batch_size BATCHSIZE`

: _Optional_

    Break pull requests into batches of this many orgs. Defaults to 200.

# **push_failure_report**

**Description:** Produce a CSV report of the failed and otherwise
anomalous push jobs.

**Class:** cumulusci.tasks.push.pushfails.ReportPushFailures

## Command Syntax

`$ cci task run push_failure_report`

## Options

`--request_id REQUESTID`

: _Required_

    PackagePushRequest ID for the request you need to report on.

`--result_file RESULTFILE`

: _Optional_

    Path to write a CSV file with the results. Defaults to
    \'push_fails.csv\'.

`--ignore_errors IGNOREERRORS`

: _Optional_

    List of ErrorTitle and ErrorType values to omit from the report

    Default: \[\'Salesforce Subscription Expired\', \'Package
    Uninstalled\'\]

# **query**

**Description:** Queries the connected org

**Class:** cumulusci.tasks.salesforce.SOQLQuery

## Command Syntax

`$ cci task run query`

## Options

`--object OBJECT`

: _Required_

    The object to query

`--query QUERY`

: _Required_

    A valid bulk SOQL query for the object

`--result_file RESULTFILE`

: _Required_

    The name of the csv file to write the results to

# **retrieve_packaged**

**Description:** Retrieves the packaged metadata from the org

**Class:** cumulusci.tasks.salesforce.RetrievePackaged

## Command Syntax

`$ cci task run retrieve_packaged`

## Options

`--path PATH`

: _Required_

    The path to write the retrieved metadata

    Default: packaged

`--package PACKAGE`

: _Required_

    The package name to retrieve. Defaults to project\_\_package\_\_name

`--namespace_strip NAMESPACESTRIP`

: _Optional_

    If set, all namespace prefixes for the namespace specified are
    stripped from files and filenames

`--namespace_tokenize NAMESPACETOKENIZE`

: _Optional_

    If set, all namespace prefixes for the namespace specified are
    replaced with tokens for use with namespace_inject

`--namespaced_org NAMESPACEDORG`

: _Optional_

    If True, the tokens %%%NAMESPACED_ORG%%% and
    \_\_\_NAMESPACED_ORG\_\_\_ will get replaced with the namespace. The
    default is false causing those tokens to get stripped and replaced
    with an empty string. Set this if deploying to a namespaced scratch
    org or packaging org.

`--api_version APIVERSION`

: _Optional_

    Override the default api version for the retrieve. Defaults to
    project\_\_package\_\_api_version

# **retrieve_src**

**Description:** Retrieves the packaged metadata into the src directory

**Class:** cumulusci.tasks.salesforce.RetrievePackaged

## Command Syntax

`$ cci task run retrieve_src`

## Options

`--path PATH`

: _Required_

    The path to write the retrieved metadata

    Default: src

`--package PACKAGE`

: _Required_

    The package name to retrieve. Defaults to project\_\_package\_\_name

`--namespace_strip NAMESPACESTRIP`

: _Optional_

    If set, all namespace prefixes for the namespace specified are
    stripped from files and filenames

`--namespace_tokenize NAMESPACETOKENIZE`

: _Optional_

    If set, all namespace prefixes for the namespace specified are
    replaced with tokens for use with namespace_inject

`--namespaced_org NAMESPACEDORG`

: _Optional_

    If True, the tokens %%%NAMESPACED_ORG%%% and
    \_\_\_NAMESPACED_ORG\_\_\_ will get replaced with the namespace. The
    default is false causing those tokens to get stripped and replaced
    with an empty string. Set this if deploying to a namespaced scratch
    org or packaging org.

`--api_version APIVERSION`

: _Optional_

    Override the default api version for the retrieve. Defaults to
    project\_\_package\_\_api_version

# **retrieve_unpackaged**

**Description:** Retrieve the contents of a package.xml file.

**Class:** cumulusci.tasks.salesforce.RetrieveUnpackaged

## Command Syntax

`$ cci task run retrieve_unpackaged`

## Options

`--path PATH`

: _Required_

    The path to write the retrieved metadata

`--package_xml PACKAGEXML`

: _Required_

    The path to a package.xml manifest to use for the retrieve.

`--namespace_strip NAMESPACESTRIP`

: _Optional_

    If set, all namespace prefixes for the namespace specified are
    stripped from files and filenames

`--namespace_tokenize NAMESPACETOKENIZE`

: _Optional_

    If set, all namespace prefixes for the namespace specified are
    replaced with tokens for use with namespace_inject

`--namespaced_org NAMESPACEDORG`

: _Optional_

    If True, the tokens %%%NAMESPACED_ORG%%% and
    \_\_\_NAMESPACED_ORG\_\_\_ will get replaced with the namespace. The
    default is false causing those tokens to get stripped and replaced
    with an empty string. Set this if deploying to a namespaced scratch
    org or packaging org.

`--api_version APIVERSION`

: _Optional_

    Override the default api version for the retrieve. Defaults to
    project\_\_package\_\_api_version

# **list_changes**

**Description:** List the changes from a scratch org

**Class:** cumulusci.tasks.salesforce.sourcetracking.ListChanges

## Command Syntax

`$ cci task run list_changes`

## Options

`--include INCLUDE`

: _Optional_

    A comma-separated list of strings. Components will be included if
    one of these strings is part of either the metadata type or name.
    Example: `-o include CustomField,Admin` matches both
    `CustomField: Favorite_Color__c` and `Profile: Admin`

`--types TYPES`

: _Optional_

    A comma-separated list of metadata types to include.

`--exclude EXCLUDE`

: _Optional_

    Exclude changed components matching this string.

`--snapshot SNAPSHOT`

: _Optional_

    If True, all matching items will be set to be ignored at their
    current revision number. This will exclude them from the results
    unless a new edit is made.

# **retrieve_changes**

**Description:** Retrieve changed components from a scratch org

**Class:** cumulusci.tasks.salesforce.sourcetracking.RetrieveChanges

## Command Syntax

`$ cci task run retrieve_changes`

## Options

`--include INCLUDE`

: _Optional_

    A comma-separated list of strings. Components will be included if
    one of these strings is part of either the metadata type or name.
    Example: `-o include CustomField,Admin` matches both
    `CustomField: Favorite_Color__c` and `Profile: Admin`

`--types TYPES`

: _Optional_

    A comma-separated list of metadata types to include.

`--exclude EXCLUDE`

: _Optional_

    Exclude changed components matching this string.

`--snapshot SNAPSHOT`

: _Optional_

    If True, all matching items will be set to be ignored at their
    current revision number. This will exclude them from the results
    unless a new edit is made.

`--path PATH`

: _Optional_

    The path to write the retrieved metadata

`--api_version APIVERSION`

: _Optional_

    Override the default api version for the retrieve. Defaults to
    project\_\_package\_\_api_version

`--namespace_tokenize NAMESPACETOKENIZE`

: _Optional_

    If set, all namespace prefixes for the namespace specified are
    replaced with tokens for use with namespace_inject

# **retrieve_qa_config**

**Description:** Retrieves the current changes in the scratch org into
unpackaged/config/qa

**Class:** cumulusci.tasks.salesforce.sourcetracking.RetrieveChanges

## Command Syntax

`$ cci task run retrieve_qa_config`

## Options

`--include INCLUDE`

: _Optional_

    A comma-separated list of strings. Components will be included if
    one of these strings is part of either the metadata type or name.
    Example: `-o include CustomField,Admin` matches both
    `CustomField: Favorite_Color__c` and `Profile: Admin`

`--types TYPES`

: _Optional_

    A comma-separated list of metadata types to include.

`--exclude EXCLUDE`

: _Optional_

    Exclude changed components matching this string.

`--snapshot SNAPSHOT`

: _Optional_

    If True, all matching items will be set to be ignored at their
    current revision number. This will exclude them from the results
    unless a new edit is made.

`--path PATH`

: _Optional_

    The path to write the retrieved metadata

    Default: unpackaged/config/qa

`--api_version APIVERSION`

: _Optional_

    Override the default api version for the retrieve. Defaults to
    project\_\_package\_\_api_version

`--namespace_tokenize NAMESPACETOKENIZE`

: _Optional_

    If set, all namespace prefixes for the namespace specified are
    replaced with tokens for use with namespace_inject

    Default: \$project_config.project\_\_package\_\_namespace

# **set_field_help_text**

**Description:** Sets specified fields\' Help Text values.

**Class:** cumulusci.tasks.metadata_etl.help_text.SetFieldHelpText

## Command Syntax

`$ cci task run set_field_help_text`

## Options

`--fields FIELDS`

: _Required_

    List of object fields to affect, in Object\_\_c.Field\_\_c form.

`--overwrite OVERWRITE`

: _Optional_

    If set to True, overwrite any differing Help Text found on the
    field. By default, Help Text is set only if it is blank.

`--api_names APINAMES`

: _Optional_

    List of API names of entities to affect

`--managed MANAGED`

: _Optional_

    If False, changes namespace_inject to replace tokens with a blank
    string

`--namespace_inject NAMESPACEINJECT`

: _Optional_

    If set, the namespace tokens in files and filenames are replaced
    with the namespace\'s prefix

    Default: \$project_config.project\_\_package\_\_namespace

`--api_version APIVERSION`

: _Optional_

    Metadata API version to use, if not
    project\_\_package\_\_api_version.

# **snapshot_changes**

**Description:** Tell SFDX source tracking to ignore previous changes in
a scratch org

**Class:** cumulusci.tasks.salesforce.sourcetracking.SnapshotChanges

## Command Syntax

`$ cci task run snapshot_changes`

# **snowfakery**

**Description:** Generate and load data from a Snowfakery recipe

**Class:** cumulusci.tasks.bulkdata.snowfakery.Snowfakery

Do a data load with Snowfakery.

All options are optional.

The most commonly supplied options are [recipe]{.title-ref} and one of
the three [run_until\_\...]{.title-ref} options.

## Command Syntax

`$ cci task run snowfakery`

## Options

`--recipe RECIPE`

: _Required_

    Path to a Snowfakery recipe file determining what data to generate
    and load.

    Default: datasets/recipe.yml

`--run_until_records_in_org RUNUNTILRECORDSINORG`

: _Optional_

    \<sobject\>:\<count\>

    > Run the recipe repeatedly until the count of \<sobject\> in the
    > org matches the given \<count\>.
    >
    > For example, [\--run_until_records_in_org
    > Account:50_000]{.title-ref} means:
    >
    > Count the Account records in the org. Let's say the number is
    > 20,000. Thus, we must run the recipe over and over again until we
    > generate 30,000 new Account records. If the recipe also generates
    > e.g.Contacts, Opportunities or whatever else, it generates the
    > appropriate number of them to match.
    >
    > Underscores are allowed but optional in big numbers: 2000000 is
    > the same as 2_000_000.

`--run_until_records_loaded RUNUNTILRECORDSLOADED`

: _Optional_

    \<sobject\>:\<count\>

    > Run the recipe repeatedly until the number of records of
    > \<sobject\> uploaded in this task execution matches \<count\>.
    >
    > For example, [\--run_until_records_loaded
    > Account:50_000]{.title-ref} means:
    >
    > Run the recipe over and over again until we generate 50_000 new
    > Account records. If the recipe also generates e.g. Contacts,
    > Opportunities or whatever else, it generates the appropriate
    > number of them to match.

`--run_until_recipe_repeated RUNUNTILRECIPEREPEATED`

: _Optional_

    Run the recipe \<count\> times,

    :   no matter what data is already in the org.

        For example, [\--run_until_recipe_repeated 50_000]{.title-ref}
        means run the recipe 50_000 times.

`--working_directory WORKINGDIRECTORY`

: _Optional_

    Path for temporary / working files

`--loading_rules LOADINGRULES`

: _Optional_

    Path to .load.yml file containing rules to use to load the file.
    Defaults to [\<recipename\>.load.yml]{.title-ref}. Multiple files
    can be comma separated.

`--recipe_options RECIPEOPTIONS`

: _Optional_

    Pass values to override options in the format VAR1:foo,VAR2:bar

    > Example: \--recipe_options weight:10,color:purple

`--bulk_mode BULKMODE`

: _Optional_

    Set to Serial to force serial mode on all jobs. Parallel is the
    default.

`--drop_missing_schema DROPMISSINGSCHEMA`

: _Optional_

    Set to True to skip any missing objects or fields instead of
    stopping with an error.

`--num_processes NUMPROCESSES`

: _Optional_

    Number of data generating processes. Defaults to matching the number
    of CPUs.

`--ignore_row_errors IGNOREROWERRORS`

: _Optional_

    Boolean: should we continue loading even after running into row
    errors? Defaults to False.

# **revert_managed_src**

**Description:** Reverts the changes from create_managed_src

**Class:** cumulusci.tasks.metadata.managed_src.RevertManagedSrc

## Command Syntax

`$ cci task run revert_managed_src`

## Options

`--path PATH`

: _Required_

    The path containing metadata to process for managed deployment

    Default: src

`--revert_path REVERTPATH`

: _Required_

    The path to copy the original metadata to for the revert call

    Default: src.orig

# **revert_unmanaged_ee_src**

**Description:** Reverts the changes from create_unmanaged_ee_src

**Class:** cumulusci.tasks.metadata.ee_src.RevertUnmanagedEESrc

## Command Syntax

`$ cci task run revert_unmanaged_ee_src`

## Options

`--path PATH`

: _Required_

    The path containing metadata to process for managed deployment

    Default: src

`--revert_path REVERTPATH`

: _Required_

    The path to copy the original metadata to for the revert call

    Default: src.orig

# **robot**

**Description:** Runs a Robot Framework test from a .robot file

**Class:** cumulusci.tasks.robotframework.Robot

Runs Robot test cases using a browser, if necessary and stores its
results in a directory. The path to the directory can be retrieved from
the `robot_outputdir` return variable. Command Syntax
\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\--

`$ cci task run robot`

## Options

`--suites SUITES`

: _Required_

    Paths to test case files/directories to be executed similarly as
    when running the robot command on the command line. Defaults to
    \"tests\" to run all tests in the tests directory

    Default: tests

`--test TEST`

: _Optional_

    Run only tests matching name patterns. Can be comma separated and
    use robot wildcards like \*

`--include INCLUDE`

: _Optional_

    Includes tests with a given tag pattern

`--exclude EXCLUDE`

: _Optional_

    Excludes tests with a given tag pattern. Excluded tests will not
    appear in the logs and reports.

`--skip SKIP`

: _Optional_

    Do not run tests with the given tag pattern. Similar to \'exclude\',
    but skipped tests will appear in the logs and reports with the
    status of SKIP.

`--vars VARS`

: _Optional_

    Pass values to override variables in the format VAR1:foo,VAR2:bar

`--xunit XUNIT`

: _Optional_

    Set an XUnit format output file for test results

`--sources SOURCES`

: _Optional_

    List of sources defined in cumulusci.yml that are required by the
    robot task.

`--options OPTIONS`

: _Optional_

    A dictionary of options to robot.run method. In simple cases this
    can be specified on the comand line using name:value,name:value
    syntax. More complex cases can be specified in cumulusci.yml using
    YAML dictionary syntax.

`--name NAME`

: _Optional_

    Sets the name of the top level test suite

`--pdb PDB`

: _Optional_

    If true, run the Python debugger when tests fail.

`--verbose VERBOSE`

: _Optional_

    If true, log each keyword as it runs.

`--robot_debug ROBOTDEBUG`

: _Optional_

    If true, enable the [breakpoint]{.title-ref} keyword to enable the
    robot debugger

`--ordering ORDERING`

: _Optional_

    Path to a file which defines the order in which parallel tests are
    run. This maps directly to the pabot option of the same name. It is
    ignored unless the processes argument is set to 2 or greater.

`--processes PROCESSES`

: _Optional_

    *experimental* Number of processes to use for running tests in
    parallel. If this value is set to a number larger than 1 the tests
    will run using the open source tool pabot rather than
    robotframework. For example, -o parallel 2 will run half of the
    tests in one process and half in another. If not provided, all tests
    will run in a single process using the standard robot test runner.
    See <https://pabot.org/> for more information on pabot.

`--testlevelsplit TESTLEVELSPLIT`

: _Optional_

    If true, split parallel execution at the test level rather than the
    suite level. This option is ignored unless the processes option is
    set to 2 or greater. Note: this option requires a boolean value even
    though the pabot option of the same name does not.

# **robot_libdoc**

**Description:** Generates documentation for project keyword files

**Class:** cumulusci.tasks.robotframework.RobotLibDoc

## Command Syntax

`$ cci task run robot_libdoc`

## Options

`--path PATH`

: _Required_

    The path to one or more keyword libraries to be documented. The path
    can be single a python file, a .robot file, a python module (eg:
    cumulusci.robotframework.Salesforce) or a comma separated list of
    any of those. Glob patterns are supported for filenames (eg:
    `robot/SAL/doc/*PageObject.py`). The order of the files will be
    preserved in the generated documentation. The result of pattern
    expansion will be sorted

`--output OUTPUT`

: _Required_

    The output file where the documentation will be written

    Default: Keywords.html

`--title TITLE`

: _Optional_

    A string to use as the title of the generated output

    Default: \$project_config.project\_\_package\_\_name

# **robot_lint**

**Description:** Static analysis tool for robot framework files

**Class:** cumulusci.tasks.robotframework.RobotLint

The robot_lint task performs static analysis on one or more .robot and
.resource files. Each line is parsed, and the result passed through a
series of rules. Rules can issue warnings or errors about each line.

If any errors are reported, the task will exit with a non-zero status.

When a rule has been violated, a line will appear on the output in the
following format:

_\<severity\>_: _\<line\>_, _\<character\>_: _\<description\>_
(_\<name\>_)

-   _\<severity\>_ will be either W for warning or E for error
-   _\<line\>_ is the line number where the rule was triggered
-   _\<character\>_ is the character where the rule was triggered, or 0
    if the rule applies to the whole line
-   _\<description\>_ is a short description of the issue
-   _\<name\>_ is the name of the rule that raised the issue

Note: the rule name can be used with the ignore, warning, error, and
configure options.

Some rules are configurable, and can be configured with the
[configure]{.title-ref} option. This option takes a list of values in
the form _\<rule\>_:_\<value\>_,\*\<rule\>_:_\<value\>\*,etc. For
example, to set the line length for the LineTooLong rule you can use
\'-o configure LineTooLong:80\'. If a rule is configurable, it will show
the configuration options in the documentation for that rule

The filename will be printed once before any errors or warnings for that
file. The filename is preceeded by [+]{.title-ref}

Example Output:

    + example.robot
    W: 2, 0: No suite documentation (RequireSuiteDocumentation)
    E: 30, 0: No testcase documentation (RequireTestDocumentation)

To see a list of all configured rules, set the \'list\' option to True:

> cci task run robot_lint -o list True

## Command Syntax

`$ cci task run robot_lint`

## Options

`--configure CONFIGURE`

: _Optional_

    List of rule configuration values, in the form of rule:args.

`--ignore IGNORE`

: _Optional_

    List of rules to ignore. Use \'all\' to ignore all rules

`--error ERROR`

: _Optional_

    List of rules to treat as errors. Use \'all\' to affect all rules.

`--warning WARNING`

: _Optional_

    List of rules to treat as warnings. Use \'all\' to affect all rules.

`--list LIST`

: _Optional_

    If option is True, print a list of known rules instead of processing
    files.

`--path PATH`

: _Optional_

    The path to one or more files or folders. If the path includes
    wildcard characters, they will be expanded. If not provided, the
    default will be to process all files under robot/\<project name\>

# **robot_testdoc**

**Description:** Generates html documentation of your Robot test suite
and writes to tests/test_suite.

**Class:** cumulusci.tasks.robotframework.RobotTestDoc

## Command Syntax

`$ cci task run robot_testdoc`

## Options

`--path PATH`

: _Required_

    The path containing .robot test files

    Default: tests

`--output OUTPUT`

: _Required_

    The output html file where the documentation will be written

    Default: tests/test_suites.html

# **run_tests**

**Description:** Runs all apex tests

**Class:** cumulusci.tasks.apex.testrunner.RunApexTests

## Command Syntax

`$ cci task run run_tests`

## Options

`--test_name_match TESTNAMEMATCH`

: _Required_

    Pattern to find Apex test classes to run (\"%\" is wildcard).
    Defaults to project\_\_test\_\_name_match from project config.
    Comma-separated list for multiple patterns.

`--test_name_exclude TESTNAMEEXCLUDE`

: _Optional_

    Query to find Apex test classes to exclude (\"%\" is wildcard).
    Defaults to project\_\_test\_\_name_exclude from project config.
    Comma-separated list for multiple patterns.

`--namespace NAMESPACE`

: _Optional_

    Salesforce project namespace. Defaults to
    project\_\_package\_\_namespace

`--managed MANAGED`

: _Optional_

    If True, search for tests in the namespace only. Defaults to False

`--poll_interval POLLINTERVAL`

: _Optional_

    Seconds to wait between polling for Apex test results.

`--junit_output JUNITOUTPUT`

: _Optional_

    File name for JUnit output. Defaults to test_results.xml

`--json_output JSONOUTPUT`

: _Optional_

    File name for json output. Defaults to test_results.json

`--retry_failures RETRYFAILURES`

: _Optional_

    A list of regular expression patterns to match against test
    failures. If failures match, the failing tests are retried in serial
    mode.

`--retry_always RETRYALWAYS`

: _Optional_

    By default, all failures must match retry_failures to perform a
    retry. Set retry_always to True to retry all failed tests if any
    failure matches.

`-o required_org_code_coverage_percent PERCENTAGE`

: _Optional_

    Require at least X percent code coverage across the org following
    the test run.

`--verbose VERBOSE`

: _Optional_

    By default, only failures get detailed output. Set verbose to True
    to see all passed test methods.

# **set_duplicate_rule_status**

**Description:** Sets the active status of Duplicate Rules.

**Class:** cumulusci.tasks.metadata_etl.SetDuplicateRuleStatus

## Command Syntax

`$ cci task run set_duplicate_rule_status`

## Options

`--active ACTIVE`

: _Required_

    Boolean value, set the Duplicate Rule to either active or inactive

`--api_names APINAMES`

: _Optional_

    List of API names of entities to affect

`--managed MANAGED`

: _Optional_

    If False, changes namespace_inject to replace tokens with a blank
    string

`--namespace_inject NAMESPACEINJECT`

: _Optional_

    If set, the namespace tokens in files and filenames are replaced
    with the namespace\'s prefix

    Default: \$project_config.project\_\_package\_\_namespace

`--api_version APIVERSION`

: _Optional_

    Metadata API version to use, if not
    project\_\_package\_\_api_version.

# **set_organization_wide_defaults**

**Description:** Sets the Organization-Wide Defaults for specific
sObjects, and waits for sharing recalculation to complete.

**Class:** cumulusci.tasks.metadata_etl.SetOrgWideDefaults

## Command Syntax

`$ cci task run set_organization_wide_defaults`

## Options

`--org_wide_defaults ORGWIDEDEFAULTS`

: _Required_

    The target Organization-Wide Defaults, organized as a list with each
    element containing the keys api_name, internal_sharing_model, and
    external_sharing_model. NOTE: you must have External Sharing Model
    turned on in Sharing Settings to use the latter feature.

`--timeout TIMEOUT`

: _Optional_

    The max amount of time to wait in seconds

`--api_names APINAMES`

: _Optional_

    List of API names of entities to affect

`--managed MANAGED`

: _Optional_

    If False, changes namespace_inject to replace tokens with a blank
    string

`--namespace_inject NAMESPACEINJECT`

: _Optional_

    If set, the namespace tokens in files and filenames are replaced
    with the namespace\'s prefix

    Default: \$project_config.project\_\_package\_\_namespace

`--api_version APIVERSION`

: _Optional_

    Metadata API version to use, if not
    project\_\_package\_\_api_version.

# **uninstall_managed**

**Description:** Uninstalls the managed version of the package

**Class:** cumulusci.tasks.salesforce.UninstallPackage

## Command Syntax

`$ cci task run uninstall_managed`

## Options

`--namespace NAMESPACE`

: _Required_

    The namespace of the package to uninstall. Defaults to
    project\_\_package\_\_namespace

`--purge_on_delete PURGEONDELETE`

: _Required_

    Sets the purgeOnDelete option for the deployment. Defaults to True

# **uninstall_packaged**

**Description:** Uninstalls all deleteable metadata in the package in
the target org

**Class:** cumulusci.tasks.salesforce.UninstallPackaged

## Command Syntax

`$ cci task run uninstall_packaged`

## Options

`--package PACKAGE`

: _Required_

    The package name to uninstall. All metadata from the package will be
    retrieved and a custom destructiveChanges.xml package will be
    constructed and deployed to delete all deleteable metadata from the
    package. Defaults to project\_\_package\_\_name

`--purge_on_delete PURGEONDELETE`

: _Required_

    Sets the purgeOnDelete option for the deployment. Defaults to True

`--dry_run DRYRUN`

: _Optional_

    Perform a dry run of the operation without actually deleting any
    components, and display the components that would be deleted.

# **uninstall_packaged_incremental**

**Description:** Deletes any metadata from the package in the target org
not in the local workspace

**Class:** cumulusci.tasks.salesforce.UninstallPackagedIncremental

## Command Syntax

`$ cci task run uninstall_packaged_incremental`

## Options

`--path PATH`

: _Required_

    The local path to compare to the retrieved packaged metadata from
    the org. Defaults to src

`--package PACKAGE`

: _Required_

    The package name to uninstall. All metadata from the package will be
    retrieved and a custom destructiveChanges.xml package will be
    constructed and deployed to delete all deleteable metadata from the
    package. Defaults to project\_\_package\_\_name

`--purge_on_delete PURGEONDELETE`

: _Required_

    Sets the purgeOnDelete option for the deployment. Defaults to True

`--ignore IGNORE`

: _Optional_

    Components to ignore in the org and not try to delete. Mapping of
    component type to a list of member names.

`--ignore_types IGNORETYPES`

: _Optional_

    List of component types to ignore in the org and not try to delete.
    Defaults to \[\'RecordType\', \'CustomObjectTranslation\'\]

`--dry_run DRYRUN`

: _Optional_

    Perform a dry run of the operation without actually deleting any
    components, and display the components that would be deleted.

# **uninstall_src**

**Description:** Uninstalls all metadata in the local src directory

**Class:** cumulusci.tasks.salesforce.UninstallLocal

## Command Syntax

`$ cci task run uninstall_src`

## Options

`--path PATH`

: _Required_

    The path to the metadata source to be deployed

    Default: src

`--unmanaged UNMANAGED`

: _Optional_

    If True, changes namespace_inject to replace tokens with a blank
    string

`--namespace_inject NAMESPACEINJECT`

: _Optional_

    If set, the namespace tokens in files and filenames are replaced
    with the namespace\'s prefix

`--namespace_strip NAMESPACESTRIP`

: _Optional_

    If set, all namespace prefixes for the namespace specified are
    stripped from files and filenames

`--check_only CHECKONLY`

: _Optional_

    If True, performs a test deployment (validation) of components
    without saving the components in the target org

`--test_level TESTLEVEL`

: _Optional_

    Specifies which tests are run as part of a deployment. Valid values:
    NoTestRun, RunLocalTests, RunAllTestsInOrg, RunSpecifiedTests.

`--specified_tests SPECIFIEDTESTS`

: _Optional_

    Comma-separated list of test classes to run upon deployment. Applies
    only with test_level set to RunSpecifiedTests.

`--static_resource_path STATICRESOURCEPATH`

: _Optional_

    The path where decompressed static resources are stored. Any
    subdirectories found will be zipped and added to the staticresources
    directory of the build.

`--namespaced_org NAMESPACEDORG`

: _Optional_

    If True, the tokens %%%NAMESPACED_ORG%%% and
    \_\_\_NAMESPACED_ORG\_\_\_ will get replaced with the namespace. The
    default is false causing those tokens to get stripped and replaced
    with an empty string. Set this if deploying to a namespaced scratch
    org or packaging org.

`--clean_meta_xml CLEANMETAXML`

: _Optional_

    Defaults to True which strips the \<packageVersions/\> element from
    all meta.xml files. The packageVersion element gets added
    automatically by the target org and is set to whatever version is
    installed in the org. To disable this, set this option to False

`--purge_on_delete PURGEONDELETE`

: _Optional_

    Sets the purgeOnDelete option for the deployment. Defaults to True

`--dry_run DRYRUN`

: _Optional_

    Perform a dry run of the operation without actually deleting any
    components, and display the components that would be deleted.

# **uninstall_pre**

**Description:** Uninstalls the unpackaged/pre bundles

**Class:** cumulusci.tasks.salesforce.UninstallLocalBundles

## Command Syntax

`$ cci task run uninstall_pre`

## Options

`--path PATH`

: _Required_

    The path to the metadata source to be deployed

    Default: unpackaged/pre

`--unmanaged UNMANAGED`

: _Optional_

    If True, changes namespace_inject to replace tokens with a blank
    string

`--namespace_inject NAMESPACEINJECT`

: _Optional_

    If set, the namespace tokens in files and filenames are replaced
    with the namespace\'s prefix

`--namespace_strip NAMESPACESTRIP`

: _Optional_

    If set, all namespace prefixes for the namespace specified are
    stripped from files and filenames

`--check_only CHECKONLY`

: _Optional_

    If True, performs a test deployment (validation) of components
    without saving the components in the target org

`--test_level TESTLEVEL`

: _Optional_

    Specifies which tests are run as part of a deployment. Valid values:
    NoTestRun, RunLocalTests, RunAllTestsInOrg, RunSpecifiedTests.

`--specified_tests SPECIFIEDTESTS`

: _Optional_

    Comma-separated list of test classes to run upon deployment. Applies
    only with test_level set to RunSpecifiedTests.

`--static_resource_path STATICRESOURCEPATH`

: _Optional_

    The path where decompressed static resources are stored. Any
    subdirectories found will be zipped and added to the staticresources
    directory of the build.

`--namespaced_org NAMESPACEDORG`

: _Optional_

    If True, the tokens %%%NAMESPACED_ORG%%% and
    \_\_\_NAMESPACED_ORG\_\_\_ will get replaced with the namespace. The
    default is false causing those tokens to get stripped and replaced
    with an empty string. Set this if deploying to a namespaced scratch
    org or packaging org.

`--clean_meta_xml CLEANMETAXML`

: _Optional_

    Defaults to True which strips the \<packageVersions/\> element from
    all meta.xml files. The packageVersion element gets added
    automatically by the target org and is set to whatever version is
    installed in the org. To disable this, set this option to False

`--purge_on_delete PURGEONDELETE`

: _Optional_

    Sets the purgeOnDelete option for the deployment. Defaults to True

`--dry_run DRYRUN`

: _Optional_

    Perform a dry run of the operation without actually deleting any
    components, and display the components that would be deleted.

# **uninstall_post**

**Description:** Uninstalls the unpackaged/post bundles

**Class:** cumulusci.tasks.salesforce.UninstallLocalNamespacedBundles

## Command Syntax

`$ cci task run uninstall_post`

## Options

`--path PATH`

: _Required_

    The path to a directory containing the metadata bundles
    (subdirectories) to uninstall

    Default: unpackaged/post

`--filename_token FILENAMETOKEN`

: _Required_

    The path to the parent directory containing the metadata bundles
    directories

    Default: \_\_\_NAMESPACE\_\_\_

`--purge_on_delete PURGEONDELETE`

: _Required_

    Sets the purgeOnDelete option for the deployment. Defaults to True

`--managed MANAGED`

: _Optional_

    If True, will insert the actual namespace prefix. Defaults to False
    or no namespace

`--namespace NAMESPACE`

: _Optional_

    The namespace to replace the token with if in managed mode. Defaults
    to project\_\_package\_\_namespace

# **unschedule_apex**

**Description:** Unschedule all scheduled apex jobs (CronTriggers).

**Class:** cumulusci.tasks.apex.anon.AnonymousApexTask

Use the [apex]{.title-ref} option to run a string of anonymous Apex. Use
the [path]{.title-ref} option to run anonymous Apex from a file. Or use
both to concatenate the string to the file contents.

## Command Syntax

`$ cci task run unschedule_apex`

## Options

`--path PATH`

: _Optional_

    The path to an Apex file to run.

`--apex APEX`

: _Optional_

    A string of Apex to run (after the file, if specified).

    Default: for (CronTrigger t : \[SELECT Id FROM CronTrigger\]) {
    System.abortJob(t.Id); }

`--managed MANAGED`

: _Optional_

    If True, will insert the project\'s namespace prefix. Defaults to
    False or no namespace.

`--namespaced NAMESPACED`

: _Optional_

    If True, the tokens %%%NAMESPACED_RT%%% and %%%namespaced%%% will
    get replaced with the namespace prefix for Record Types.

`--param1 PARAM1`

: _Optional_

    Parameter to pass to the Apex. Use as %%%PARAM_1%%% in the Apex
    code. Defaults to an empty value.

`--param2 PARAM2`

: _Optional_

    Parameter to pass to the Apex. Use as %%%PARAM_2%%% in the Apex
    code. Defaults to an empty value.

# **update_admin_profile**

**Description:** Retrieves, edits, and redeploys the Admin.profile with
full FLS perms for all objects/fields

**Class:** cumulusci.tasks.salesforce.ProfileGrantAllAccess

## Command Syntax

`$ cci task run update_admin_profile`

## Options

`--package_xml PACKAGEXML`

: _Optional_

    Override the default package.xml file for retrieving the
    Admin.profile and all objects and classes that need to be included
    by providing a path to your custom package.xml

`--record_types RECORDTYPES`

: _Optional_

    A list of dictionaries containing the required key
    [record_type]{.title-ref} with a value specifying the record type in
    format \<object\>.\<developer_name\>. Record type names can use the
    token strings {managed} and {namespaced_org} for namespace prefix
    injection as needed. By default, all listed record types will be set
    to visible and not default. Use the additional keys
    [visible]{.title-ref}, [default]{.title-ref}, and
    [person_account_default]{.title-ref} set to true/false to override.
    NOTE: Setting record_types is only supported in cumulusci.yml,
    command line override is not supported.

`--managed MANAGED`

: _Optional_

    If True, uses the namespace prefix where appropriate. Use if running
    against an org with the managed package installed. Defaults to False

`--namespaced_org NAMESPACEDORG`

: _Optional_

    If True, attempts to prefix all unmanaged metadata references with
    the namespace prefix for deployment to the packaging org or a
    namespaced scratch org. Defaults to False

`--namespace_inject NAMESPACEINJECT`

: _Optional_

    If set, the namespace tokens in files and filenames are replaced
    with the namespace\'s prefix. Defaults to
    project\_\_package\_\_namespace

`--profile_name PROFILENAME`

: _Optional_

    Name of the Profile to target for updates (deprecated; use api_names
    to target multiple profiles).

`--include_packaged_objects INCLUDEPACKAGEDOBJECTS`

: _Optional_

    Automatically include objects from all installed managed packages.
    Defaults to True in projects that require CumulusCI 3.9.0 and
    greater that don\'t use a custom package.xml, otherwise False.

`--api_names APINAMES`

: _Optional_

    List of API names of Profiles to affect

# **update_dependencies**

**Description:** Installs all dependencies in project\_\_dependencies
into the target org

**Class:** cumulusci.tasks.salesforce.UpdateDependencies

## Command Syntax

`$ cci task run update_dependencies`

## Options

`--dependencies DEPENDENCIES`

: _Optional_

    List of dependencies to update. Defaults to project\_\_dependencies.
    Each dependency is a dict with either \'github\' set to a github
    repository URL or \'namespace\' set to a Salesforce package
    namespace. GitHub dependencies may include \'tag\' to install a
    particular git ref. Package dependencies may include \'version\' to
    install a particular version.

`--ignore_dependencies IGNOREDEPENDENCIES`

: _Optional_

    List of dependencies to be ignored, including if they are present as
    transitive dependencies. Dependencies can be specified using the
    \'github\' or \'namespace\' keys (all other keys are not used). Note
    that this can cause installations to fail if required prerequisites
    are not available.

`--purge_on_delete PURGEONDELETE`

: _Optional_

    Sets the purgeOnDelete option for the deployment. Defaults to True

`--include_beta INCLUDEBETA`

: _Optional_

    Install the most recent release, even if beta. Defaults to False.
    This option is only supported for scratch orgs, to avoid installing
    a package that can\'t be upgraded in persistent orgs.

`--allow_newer ALLOWNEWER`

: _Optional_

    Deprecated. This option has no effect.

`--prefer_2gp_from_release_branch PREFER2GPFROMRELEASEBRANCH`

: _Optional_

    If True and this build is on a release branch (feature/NNN, where
    NNN is an integer), or a child branch of a release branch, resolve
    GitHub managed package dependencies to 2GP builds present on a
    matching release branch on the dependency.

`--resolution_strategy RESOLUTIONSTRATEGY`

: _Optional_

    The name of a sequence of resolution_strategy (from
    project\_\_dependency_resolutions) to apply to dynamic dependencies.

`--packages_only PACKAGESONLY`

: _Optional_

    Install only packaged dependencies. Ignore all unmanaged metadata.
    Defaults to False.

`--security_type SECURITYTYPE`

: _Optional_

    Which Profiles to install packages for (FULL = all profiles, NONE =
    admins only, PUSH = no profiles, CUSTOM = custom profiles). Defaults
    to FULL.

`--name_conflict_resolution NAMECONFLICTRESOLUTION`

: _Optional_

    Specify how to resolve name conflicts when installing an Unlocked
    Package. Available values are Block and RenameMetadata. Defaults to
    Block.

`--activate_remote_site_settings ACTIVATEREMOTESITESETTINGS`

: _Optional_

    Activate Remote Site Settings when installing a package. Defaults to
    True.

# **update_metadata_first_child_text**

**Description:** Updates the text of the first child of Metadata with
matching tag. Adds a child for tag if it does not exist.

**Class:** cumulusci.tasks.metadata_etl.UpdateMetadataFirstChildTextTask

Metadata ETL task to update a single child element\'s text within
metadata XML.

If the child doesn\'t exist, the child is created and appended to the
Metadata. Furthermore, the `value` option is namespaced injected if the
task is properly configured.

## Example: Assign a Custom Object\'s Compact Layout

Researching
[CustomObject](https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/customobject.htm)
in the Metadata API documentation or even retrieving the CustomObject\'s
Metadata for inspection, we see the `compactLayoutAssignment` Field. We
want to assign a specific Compact Layout for our Custom Object, so we
write the following CumulusCI task in our project\'s `cumulusci.yml`.

```yaml
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
```

Suppose the original CustomObject metadata XML looks like:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    ...
    <label>Our Custom Object</label>
    <compactLayoutAssignment>OriginalCompactLayout</compactLayoutAssignment>
    ...
</CustomObject>
```

After running `cci task run assign_compact_layout`, the CustomObject
metadata XML is deployed as:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    ...
    <label>Our Custom Object</label>
    <compactLayoutAssignment>DifferentCompactLayout</compactLayoutAssignment>
    ...
</CustomObject>
```

## Command Syntax

`$ cci task run update_metadata_first_child_text`

## Options

`--metadata_type METADATATYPE`

: _Required_

    Metadata Type

`--tag TAG`

: _Required_

    Targeted tag. The text of the first instance of this tag within the
    metadata entity will be updated.

`--value VALUE`

: _Required_

    Desired value to set for the targeted tag\'s text. This value is
    namespace-injected.

`--api_names APINAMES`

: _Optional_

    List of API names of entities to affect

`--managed MANAGED`

: _Optional_

    If False, changes namespace_inject to replace tokens with a blank
    string

`--namespace_inject NAMESPACEINJECT`

: _Optional_

    If set, the namespace tokens in files and filenames are replaced
    with the namespace\'s prefix

    Default: \$project_config.project\_\_package\_\_namespace

`--api_version APIVERSION`

: _Optional_

    Metadata API version to use, if not
    project\_\_package\_\_api_version.

# **update_package_xml**

**Description:** Updates src/package.xml with metadata in src/

**Class:** cumulusci.tasks.metadata.package.UpdatePackageXml

## Command Syntax

`$ cci task run update_package_xml`

## Options

`--path PATH`

: _Required_

    The path to a folder of metadata to build the package.xml from

    Default: src

`--output OUTPUT`

: _Optional_

    The output file, defaults to \<path\>/package.xml

`--package_name PACKAGENAME`

: _Optional_

    If set, overrides the package name inserted into the \<fullName\>
    element

`--managed MANAGED`

: _Optional_

    If True, generate a package.xml for deployment to the managed
    package packaging org

`--delete DELETE`

: _Optional_

    If True, generate a package.xml for use as a destructiveChanges.xml
    file for deleting metadata

# **upload_beta**

**Description:** Uploads a beta release of the metadata currently in the
packaging org

**Class:** cumulusci.tasks.salesforce.PackageUpload

## Command Syntax

`$ cci task run upload_beta`

## Options

`--name NAME`

: _Required_

    The name of the package version.

`--production PRODUCTION`

: _Optional_

    If True, uploads a production release. Defaults to uploading a beta

`--description DESCRIPTION`

: _Optional_

    A description of the package and what this version contains.

`--password PASSWORD`

: _Optional_

    An optional password for sharing the package privately with anyone
    who has the password. Don\'t enter a password if you want to make
    the package available to anyone on AppExchange and share your
    package publicly.

`--post_install_url POSTINSTALLURL`

: _Optional_

    The fully-qualified URL of the post-installation instructions.
    Instructions are shown as a link after installation and are
    available from the package detail view.

`--release_notes_url RELEASENOTESURL`

: _Optional_

    The fully-qualified URL of the package release notes. Release notes
    are shown as a link during the installation process and are
    available from the package detail view after installation.

`--namespace NAMESPACE`

: _Optional_

    The namespace of the package. Defaults to
    project\_\_package\_\_namespace

`--resolution_strategy RESOLUTIONSTRATEGY`

: _Optional_

    The name of a sequence of resolution_strategy (from
    project\_\_dependency_resolutions) to apply to dynamic dependencies.
    Defaults to \'production\'.

# **upload_production**

**Description:** Uploads a production release of the metadata currently
in the packaging org

**Class:** cumulusci.tasks.salesforce.PackageUpload

## Command Syntax

`$ cci task run upload_production`

## Options

`--name NAME`

: _Required_

    The name of the package version.

    Default: Release

`--production PRODUCTION`

: _Optional_

    If True, uploads a production release. Defaults to uploading a beta

    Default: True

`--description DESCRIPTION`

: _Optional_

    A description of the package and what this version contains.

`--password PASSWORD`

: _Optional_

    An optional password for sharing the package privately with anyone
    who has the password. Don\'t enter a password if you want to make
    the package available to anyone on AppExchange and share your
    package publicly.

`--post_install_url POSTINSTALLURL`

: _Optional_

    The fully-qualified URL of the post-installation instructions.
    Instructions are shown as a link after installation and are
    available from the package detail view.

`--release_notes_url RELEASENOTESURL`

: _Optional_

    The fully-qualified URL of the package release notes. Release notes
    are shown as a link during the installation process and are
    available from the package detail view after installation.

`--namespace NAMESPACE`

: _Optional_

    The namespace of the package. Defaults to
    project\_\_package\_\_namespace

`--resolution_strategy RESOLUTIONSTRATEGY`

: _Optional_

    The name of a sequence of resolution_strategy (from
    project\_\_dependency_resolutions) to apply to dynamic dependencies.
    Defaults to \'production\'.

# **upload_user_profile_photo**

**Description:** Uploads a profile photo for a specified or default
User.

**Class:** cumulusci.tasks.salesforce.users.photos.UploadProfilePhoto

Uploads a profile photo for a specified or default User.

## Examples

Upload a profile photo for the default user.

```yaml
tasks:
    upload_profile_photo_default:
        group: Internal storytelling data
        class_path: cumulusci.tasks.salesforce.users.UploadProfilePhoto
        description: Uploads a profile photo for the default user.
        options:
            photo: storytelling/photos/default.png
```

Upload a profile photo for a user whose Alias equals `grace` or
`walker`, is active, and created today.

```yaml
tasks:
    upload_profile_photo_grace:
        group: Internal storytelling data
        class_path: cumulusci.tasks.salesforce.users.UploadProfilePhoto
        description: Uploads a profile photo for Grace.
        options:
            photo: storytelling/photos/grace.png
            where: (Alias = 'grace' OR Alias = 'walker') AND IsActive = true AND CreatedDate = TODAY
```

## Command Syntax

`$ cci task run upload_user_profile_photo`

## Options

`--photo PHOTO`

: _Required_

    Path to user\'s profile photo.

`--where WHERE`

: _Optional_

    WHERE clause used querying for which User to upload the profile
    photo for.

-   No need to prefix with `WHERE`
-   The SOQL query must return one and only one User record.
-   If no \"where\" is supplied, uploads the photo for the org\'s
    default User.

# **util_sleep**

**Description:** Sleeps for N seconds

**Class:** cumulusci.tasks.util.Sleep

## Command Syntax

`$ cci task run util_sleep`

## Options

`--seconds SECONDS`

: _Required_

    The number of seconds to sleep

    Default: 5

# **log**

**Description:** Log a line at the info level.

**Class:** cumulusci.tasks.util.LogLine

## Command Syntax

`$ cci task run log`

## Options

`--level LEVEL`

: _Required_

    The logger level to use

    Default: info

`--line LINE`

: _Required_

    A formatstring like line to log

`--format_vars FORMATVARS`

: _Optional_

    A Dict of format vars

# **generate_dataset_mapping**

**Description:** Create a mapping for extracting data from an org.

**Class:** cumulusci.tasks.bulkdata.GenerateMapping

Generate a mapping file for use with the [extract_dataset]{.title-ref}
and [load_dataset]{.title-ref} tasks. This task will examine the schema
in the specified org and attempt to infer a mapping suitable for
extracting data in packaged and custom objects as well as customized
standard objects.

Mappings must be serializable, and hence must resolve reference cycles -
situations where Object A refers to B, and B also refers to A. Mapping
generation will stop and request user input to resolve such cycles by
identifying the correct load order. If you would rather the mapping
generator break such a cycle randomly, set the
[break_cycles]{.title-ref} option to [auto]{.title-ref}.

Alternately, specify the [ignore]{.title-ref} option with the name of
one of the lookup fields to suppress it and break the cycle.
[ignore]{.title-ref} can be specified as a list in
[cumulusci.yml]{.title-ref} or as a comma-separated string at the
command line.

In most cases, the mapping generated will need minor tweaking by the
user. Note that the mapping omits features that are not currently well
supported by the [extract_dataset]{.title-ref} and
[load_dataset]{.title-ref} tasks, such as references to the
[User]{.title-ref} object.

## Command Syntax

`$ cci task run generate_dataset_mapping`

## Options

`--path PATH`

: _Required_

    Location to write the mapping file

    Default: datasets/mapping.yml

`--namespace_prefix NAMESPACEPREFIX`

: _Optional_

    The namespace prefix to use

    Default: \$project_config.project\_\_package\_\_namespace

`--ignore IGNORE`

: _Optional_

    Object API names, or fields in Object.Field format, to ignore

`--break_cycles BREAKCYCLES`

: _Optional_

    If the generator is unsure of the order to load, what to do? Set to
    [ask]{.title-ref} (the default) to allow the user to choose or
    [auto]{.title-ref} to pick randomly.

`--include INCLUDE`

: _Optional_

    Object names to include even if they might not otherwise be
    included.

`--strip_namespace STRIPNAMESPACE`

: _Optional_

    If True, CumulusCI removes the project\'s namespace where found in
    fields and objects to support automatic namespace injection. On by
    default.

# **extract_dataset**

**Description:** Extract a sample dataset using the bulk API.

**Class:** cumulusci.tasks.bulkdata.ExtractData

## Command Syntax

`$ cci task run extract_dataset`

## Options

`--mapping MAPPING`

: _Required_

    The path to a yaml file containing mappings of the database fields
    to Salesforce object fields

    Default: datasets/mapping.yml

`--database_url DATABASEURL`

: _Optional_

    A DATABASE_URL where the query output should be written

`--sql_path SQLPATH`

: _Optional_

    If set, an SQL script will be generated at the path provided This is
    useful for keeping data in the repository and allowing diffs.

    Default: datasets/sample.sql

`--inject_namespaces INJECTNAMESPACES`

: _Optional_

    If True, the package namespace prefix will be automatically added to
    (or removed from) objects and fields based on the name used in the
    org. Defaults to True.

`--drop_missing_schema DROPMISSINGSCHEMA`

: _Optional_

    Set to True to skip any missing objects or fields instead of
    stopping with an error.

# **load_dataset**

**Description:** Load a sample dataset using the bulk API.

**Class:** cumulusci.tasks.bulkdata.LoadData

## Command Syntax

`$ cci task run load_dataset`

## Options

`--database_url DATABASEURL`

: _Optional_

    The database url to a database containing the test data to load

`--mapping MAPPING`

: _Optional_

    The path to a yaml file containing mappings of the database fields
    to Salesforce object fields

    Default: datasets/mapping.yml

`--start_step STARTSTEP`

: _Optional_

    If specified, skip steps before this one in the mapping

`--sql_path SQLPATH`

: _Optional_

    If specified, a database will be created from an SQL script at the
    provided path

    Default: datasets/sample.sql

`--ignore_row_errors IGNOREROWERRORS`

: _Optional_

    If True, allow the load to continue even if individual rows fail to
    load.

`--reset_oids RESETOIDS`

: _Optional_

    If True (the default), and the \_sf_ids tables exist, reset them
    before continuing.

`--bulk_mode BULKMODE`

: _Optional_

    Set to Serial to force serial mode on all jobs. Parallel is the
    default.

`--inject_namespaces INJECTNAMESPACES`

: _Optional_

    If True, the package namespace prefix will be automatically added to
    (or removed from) objects and fields based on the name used in the
    org. Defaults to True.

`--drop_missing_schema DROPMISSINGSCHEMA`

: _Optional_

    Set to True to skip any missing objects or fields instead of
    stopping with an error.

`--set_recently_viewed SETRECENTLYVIEWED`

: _Optional_

    By default, the first 1000 records inserted via the Bulk API will be
    set as recently viewed. If fewer than 1000 records are inserted,
    existing objects of the same type being inserted will also be set as
    recently viewed.

# **load_custom_settings**

**Description:** Load Custom Settings specified in a YAML file to the
target org

**Class:** cumulusci.tasks.salesforce.LoadCustomSettings

## Command Syntax

`$ cci task run load_custom_settings`

## Options

`--settings_path SETTINGSPATH`

: _Required_

    The path to a YAML settings file

# **remove_metadata_xml_elements**

**Description:** Remove specified XML elements from one or more metadata
files

**Class:** cumulusci.tasks.metadata.modify.RemoveElementsXPath

## Command Syntax

`$ cci task run remove_metadata_xml_elements`

## Options

`--xpath XPATH`

: _Optional_

    An XPath specification of elements to remove. Supports the re:
    regexp function namespace. As in re:match(text(), \'.\*\_\_c\')Use
    ns: to refer to the Salesforce namespace for metadata elements.for
    example: ./ns:Layout/ns:relatedLists (one-level) or
    //ns:relatedLists (recursive)Many advanced examples are available
    here:
    <https://github.com/SalesforceFoundation/NPSP/blob/26b585409720e2004f5b7785a56e57498796619f/cumulusci.yml#L342>

`--path PATH`

: _Optional_

    A path to the files to change. Supports wildcards including \*\* for
    directory recursion. More info on the details:
    <https://www.poftut.com/python-glob-function-to-match-path-directory-file-names-with-examples/>
    <https://www.tutorialspoint.com/How-to-use-Glob-function-to-find-files-recursively-in-Python>

`--elements ELEMENTS`

: _Optional_

    A list of dictionaries containing path and xpath keys. Multiple
    dictionaries can be passed in the list to run multiple removal
    queries in the same task. This parameter is intended for usages
    invoked as part of a cumulusci.yml .

`--chdir CHDIR`

: _Optional_

    Change the current directory before running the replace

# **disable_tdtm_trigger_handlers**

**Description:** Disable specified TDTM trigger handlers

**Class:**
cumulusci.tasks.salesforce.trigger_handlers.SetTDTMHandlerStatus

## Command Syntax

`$ cci task run disable_tdtm_trigger_handlers`

## Options

`--handlers HANDLERS`

: _Optional_

    List of Trigger Handlers (by Class, Object, or \'Class:Object\') to
    affect (defaults to all handlers).

`--namespace NAMESPACE`

: _Optional_

    The namespace of the Trigger Handler object (\'eda\' or \'npsp\').
    The task will apply the namespace if needed.

`--active ACTIVE`

: _Optional_

    True or False to activate or deactivate trigger handlers.

`--restore_file RESTOREFILE`

: _Optional_

    Path to the state file to store or restore the current trigger
    handler state. Set to False to discard trigger state information. By
    default the state is cached in an org-specific directory for later
    restore.

`--restore RESTORE`

: _Optional_

    If True, restore the state of Trigger Handlers to that stored in the
    (specified or default) restore file.

# **restore_tdtm_trigger_handlers**

**Description:** Restore status of TDTM trigger handlers

**Class:**
cumulusci.tasks.salesforce.trigger_handlers.SetTDTMHandlerStatus

## Command Syntax

`$ cci task run restore_tdtm_trigger_handlers`

## Options

`--handlers HANDLERS`

: _Optional_

    List of Trigger Handlers (by Class, Object, or \'Class:Object\') to
    affect (defaults to all handlers).

`--namespace NAMESPACE`

: _Optional_

    The namespace of the Trigger Handler object (\'eda\' or \'npsp\').
    The task will apply the namespace if needed.

`--active ACTIVE`

: _Optional_

    True or False to activate or deactivate trigger handlers.

`--restore_file RESTOREFILE`

: _Optional_

    Path to the state file to store or restore the current trigger
    handler state. Set to False to discard trigger state information. By
    default the state is cached in an org-specific directory for later
    restore.

`--restore RESTORE`

: _Optional_

    If True, restore the state of Trigger Handlers to that stored in the
    (specified or default) restore file.

    Default: True
