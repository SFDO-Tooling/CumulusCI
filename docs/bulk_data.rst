=========
Bulk Data
=========

The cumulusci.tasks.bulkdata module contains three tasks for dealing with 
test and sample data.

QueryData
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
            Id: sf_id
            API Name: sqlite3 name
        lookups:
            ForeignKeyAPIName (e.g. AccountId):
                key_field (field on CURRENT table (specified in step.table) that contains the foreign key)
                table (table to join to)
                join_field (field on table just specified that contains the referenced key. usually id/pk)
                value_field (field on the joined table to use as value, usually sf_id)
        static:
            FieldAPIName: True
            AnotherFieldAPIName: MonthlyLiteral


Example
^^^^^^^

.. code-block:: yaml    

    Insert Organizations:
        sf_object: Account
        table: organizations
        fields:
            Id: sf_id
            Name: organization
        record_type: Organization


    Insert Household Contacts:
        sf_object: Contact
        table: contacts
        filters:
            - 'household_id is not null'
        fields:
            Id: sf_id
            Salutation: salutation
            FirstName: first_name
            LastName: last_name
            Email: email
            Phone: phone
            Title: job_title
        lookups:
            AccountId:
                key_field: household_id
                table: households
                join_field: household_id
                value_field: sf_id
            Primary_Affiliation__c: 
                key_field: organization_id
                table: organizations
                join_field: organization_id
                value_field: sf_id

