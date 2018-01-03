=========
Bulk Data
=========

Mapping File
===========

Step Name: (must be unique)
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
            key_field
            table
            join_field
            value_field
    static:
        FieldAPIName: True
        AnotherFieldAPIName: MonthlyLiteral



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
