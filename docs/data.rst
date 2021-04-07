========================
Automate Data Operations
========================

CumulusCI offers a suite of tasks to help you to manage data as part of your project
automation. Within your repository, you can define one or several *datasets*,
collections of data you use for specific purposes. CumulusCI tasks support
extracting defined datasets from scratch orgs or persistent orgs,
storing those snapshots within the repository, and automating the load of datasets 
into orgs. Data operations are executed via the Bulk and REST APIs.

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
        fields:
            - Name
            - Description
            - RecordTypeId
        lookups:
            ParentId:
                table: Account
                after: Accounts
    Contacts:
        sf_object: Contact
        fields:
            - FirstName
            - LastName
            - Email
        lookups:
            AccountId:
                table: Account

This example defines two steps: ``Accounts`` and ``Contacts``. (The names of steps
are arbitrary). Each step governs the  extraction or load of records in the sObject denoted 
in its ``sf_object`` property.

Relationships are defined in the ``lookups`` section. Each key within ``lookups`` is the API
name of the relationship field. Beneath, the ``table`` key defines the stored table to which
this relationship refers.

CumulusCI loads steps in order. However, sObjects earlier in the sequence of steps may include
lookups to sObjects loaded later, or to themselves. For these cases, the ``after`` key may be 
included in a lookup definition, with a value set to the name of the step after which the 
referenced record is expected to be available. CumulusCI will defer populating the lookup field 
until the referenced step has been completed. In the example above, an ``after`` definition
is used to support the ``ParentId`` self-lookup on ``Account``.

API Selection
-------------

By default, CumulusCI will determine the data volume of the specified object and select an API
for you: for under 2,000 records, the REST Collections API is used; for more, the Bulk API is
used. The Bulk API is also used for delete operations where the hard delete operation is
requested, as this is available only in the Bulk API. Smart API selection helps increase
speed for low- and moderate-volume data loads.

To prefer a specific API, set the ``api`` key within any mapping step; allowed values are
``"rest"``, ``"bulk"``, and ``"smart"``, the default.

CumulusCI defaults to using the Bulk API in Parallel mode. If required to avoid row locks,
specify the key ``bulk_mode: Serial`` in each step requiring the use of serial mode.

For REST API and smart-API modes, you can specify a batch size using the ``batch_size`` key.
Legal values are between 1 and 200. The batch size cannot be set for the Bulk API.

Database Mapping
----------------

CumulusCI's definition format includes considerable flexibility for use cases where datasets
are stored in SQL databases whose structure is not identical to the Salesforce database.
Salesforce objects may be assigned to arbitrary database tables, and Salesforce field names
mapped to arbitrary columns.

For new mappings, it's recommended to allow CumulusCI to use sensible defaults by specifying
only the Salesforce entities. Legacy datasets are likely to include explicit database mappings,
which would look like this for the same data model as above: 

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

Note that in this version, fields are specified as a colon-separated mapping, not a list. Each pair 
in the field map is structured as ``Salesforce API Name: Database Column Name``. Additionally, each
object has a ``table`` key to specify the underlying database table.

New mappings that do not connect to an external SQL database (that is, mappings which simply extract
and load data between Salesforce orgs) should not need to use this feature, and new mappings that
are generated by CumulusCI use the simpler version shown above. Existing mappings may be converted
to this streamlined style in most cases by loading the existing dataset, modifying the mapping file,
and then extracting a fresh copy of the data. Note however that datasets which make use of older and
deprecated CumulusCI features, such as the ``record_type`` key, may need to continue using explicit
database mapping.

Record Types
------------

CumulusCI supports automatic mapping of Record Types between orgs, keyed upon the Developer Name.
To take advantage of this support, simply include the ``RecordTypeId`` field in any step.
CumulusCI will transparently extract Record Type information during dataset capture and
map Record Types by Developer Name into target orgs during loads.

Older dataset definitions may also use a ``record_type`` key::

    Accounts:
        sf_object: Account
        fields:
            - Name
        record_type: Organization

This feature limits extraction to records possessing that specific Record Type, and assigns
the same Record Type upon load.

It's recommended that new datasets use Record Type mapping by including the ``RecordTypeId`` 
field. Using ``record_type`` will result in CumulusCI issuing a warning.

Relative Dates
--------------

CumulusCI supports maintaining *relative dates*, helping to keep the dataset relevant by
ensuring that date and date-time fields are updated when loaded.

Relative dates are enabled by defining an *anchor date*, which is specified in each mapping
step with the ``anchor_date`` key, whose value is a date in the format ``2020-07-01``.

When you specify a relative date, CumulusCI modifies all date and date-time fields on the
object such that when loaded, they have the same relationship to today as they did to the
anchor date. Hence, given a stored date of 2020-07-10 and an anchor date of 2020-07-01,
if you perform a load on 2020-09-10, the date field will be rendered as 2020-09-19 -
nine days ahead of today's date, as it was nine days ahead of the anchor date.

Relative dates are also adjusted upon extract so that they remain stable. Extracting the same
data mentioned above would result in CumulusCI adjusting the date back to 2020-07-10 for
storage, keeping it relative to the anchor date.

Relative dating is applied to all date and date-time fields on any mapping step that
contains the ``anchor_date`` clause. If orgs are `configured <https://help.salesforce.com/articleView?id=000334139&language=en_US&type=1&mode=1>`_ to permit setting audit 
fields upon record creation and the appropriate user permission is enabled,
CumulusCI can apply relative dating to audit fields, such as ``CreatedDate``.
For more about how to automate that setup, review the ``create_bulk_data_permission_set``
task below.

For example, this mapping step:

.. code-block:: yaml

    Contacts:
        sf_object: Contact
        fields:
            - FirstName
            - LastName
            - Birthdate
        anchor_date: 1990-07-01

would adjust the ``Birthdate`` field on both load and extract around the anchor date of
July 1, 1990. Note that date and datetime fields not mapped, as well as fields on other
steps, are unaffected.

Person Accounts
---------------

CumulusCI supports extracting and loading person account data.  In your dataset definition, map person account fields like ``LastName``, ``PersonBirthdate``, or ``CustomContactField__pc`` to **Account** steps (i.e. where ``sf_object`` equals **Account**).

.. code-block:: yaml

    Account:
      sf_object: Account
      table: Account
      fields:
        # Business Account Fields
        - Name
        - AccountNumber
        - BillingStreet
        - BillingCity

        # Person Account Fields
        - FirstName
        - LastName
        - PersonEmail
        - CustomContactField__pc

        # Optional (though recommended) Record Type
        - RecordTypeId

Record Types
++++++++++++

It's recommended, though not required, to extract Account Record Types to support datasets with person accounts so there is consistency in the Account record types loaded.   If Account ``RecordTypeId`` is not extracted, the default business account Record Type and default person account Record Type will be applied to business and person account records respectively.

Extract
+++++++

During dataset extraction, if the org has person accounts enabled, the ``IsPersonAccount`` field is extracted for **Account** and **Contact** records so CumulusCI can properly load these records later.  Additionally, ``Account.Name`` is not createable for person account **Account** records, so ``Account.Name`` is not extracted for person account **Account** records.

Load
++++

Before loading, CumulusCI checks if the dataset contains any person account records (i.e. any **Account** or **Contact** records with ``IsPersonAccount`` as ``true``).  If the dataset does contain any person account records, CumulusCI validates the org has person accounts enabled.

You can enable person accounts for scratch orgs by including the `PersonAccounts <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_scratch_orgs_def_file_config_values.htm#so_personaccounts/>`_ feature in your scratch org definition.

Advanced Features
-------------------

CumulusCI supports two additional keys within each step 

The ``filters`` key encompasses filters applied to the SQL data store when loading data.
Use of ``filters`` can support use cases where only a subset of stored data should be loaded. ::

    filters:
        - 'SQL string'

Note that ``filters`` uses SQL syntax, not SOQL. Filters do not perform filtration or data subsetting
upon extraction; they only impact loading. This is an advanced feature.

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
script format. However, it comes at some performance penalty when extracting data. It's
recommended that most mappings do not map the Id field and allow CumulusCI to utilize
the automatic primary key.

Handling Namespaces
+++++++++++++++++++

All CumulusCI bulk data tasks support automatic namespace injection or removal. In other words,
the same mapping file will work for namespaced and unnamespaced orgs, as well as orgs with
the package installed managed or unmanaged. If a mapping element has no namespace prefix and
adding the project's namespace prefix is required to match a name in the org, CumulusCI will
add one. Similarly, if removing a namespace is necessary, CumulusCI will do so.

In the extremely rare circumstance that an org contains the same mapped schema element in both
namespaced and non-namespaced form, CumulusCI does not perform namespace injection or removal
for that element.

Namespace injection can be deactivated by setting the ``inject_namespaces`` option to ``False``.

The ``generate_dataset_mapping`` generates mapping files with no namespace and this is the
most common pattern in CumulusCI projects.

Namespace Handing with Multiple Mapping Files
+++++++++++++++++++++++++++++++++++++++++++++

It's also possible, and common in older managed package products, to use multiple mapping files
to achieve loading the same data set in both namespaced and non-namespaced contexts. This is no
longer recommended practice.

A mapping file that is converted to use explicit namespacing might look like this:

Original version: ::

    Destinations:
        sf_object: Destination__c
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

Note that mappings which use the flat list style of field specification must use mapping style to convert
between namespaced and non-namespaced deployment.

It's recommended that all new mappings use flat list field specifications and allow CumulusCI to manage
namespace injection. This capability typically results in significant simplication in automation.

Optional Data Elements
++++++++++++++++++++++

Some projects need to build datasets that include optional data elements - fields and objects that are loaded
into some of the project's orgs, but not others. This can cover both optional managed packages and features
that are included in some, but not all, orgs. For example, a managed package A that does not require another
managed package B but is designed to work with it may wish to include data for managed package B in its
data sets, but load that data if and only if B is installed. Likewise, a package might wish to include data
supporting a particular org feature, but not load that data in an org where the feature is turned off (and its
associated fields and objects are for that reason unavailable).

To support this use case, the ``load_dataset`` and ``extract_dataset`` tasks offer a ``drop_missing_schema``
option. When enabled, this option results in CumulusCI ignoring any mapped fields, sObjects, or lookups that
correspond to schema that is not present in the org.

Projects that require this type of conditional behavior can build their datasets in an org that contains managed
package B, capture it, and then load it safely in orgs that both do and do not contain B. However, it's important
to always capture from an org with B present, or B data will not be preserved in the dataset.


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

``create_bulk_data_permission_set``
-----------------------------------

Create and assign a Permission Set that enables key features used in Bulk Data
tasks (Hard Delete and Set Audit Fields) for the current user. The Permission
Set will be called ``CumulusCI Bulk Data``.

Note that prior to running this task you must ensure that your org is configured
to allow the use of Set Audit Fields. You can do so by manually updating
the required setting in the User Interface section of Saleforce Setup, or by
updating your scratch org configuration to include ::

    "securitySettings": {
      "enableAuditFieldsInactiveOwner": true
    }

For more information about the Set Audit Fields feature, review `this Knowledge
article <https://help.salesforce.com/articleView?id=000213290&type=1>`_.

After this task runs, you'll be able to run the ``delete_data`` task with the
``hardDelete`` option, and you'll be able to map audit fields like ``CreatedDate``.


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
needed for the dataset. 

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

``delete_data``
---------------

You can also delete records using CumulusCI. You can either delete every record of a
particular object, certain records based on a  ``where`` clause or every record of
multiple objects. Because ``where`` clauses seldom make logical sense when applied
to multiple objects, you cannot use a ``where`` clause when specifying multiple
objects.

Details are available with ``cci org info delete_data``
and `in the task reference <./tasks.html#delete-data>`_.

Examples
++++++++

.. code-block::

    cci task run delete_data -o objects Opportunity,Contact,Account --org qa

    cci task run delete_data -o objects Opportunity -o where "StageName = 'Active' "

    cci task run delete_data -o objects Account -o ignore_row_errors True

    cci task run delete_data -o objects Account -o hardDelete True



Generate Fake Data
==================
It is possible to use CumulusCI to generate arbitrary amounts of
synthetic data using the ``generate_and_load_from_yaml`` 
`task <https://cumulusci.readthedocs.io/en/latest/tasks.html#generate-and-load-from-yaml>`_. That
task is built on the `Snowfakery language
<https://snowfakery.readthedocs.io/en/docs/>`_. CumulusCI ships
with Snowfakery embedded, so you do not need to install it.

To start, you will need a Snowfakery recipe. You can learn about
writing them in the `Snowfakery docs
<https://snowfakery.readthedocs.io/en/docs/>`_.

Once you have it, you can fill an org with data like this:

``$ cci task run generate_and_load_from_yaml -o generator_yaml
datasets/some_snowfakery_recipe.yml``

If you would like to execute the recipe multiple times to generate
more data, you do so like this:

``$ cci task run generate_and_load_from_yaml -o generator_yaml
datasets/some_snowfakery_recipe.yml -o num_records 1000 -o num_records_tablename
Account â€”-org dev``

``generator_yaml`` is a reference to your Snowfakery recipe.

``num_records_tablename`` says what record type will control how
many records are created.

``num_records`` says how many of that record type ("Account" in
this case) to make.

Generated Record Counts
-----------------------

The counting works like this:

  * Snowfakery always executes a *complete* recipe. It never stops halfway through.
  
  * At the end of executing a recipe, it checks whether it has
    created enough of the object type defined by ``num_records_tablename``
  
  * If so, it finishes. If not, it runs the recipe again.

So if your recipe creates 10 Accounts, 5 Contacts and 15 Opportunities,
then when you run the command above it will run the recipe
100 times (100*10=1000) which will generate 1000 Accounts, 500 Contacts
and 1500 Opportunities.

Controlling the Loading Process
-------------------------------

CumulusCI's data loader has many knobs and switches that you might want to
adjust during your load. It supports a ".load.yml" file format which allows you to
manipulate these load settings. The simplest way to use this file format is to make
a file in the same directory as your recipe with a filename that is derived from
the recipe's by replacing everything after the first "." with ".load.yml". For example,
if your recipe is called "babka.recipe.yml" then your load file would be
"babka.load.yml".

Inside of that file you put a list of declarations in the following format:

.. code-block::

    - sf_object: Account
      api: bulk
      bulk_mode: parallel


Which would specifically load accounts using the bulk API's parallel mode.

The specific keys that you can associate with an object are:

* api: "smart", "rest" or "bulk"
* batch_size: a number
* bulk_mode: "serial" or "parallel"
* load_after: the name of another sobject to wait for before loading

"api", "batch_size" and "bulk_mode" have the same meanings that they
do in mapping.yml as described in `API Selection`_.

For example, one could force Accounts and Opportunities to load after
Contacts:

.. code-block::

    - sf_object: Account
      load_after: Contact

    - sf_object: Opportunity
      load_after: Contact

If you wish to share a loading file between multiple recipes, you can
refer to it with the ``--loading_rules`` option. That will override the
default filename (``<recipename>.load.yml``). If you want both, or
any combination of multiple files, you can do that by listing them with
commas between the filenames.

Batch Sizes
-----------

You can also control batch sizes with the ``-o batch_size BATCHSIZE``
parameter. This is not the Salesforce bulk API batch size. No matter
what batch size you select, CumulusCI will properly split your data
into batches for the bulk API.

You need to understand the loading process to understand why you
might want to set the ``batch_size``.

If you haven't set the ``batch_size`` then Snowfakery generates all
of the records for your load job at once.

So the first reason why you might want to set the batch_size is
because you don't have enough local disk space for the number of
records you are generating (across all tables).

This isn't usually a problem though.

The more common problem arises from the fact that Salesforce bulk
uploads are always done in batches of records a particular SObject.
So in the case above, it would upload 1000 Accounts, then 500
Contacts, then 1500 Opportunities. (remember that our scenario
involves a recipe that generates 10 Accounts, 5 Contacts and 15
Opportunities).

Imagine if the numbers were more like 1M, 500K and 1.5M. And further,
imagine if your network crashed after 1M Accounts and 499K Contacts 
were uploaded. You would not have a single "complete set" of 10/5/15.
Instead you would have 1M "partial sets".

If, by contrast, you had set your batch size to 100_000, your network
might die more around the 250,000 Account mark, but you would have
200,000/20 [#]_ =10K *complete sets*  plus some "extra" Accounts 
which you might ignore or delete. You can restart your load with a 
smaller goal (800K Accounts) and finish the job.

.. [#] remember that our sets have 20 Accounts each

Another reason you might choose smaller batch sizes is to minimize
the risk of row locking errors when you have triggers enabled.
Turning off triggers is generally preferable, and CumulusCI `has a
task
<https://cumulusci.readthedocs.io/en/latest/tasks.html#disable-tdtm-trigger-handlers>`_
for doing for TDTM trigger handlers, but sometimes you cannot avoid
them. Using smaller batch sizes may be preferable to switching to
serial mode. If every SObject in a batch uploads less than 10,000
rows then you are defacto in serial mode (because only one "bulk mode
batch" at a time is being processed).

In general, bigger batch sizes achieve higher throughput. No batching
at all is the fastest.

Smaller batch sizes reduce the risk of something going wrong. You
may need to experiment to find the best batch size for your use
case.

