*** Settings ***
Resource         cumulusci/robotframework/SalesforcePlaywright.robot

Suite Setup      Open test browser
Suite Teardown   Delete records and close browser

Force Tags       playwright

*** Test Cases ***
Create contact via app launcher and verify
    [Documentation]
    ...  End-to-end test exercising app launcher navigation, form population,
    ...  modal handling, and record verification via SalesforcePlaywright keywords.
    ...  This test is part of the Robot Framework maintenance comparison PoC.

    Open app launcher
    Select app launcher app    Sales
    Wait until loading is complete

    Click    css:.slds-page-header button[name='New']
    Wait until modal is open

    Populate form
    ...    First Name=Test
    ...    Last Name=RobotPlaywright

    Click modal button    Save
    Wait until modal is closed
    Wait until loading is complete

    ${record_id}=    Get current record id
    Should not be empty    ${record_id}
