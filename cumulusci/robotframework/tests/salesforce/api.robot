*** Settings ***

Resource       cumulusci/robotframework/Salesforce.robot
Suite Teardown  Delete Session Records

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
