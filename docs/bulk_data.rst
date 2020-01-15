==========================
Automating Data Operations
==========================

CumulusCI offers a suite of tasks to help you to manage data as part of your project
automation. Within your repository, you can define one or several *datasets*,
collections of data you use for specific purposes. CumulusCI tasks support
extracting defined datasets from scratch orgs or persistent orgs,
storing those snapshots within the repository, and automating the load of datasets 
into orgs. Data operations are executed via the Bulk API.

A dataset consists of 

* a *definition file*, written in YAML, which specifies the sObjects
  and fields contained in the dataset and the order in which they are 
  loaded or extracted from an org.
* a *storage location*, which may take the form of a SQL database 
  (typically, a SQLite file stored within the repository, although 
  external databases are supported) or a SQL script file.

Datasets are stored in the ``datasets/`` folder within a repository by default.
Projects created with a recent version of CumulusCI ship with this directory
in place.

The Lifecycle of a Dataset
==========================

A dataset starts with a definition: which objects, and which fields, are to be captured,
persisted, and loaded into orgs? (The details of definition file format are covered below).

With a definition available, the dataset may be captured from an org into the repository.
A captured dataset may be stored under version control and incorporated into project 
automation, loaded as part of flows during org builds or at need. As the project's needs
evolve, datasets may be re-captured from orgs and versioned alongside the project metadata.

Projects may define one or many datasets. Datasets can contain an arbitrary amount of data.

Defining Datasets
=================

A dataset is defined in YAML as a series of steps. Each step registers a specific sObject
as part of the dataset, and defines the relevant fields on that sObject as well as its
relationships to other sObjects that are included in the data set.

    Note: this section discusses how to define a dataset and the format of the definition
    file. In many cases, it's easier to use the ``generate_dataset_mapping`` task than to
    create this definition by hand. See below for more details.

A simple dataset definition looks like this:

.. code-block:: yaml

    Accounts:
        sf_object: Account
        table: Account
        fields:
            Name: Name
            Description: Description
            RecordTypeId: RecordTypeId
        lookups:
            ParentId:
                table: Account
                after: Accounts
    Contacts:
        sf_object: Contact
        table: Contact
        fields:
            FirstName: FirstName
            LastName: LastName
            Email: Email
        lookups:
            AccountId:
                table: Account

This example defines two steps: ``Accounts`` and ``Contacts``. (The names of steps
are arbitrary). Each step governs the 
extraction or load of records in the sObject denoted in its ``sf_object`` property, which is
stored in the ``table`` table in the local database. In most cases, ``sf_object`` and ``table``
may be identical.

Those fields which are named in ``fields`` are included. Each field entry has the form 
``API Name: Stored Name``; that is, the first component is the Salesforce API name of the
field, and the second is the name under which that data is stored in the extracted version of
the dataset. In most cases, these values can be the same; users need to use a distinct stored
name only if the data is stored in a SQL database under a column other than its Salesforce API
name.

    CumulusCI's definition format includes considerable flexibility for use cases where datasets
    are stored in SQL databases whose structure is not identical to the Salesforce database.
    It's recommended that most new datasets set ``table`` equal to ``sf_object`` for each
    step and have API name and stored name the same for each field. Definitions generated
    by CumulusCI (see below) match these expectations.

Relationships are defined in the ``lookups`` section. Each key within ``lookups`` is the API
name of the relationship field. Beneath, the ``table`` key defines the stored table to which
this relationship refers.

CumulusCI loads steps in order. However, sObjects earlier in the sequence of steps may include
lookups to sObjects loaded later, or to themselves. For these cases, the ``after`` key may be 
included in a lookup definition, with a value set to the name of the step after which the 
referenced record is expected to be available. CumulusCI will defer populating the lookup field 
until the referenced step has been completed. In the example above, an ``after`` definition
is used to support the ``ParentId`` self-lookup on ``Account``.

CumulusCI defaults to using the Bulk API in Parallel mode. If required to avoid row locks,
specify the key ``bulk_mode: Serial`` in each step requiring the use of serial mode.

Record Types
------------

CumulusCI supports automatic mapping of Record Types between orgs, keyed upon the Developer Name.
To take advantage of this support, simply include the ``RecordTypeId`` field in any step.
CumulusCI will transparently extract Record Type information during dataset capture and
map Record Types by Developer Name into target orgs during loads.

Older dataset definitions may also use a ``record_type`` key::

    Accounts:
        sf_object: Account
        table: Account
        fields:
            Name: Name
        record_type: Organization

This feature limits extraction to records possessing that specific Record Type, and assigns
the same Record Type upon load.

It's recommended that new datasets use Record Type mapping by including the ``RecordTypeId`` 
field.

Advanced Features
-------------------

CumulusCI supports two additional keys within each step 

The ``filters`` key encompasses filters applied to the SQL data store when loading data.
Use of ``filters`` can support use cases where only a subset of stored data should be loaded. ::

    filters:
        - 'SQL string'

Note that ``filters`` uses SQL syntax, not SOQL. This is an advanced feature.

The ``static`` key allows individual fields to be populated with a fixed, static value. ::

        static:
            CustomCheckbox__c: True
            CustomDateField__c: 2019-01-01

Primary Keys
++++++++++++

CumulusCI offers two modes of managing Salesforce Ids and primary keys within the stored
database.

If the ``fields`` list for an sObject contains a mapping::

    Id: sf_id

CumulusCI will extract the Salesforce Id for each record and use that Id as the primary
key in the stored database.

If no such mapping is provided, CumulusCI will remove the Salesforce Id from extracted
data and replace it with an autoincrementing integer primary key.

Use of integer primary keys may help yield more readable text diffs when storing data in SQL
script format. However, it comes at some performance penalty when extracting data.

Handling Namespaces
+++++++++++++++++++

In many cases, the same dataset can be cleanly deployed to both namespaced (or managed)
and non-namespaced orgs. Data will be stored in the form corresponding to the org from
which it was captured - that is, data captured from a namespaced scratch org, or a managed
installation, will be stored with a namespace, and data captured from an unmanaged and 
non-namespaced scratch org without.

An additional definition file can be customized to permit loading the same data into the
opposite type of org. This example shows two versions of the same step, adapting an originally
non-namespaced definition to deploy non-namespaced data into a namespaced org with the 
namespace prefix ``MyNS``. 

Original version: ::

    Destinations:
        sf_object: Destination__c
        table: Destination__c
        fields:
            Name: Name
            Target__c: Target__c
        lookups:
            Supplier__c:
                table: Supplier__c

Namespaced version: ::

    Destinations:
        sf_object: MyNS__Destination__c
        table: Destination__c
        fields:
            MyNS__Name: Name
            MyNS__Target__c: Target__c
        lookups:
            MyNS__Supplier__c:
                key_field: Supplier__c
                table: Supplier__c

Note that each of the definition elements that refer to *local* storage remains un-namespaced,
while those elements referring to the Salesforce schema acquire the namespace prefix.

For each lookup, an additional ``key_field`` declaration is required, whose value is the 
original storage location in local storage for that field's data. In most cases, this is
simply the version of the field name in the original definition file.

Adapting an originally-namespaced definition to load into a non-namespaced org follows the same
pattern, but in reverse.

Custom Settings
===============

Datasets don't support Custom Settings. However, a separate task is supplied to deploy Custom 
Settings (both list and hierarchy) into an org: ``load_custom_settings``. The data for this
task is defined in a YAML text file

Each top-level YAML key should be the API name of a Custom Setting.
List Custom Settings should contain a nested map of names to values.
Hierarchy Custom settings should contain a list, each of which contains
a `data` key and a `location` key. The `location` key may contain either
`profile: <profile name>`, `user: name: <username>`, `user: email: <email>`,
or `org`. 

Example: ::

    List__c:
        Test:
            MyField__c: 1
        Test 2:
            MyField__c: 2
    Hierarchy__c:
        -
            location: org
            data:
                MyField__c: 1
        -
            location:
                user:
                    name: test@example.com
            data:
                MyField__c: 2"""

CumulusCI will automatically resolve the ``location`` specified for Hierarchy Custom Settings
to a ``SetupOwnerId``. Any Custom Settings existing in the target org with the specified
name (List) or setup owner (Hierarchy) will be updated with the given data.

Dataset Tasks
=============

``extract_dataset``
-------------------

Extract the data for a dataset from an org and persist it to disk.

Options
+++++++

* ``mapping``: the path to the YAML definition file for this dataset.
* ``sql_path``: the path to a SQL script storage location for this dataset.
* ``database_url``: the URL for the database storage location for this dataset.

``mapping`` and either ``sql_path`` or ``database_url`` must be supplied.

Example: ::

    cci task run extract_dataset -o mapping datasets/qa/mapping.yml -o sql_path datasets/qa/data.sql --org qa

``load_dataset``
----------------

Load the data for a dataset into an org. If the storage is a database, persist new
Salesforce Ids to storage.

Options
+++++++

* ``mapping``: the path to the YAML definition file for this dataset.
* ``sql_path``: the path to a SQL script storage location for this dataset.
* ``database_url``: the URL for the database storage location for this dataset.
* ``start_step``: the name of the step to start the load with (skipping all prior steps).
* ``ignore_row_errors``: If True, allow the load to continue even if individual rows 
  fail to load. By default, the load stops if any errors occur.

``mapping`` and either ``sql_path`` or ``database_url`` must be supplied.

Example: ::

    cci task run load_dataset -o mapping datasets/qa/mapping.yml -o sql_path datasets/qa/data.sql --org qa


``generate_dataset_mapping``
----------------------------

Inspect an org and generate a dataset definition for the schema found there.

This task is intended to streamline the process of creating a dataset definition.
To use it, first build an org (scratch or persistent) containing all of the schema
needed for the dataset. Carefully consider whether the org is namespaced, and 
whether the project is installed managed or unmanaged. 

Then, execute ``generate_dataset_mapping``. The task inspects the target org and 
creates a dataset definition encompassing the project's schema, attempting to be
minimal in its inclusion outside that schema. Specifically, the definition will
include:

* Any custom object without a namespace
* Any custom object with the project's namespace
* Any object with a custom field matching the same namespace criteria
* Any object that's the target of a master-detail relationship, or 
  a custom lookup relationship, from another included object.

On those sObjects, the definition will include

* Any custom field (including those defined by other packages)
* Any required field
* Any relationship field targeting another included object
* The ``Id``, ``FirstName``, ``LastName``, and ``Name`` fields, if present

Certain fields will always be omitted, including

* Lookups to the User object
* Binary-blob (base64) fields
* Compound fields
* Non-createable fields

The resulting definition file is intended to be a viable starting point for a project's
dataset. However, some additional editing is typically required to ensure the definition
fully suits the project's use case. In particular, any fields required on standard objects
that aren't automatically included must be added manually.

Reference Cycles
++++++++++++++++

Dataset definition files must execute in a sequence, one sObject after another. However,
Salesforce schemas often include *reference cycles*: situations in which Object A refers
to Object B, which also refers to Object A, or in which Object A refers to itself.

CumulusCI will detect these reference cycles during mapping generation and ask the user
for assistance resolving them into a linear sequence of load and extract operations. In
most cases, selecting the schema's most core object (often a standard object like Account)
will successfully resolve reference cycles. CumulusCI will automatically tag affected 
relationship fields with ``after`` directives to ensure they're populated after their 
target records become available.

Options
+++++++

* ``path``: Location to write the mapping file. Default: datasets/mapping.yml
* ``ignore``: Object API names, or fields in Object.Field format, to ignore
* ``namespace_prefix``: The namespace prefix to treat as belonging to the project, if any

Example: ::

    cci task run generate_dataset_mapping --org qa -o namespace_prefix my_ns

``load_custom_settings``
--------------------------

Load custom settings stored in YAML into an org.

Options
+++++++

* ``settings_path``: Location of the YAML settings file.
