*** Settings ***

Resource        cumulusci/robotframework/Salesforce.robot
Suite Setup     Open Test Browser
Suite Teardown  Delete Records and Close Browser

*** Keywords ***

Create Contact
    ${first_name} =  Generate Random String
    ${last_name} =  Generate Random String
    ${contact_id} =  Salesforce Insert  Contact  FirstName=${first_name}  LastName=${last_name}
    &{contact} =  Salesforce Get  Contact  ${contact_id}
    [return]  &{contact}

*** Test Cases ***

Click Modal Button
    Go To Object Home  Contact
    Click Object Button  New
    Click Modal Button  Save
    ${locator} =  Get Locator  modal.has_error
    Page Should Contain Element  ${locator}

Click Object Button
    Go To Object Home  Contact
    Click Object Button  New
    Page Should Contain  New Contact

Click Related List Button
    &{contact} =  Create Contact
    Go To Record Home  &{contact}[Id]
    Click Related List Button  Opportunities  New
    Wait Until Modal Is Open
    Page Should Contain  New Opportunity

Get Current Record Id
    &{contact} =  Create Contact
    Go To Record Home  &{contact}[Id]
    ${contact_id} =  Get Current Record Id
    Should Be Equal  &{contact}[Id]  ${contact_id}

Go To Setup Home
    Go To Setup Home

Go To Setup Object Manager
    Go To Setup Object Manager

Go To Object Home
    Go To Object List  Contact

Go To Object List
    Go To Object List  Contact

Go To Object List With Filter
    Go To Object List  Contact  filter=Recent

Go To Record Home
    &{contact} =  Create Contact
    Go To Record Home  &{contact}[Id]

Populate Field
    ${account_name} =  Generate Random String
    Go To Object Home  Account
    Click Object Button  New
    Populate Field  Account Name  ${account_name}
    ${locator} =  Get Locator  object.field  Account Name
    ${value} =  Get Value  ${locator}
    Should Be Equal  ${value}  ${account_name}

Populate Form
    ${account_name} =  Generate Random String
    Go To Object Home  Account
    Click Object Button  New
    Populate Form  Account Name=${account_name}
    ${locator} =  Get Locator  object.field  Account Name
    ${value} =  Get Value  ${locator}
    Should Be Equal  ${value}  ${account_name}
