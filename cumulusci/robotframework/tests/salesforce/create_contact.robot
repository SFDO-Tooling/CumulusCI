*** Settings ***

Resource        cumulusci/robotframework/Salesforce.robot
Suite Setup     Open Test Browser
Suite Teardown  Delete Records and Close Browser
Library         cumulusci.robotframework.PageObjects


*** Test Cases ***

Via API
    ${first_name} =       Generate Random String
    ${last_name} =        Generate Random String
    ${contact_id} =       Salesforce Insert  Contact
    ...                     FirstName=${first_name}
    ...                     LastName=${last_name}
    &{contact} =          Salesforce Get  Contact  ${contact_id}
    Validate Contact      ${contact_id}  ${first_name}  ${last_name}

Create Contact through UI
    [Setup]  Run keywords
    ...       set test variable    ${first name}  ${fake.first_name()}
    ...  AND  set test variable    ${last name}   ${fake.last_name()}

    Go to page            Home  Contact
    Click object button   New

    Wait for page object  New  contact

    Populate Form
    ...                  First Name=${first name}
    ...                  Last Name=${last name}
    Click dialog button  Save

    Wait until dialog is closed

    # I want to get rid of the next keyword. What if we have 'smart'
    # variables like  'Store session record  Contact  ${current_contact_id()}
    # What I really wish is that variables could be properties, so I could
    # define a getter for ${current_contact_id}
    Get record ID from URL  ${contact_id}
    Store session record  Contact  ${contact_id}
    Validate Contact      ${contact_id}  ${first_name}  ${last_name}

Via UI
    [tags]  bryan

    ${first_name} =       Generate Random String
    ${last_name} =        Generate Random String

    Go to page            Home  Contact
    Click Object Button   New
    Wait for dialog       New  Contact

    Populate Form
    ...                   First Name=${first_name}
    ...                   Last Name=${last_name}
    Click Dialog Button   Save
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
