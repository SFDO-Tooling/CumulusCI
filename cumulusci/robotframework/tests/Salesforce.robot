*** Settings ***

Resource       cumulusci/robotframework/Salesforce.robot

*** Keywords ***

Create Contact
    ${first_name} =  Generate Random String
    ${last_name} =  Generate Random String
    ${contact_id} =  Salesforce Insert  Contact  FirstName=${first_name}  LastName=${last_name}
    &{contact} =  Salesforce Get  Contact  ${contact_id}
    [return]  &{contact}

*** Test Cases ***

Click Modal Button
    Open Test Browser
    Go To Object Home  Contact
    Click Object Button  New
    Click Modal Button  Save
    ${locator} =  Get Locator  modal.has_error
    Page Should Contain Element  ${locator}
    [Teardown]  Close Browser

Click Object Button
    Open Test Browser
    Go To Object Home  Contact
    Click Object Button  New
    Page Should Contain  New Contact
    [Teardown]  Close Browser

Click Related List Button
    Open Test Browser
    &{contact} =  Create Contact
    Go To Record Home  &{contact}[Id]
    Click Related List Button  Opportunities  New
    Wait Until Modal Is Open
    Page Should Contain  New Opportunity
    [Teardown]  Close Browser

Get Current Record Id
    Open Test Browser
    &{contact} =  Create Contact
    Go To Record Home  &{contact}[Id]
    ${contact_id} =  Get Current Record Id
    Should Be Equal  &{contact}[Id]  ${contact_id}
    [Teardown]  Close Browser

Go To Setup Home
    Open Test Browser
    Go To Setup Home
    [Teardown]  Close Browser

Go To Setup Object Manager
    Open Test Browser
    Go To Setup Object Manager
    [Teardown]  Close Browser

Go To Object Home
    Open Test Browser
    Go To Object List  Contact
    [Teardown]  Close Browser

Go To Object List
    Open Test Browser
    Go To Object List  Contact
    [Teardown]  Close Browser

Go To Object List With Filter
    Open Test Browser
    Go To Object List  Contact  filter=Recent
    [Teardown]  Close Browser

Go To Record Home
    Open Test Browser
    &{contact} =  Create Contact
    Go To Record Home  &{contact}[Id]
    Salesforce Delete  Contact  &{contact}[Id]
    [Teardown]  Close Browser

Log In
    Open Test Browser
    Wait Until Loading Is Complete
    Page Should Contain  Home
    [Teardown]  Close Browser

Populate Field
    Open Test Browser
    ${account_name} =  Generate Random String
    Go To Object Home  Account
    Click Object Button  New
    Populate Field  Account Name  ${account_name}
    ${locator} =  Get Locator  object.field  Account Name
    ${value} =  Get Value  ${locator}
    Should Be Equal  ${value}  ${account_name}
    [Teardown]  Close Browser

Populate Form
    Open Test Browser
    ${account_name} =  Generate Random String
    Go To Object Home  Account
    Click Object Button  New
    Populate Form  Account Name=${account_name}
    ${locator} =  Get Locator  object.field  Account Name
    ${value} =  Get Value  ${locator}
    Should Be Equal  ${value}  ${account_name}
    [Teardown]  Close Browser

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
    [Teardown]  Salesforce Delete  Contact  ${contact_id}
    
Salesforce Update
    &{contact} =  Create Contact
    ${new_last_name} =  Generate Random String
    Salesforce Update  Contact  &{contact}[Id]  LastName=${new_last_name}
    &{contact} =  Salesforce Get  Contact  &{contact}[Id]
    Should Be Equal  &{contact}[LastName]  ${new_last_name}
    [Teardown]  Salesforce Delete  Contact  &{contact}[Id]

Salesforce Query
    &{new_contact} =  Create Contact
    @{records} =  Salesforce Query  Contact
    ...              select=Id,FirstName,LastName
    ...              Id=&{new_contact}[Id]
    &{contact} =  Get From List  ${records}  0
    Should Be Equal  &{contact}[Id]  &{new_contact}[Id]
    Should Be Equal  &{contact}[FirstName]  &{new_contact}[FirstName]
    Should Be Equal  &{contact}[LastName]  &{new_contact}[LastName]
    [Teardown]  Salesforce Delete  Contact  &{new_contact}[Id]

SOQL Query
    &{new_contact} =  Create Contact
    &{result} =  Soql Query  Select Id, FirstName, LastName from Contact WHERE Id = '&{new_contact}[Id]'
    @{records} =  Get From Dictionary  ${result}  records
    Log Variables
    &{contact} =  Get From List  ${records}  0
    Should Be Equal  &{result}[totalSize]  ${1}
    Should Be Equal  &{contact}[FirstName]  &{new_contact}[FirstName]
    Should Be Equal  &{contact}[LastName]  &{new_contact}[LastName]
    [Teardown]  Salesforce Delete  Contact  &{new_contact}[Id]
