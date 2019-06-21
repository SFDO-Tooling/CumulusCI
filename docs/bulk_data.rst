=========
Bulk Data
=========

The cumulusci.tasks.bulkdata module contains three tasks for dealing with 
test and sample data.

ExtractData
^^^^^^^^^
Runs the mapping YAML in order, from top to bottom, selecting data from the specified
sf_object and inserting it into the local table.

LoadData
^^^^^^^^
Runs the mapping YAML in order, selecting data from the local table and inserting into the
specified sf_object 


Mapping File
============

.. code-block:: yaml

    Step Name: (must be unique)
        api: [(bulk)|sobject] (not yet implemented, specify which API to use to load data)
        sf_object: API Name for sfdc object
        table: full table name in sqlite3
        filters: used to filter the sqlite3 table when loading data
            - 'sql string' 
        record_type: API Name (for insert/query)
        fields:
            API Name: sqlite3 name
        lookups:
            ForeignKeyAPIName (e.g. AccountId):
                key_field (OPTIONAL, field on CURRENT table (specified in step.table) that contains the foreign key)
                table (table to join to)
        static:
            FieldAPIName: True
            AnotherFieldAPIName: MonthlyLiteral

Salesforce OID as Primary key
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, the ExtractData and LoadData task will use an autoincrementing integer field named `id` as the primary key.  In order to make the references using an integer, the ExtractData task has to do a multitable update that could impact performance when querying large data sets.

If the performance of ExtractData on large data sets is more important than the advantages of abstracting references to use integer ID's, you can configure a mapping to use the queried Salesforce OID's as the reference for lookup fields by adding the following to the fields section:
.. code-block:: yaml    

        fields:
            Id: sf_id

Example
^^^^^^^

.. code-block:: yaml    

    Insert Organizations:
        sf_object: Account
        table: organizations
        fields:
            Name: organization
        record_type: Organization


    Insert Household Contacts:
        sf_object: Contact
        table: contacts
        filters:
            - 'household_id is not null'
        fields:
            Salutation: salutation
            FirstName: first_name
            LastName: last_name
            Email: email
            Phone: phone
            Title: job_title
        lookups:
            AccountId:
                table: households
            Primary_Affiliation__c: 
                table: organizations
