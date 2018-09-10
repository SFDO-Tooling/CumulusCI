*** Settings ***

Resource        cumulusci/robotframework/Salesforce.robot
Suite Setup     Open Test Browser
Suite Teardown  Delete Records and Close Browser

*** Test Cases ***

Via API
    ${first_name} =       Generate Random String
    ${last_name} =        Generate Random String
    ${contact_id} =       Salesforce Insert  Contact
    ...                     FirstName=${first_name}
    ...                     LastName=${last_name}
    &{contact} =          Salesforce Get  Contact  ${contact_id}
    Validate Contact      ${contact_id}  ${first_name}  ${last_name}

Via UI
    ${first_name} =       Generate Random String
    ${last_name} =        Generate Random String
    Go To Object Home     Contact
    Click Object Button   New
    Populate Form
    ...                   First Name=${first_name}
    ...                   Last Name=${last_name}
    Click Modal Button    Save
    Wait Until Modal Is Closed
    ${contact_id} =       Get Current Record Id
    Store Session Record  Contact  ${contact_id}
    Validate Contact      ${contact_id}  ${first_name}  ${last_name}
     

*** Keywords ***

Validate Contact
    [Arguments]          ${contact_id}  ${first_name}  ${last_name}
    # Validate via UI
    Go To Record Home    ${contact_id}
    Page Should Contain  ${first_name} ${last_name}
    # Validate via API
    &{contact} =     Salesforce Get  Contact  ${contact_id}
    Should Be Equal  ${first_name}  &{contact}[FirstName]
    Should Be Equal  ${last_name}  &{contact}[LastName]


