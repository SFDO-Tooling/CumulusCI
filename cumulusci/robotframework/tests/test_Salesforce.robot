*** Settings ***

Resource       cumulusci/robotframework/Salesforce.robot
Suite Setup    Set Login Url

*** Keywords ***

Create Random Contact
    ${first_name} =  Generate Random String
    ${last_name} =  Generate Random String
    ${contact_id} =  Salesforce Insert  Contact  FirstName=${first_name}  LastName=${last_name}
    Set Test Variable  ${first_name}  ${first_name}
    Set Test Variable  ${last_name}  ${last_name}
    Set Test Variable  ${contact_id}  ${contact_id}

*** Test Cases ***

Test Click Object Button
    Open Test Browser
    Go To Object Home  Contact
    Click Object Button  New
    Page Should Contain  New Contact
    Capture Page Screenshot
    [Teardown]  Close Browser

Test Go To Setup Home
    Open Test Browser
    Go To Setup Home
    Capture Page Screenshot
    [Teardown]  Close Browser

Test Go To Setup Object Manager
    Open Test Browser
    Go To Setup Object Manager
    Capture Page Screenshot
    [Teardown]  Close Browser

Test Go To Object Home
    Open Test Browser
    Go To Object List  Contact
    Capture Page Screenshot
    [Teardown]  Close Browser

Test Go To Object List
    Open Test Browser
    Go To Object List  Contact
    Capture Page Screenshot
    [Teardown]  Close Browser

Test Go To Object List With Filter
    Open Test Browser
    Go To Object List  Contact  filter=Recent
    Capture Page Screenshot
    [Teardown]  Close Browser

Test Go To Record Home
    Open Test Browser
    Create Random Contact
    Go To Record Home  ${contact_id}
    Capture Page Screenshot
    Salesforce Delete  Contact  ${contact_id}
    [Teardown]  Close Browser

Test Log In
    Open Test Browser
    Wait Until Loading Is Complete
    Page Should Contain  Home
    Capture Page Screenshot
    [Teardown]  Close Browser

Test Salesforce Delete
    Log Variables
    Create Random Contact
    Salesforce Delete  Contact  ${contact_id}
    &{result} =  SOQL Query  Select Id from Contact WHERE Id = '${contact_id}'
    Should Be Equal  &{result}[totalSize]  ${0}

Test Salesforce Insert
    Create Random Contact
    &{contact} =  Salesforce Get  Contact  ${contact_id}
    Should Be Equal  &{contact}[FirstName]  ${first_name}
    Should Be Equal  &{contact}[LastName]  ${last_name}
    [Teardown]  Salesforce Delete  Contact  ${contact_id}
    
Test Salesforce Update
    Create Random Contact
    ${new_last_name} =  Generate Random String
    Salesforce Update  Contact  ${contact_id}  FirstName=${first_name}  LastName=${new_last_name}
    &{contact} =  Salesforce Get  Contact  ${contact_id}
    Should Be Equal  &{contact}[FirstName]  ${first_name}
    Should Be Equal  &{contact}[LastName]  ${new_last_name}
    [Teardown]  Salesforce Delete  Contact  ${contact_id}

Test SOQL Query
    Create Random Contact
    &{result} =  Soql Query  Select Id, FirstName, LastName from Contact WHERE Id = '${contact_id}'
    @{records} =  Get From Dictionary  ${result}  records
    Log Variables
    &{contact} =  Get From List  ${records}  0
    Should Be Equal  &{result}[totalSize]  ${1}
    Should Be Equal  &{contact}[FirstName]  ${first_name}
    Should Be Equal  &{contact}[LastName]  ${last_name}
    [Teardown]  Salesforce Delete  Contact  ${contact_id}
