** Settings ***
Resource        cumulusci/robotframework/SalesforcePlaywright.robot
Library         cumulusci/robotframework/tests/salesforce/TestListener.py

Suite Setup     Open Test Browser
Suite Teardown  Delete Records and Close Browser

Force Tags      playwright

*** Keywords ***
Create Test Contact
    [Arguments]      &{fields}
    ${first_name} =  Get fake data  first_name
    ${last_name} =   Get fake data  last_name
    ${contact_id} =  Salesforce Insert  Contact
    ...                FirstName=${first_name}
    ...                LastName=${last_name}
    ...                &{fields}
    &{contact} =     Salesforce Get  Contact  ${contact_id}
    [return]  &{contact}

*** Test Cases ***
Get Current Record Id
    [Documentation]    Verify that `Get Current Record Id` returns the correct id

    &{contact} =       Create Test Contact
    Go To Record Home  ${contact}[Id]
    # this fetches the ID from the URL; we expect that the keyword
    # will return the ID of the record we just created and navigated
    #  to
    ${contact_id} =    Get Current Record Id
    Should Be Equal    ${contact}[Id]  ${contact_id}
