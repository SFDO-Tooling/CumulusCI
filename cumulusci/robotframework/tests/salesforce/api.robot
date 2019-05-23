*** Settings ***

Resource        cumulusci/robotframework/Salesforce.robot
Suite Teardown  Delete Session Records
Force Tags      api

*** Keywords ***

Create Contact
    ${first_name} =  Generate Random String
    ${last_name} =  Generate Random String
    ${contact_id} =  Salesforce Insert  Contact  FirstName=${first_name}  LastName=${last_name}
    &{contact} =  Salesforce Get  Contact  ${contact_id}
    [return]  &{contact}

*** Test Cases ***

Salesforce Delete
    Log Variables
    &{contact} =  Create Contact
    Salesforce Delete  Contact  &{contact}[Id]
    &{result} =  SOQL Query  Select Id from Contact WHERE Id = '&{contact}[Id]'
    Should Be Equal  &{result}[totalSize]  ${0}

Salesforce Insert
    ${first_name} =  Generate Random String
    ${last_name} =  Generate Random String
    ${contact_id} =  Salesforce Insert  Contact
    ...  FirstName=${first_name}
    ...  LastName=${last_name}
    &{contact} =  Salesforce Get  Contact  ${contact_id}
    Should Be Equal  &{contact}[FirstName]  ${first_name}
    Should Be Equal  &{contact}[LastName]  ${last_name}
    
Salesforce Update
    &{contact} =  Create Contact
    ${new_last_name} =  Generate Random String
    Salesforce Update  Contact  &{contact}[Id]  LastName=${new_last_name}
    &{contact} =  Salesforce Get  Contact  &{contact}[Id]
    Should Be Equal  &{contact}[LastName]  ${new_last_name}

Salesforce Query
    &{new_contact} =  Create Contact
    @{records} =  Salesforce Query  Contact
    ...              select=Id,FirstName,LastName
    ...              Id=&{new_contact}[Id]
    &{contact} =  Get From List  ${records}  0
    Should Be Equal  &{contact}[Id]  &{new_contact}[Id]
    Should Be Equal  &{contact}[FirstName]  &{new_contact}[FirstName]
    Should Be Equal  &{contact}[LastName]  &{new_contact}[LastName]

SOQL Query
    &{new_contact} =  Create Contact
    &{result} =  Soql Query  Select Id, FirstName, LastName from Contact WHERE Id = '&{new_contact}[Id]'
    @{records} =  Get From Dictionary  ${result}  records
    Log Variables
    &{contact} =  Get From List  ${records}  0
    Should Be Equal  &{result}[totalSize]  ${1}
    Should Be Equal  &{contact}[FirstName]  &{new_contact}[FirstName]
    Should Be Equal  &{contact}[LastName]  &{new_contact}[LastName]

Salesforce Delete Session Records
    [Documentation]
    ...  Verify that 'Delete Session Records' deletes all session records
    ...  This verifies that we fixed a bug which resulted in some records
    ...  not being deleted.

    # We'll use this to uniquely identify all records created in this test
    ${random string}=  Generate Random String

    # First, make sure we have no records that match
    @{query}=  Salesforce Query  Contact  LastName=${random string}
    length should be  ${query}  0         Expected the query to return no records, but it returned ${query}

    # Next, create some records
    FOR  ${i}  IN RANGE  5
        ${contact_id} =  Salesforce Insert  Contact
        ...  FirstName=User-${i}
        ...  LastName=${random string}
    END
    @{query}=  Salesforce Query    Contact  LastName=${random string}
    length should be  ${query}  5  Expected the query to return five records, but it returned ${query}

    # Now, call 'Delete Session Records' and verify all five were deleted
    Delete Session Records
    @{query}=  Salesforce Query  Contact
    ...  LastName=${random string}
    length should be  ${query}  0  Expected the query to return 0 records, but it returned ${query}
