*** Settings ***
Documentation
...  This suite tests the `Get All Picklist Values` keyword.
...  Specifically, it verifies that the keyword can open a Salesforce
...  Lightning picklist and return the available option values.

Library   String
Library   DateTime
Library   Collections
Resource  cumulusci/robotframework/Salesforce.robot

Suite Setup     run keywords
...  Open test browser
...  AND  Create opportunity
Suite Teardown  Delete Records and Close Browser


*** Keywords ***
Create opportunity
    [Documentation]
    ...  Creates a test opportunity with a random name and a close
    ...  date 30 days in the future. A reference to the created
    ...  opportunity will be stored in the suite variable ${opportunity}.

    ${30 days from now}=  Get Current Date  increment=30 days  result_format=%Y-%m-%d
    ${random}=            Generate random string  8  [NUMBERS]
    ${opportunity_id}=    Salesforce Insert  Opportunity
    ...                   Name=Picklist Test ${random}
    ...                   CloseDate=${30 days from now}
    ...                   Amount=100000
    ...                   Probability=42
    ...                   StageName=Prospecting
    ...                   Description=Picklist keyword test
    &{opportunity}=       Salesforce Get  Opportunity  ${opportunity_id}
    set suite variable    ${opportunity}
    [Return]              ${opportunity}


*** Test Cases ***
Test Get All Picklist Values
    [Documentation]
    ...  Verify that Get All Picklist Values returns available values
    ...  from a Lightning picklist field.

    [Setup]  run keywords
    ...  go to object home     Opportunity
    ...  AND  click link       ${opportunity['Name']}
    ...  AND  click object button   Edit
    ...  AND  wait until modal is open

    ${values}=  Get All Picklist Values  Stage
    Log  ${values}

    Run keyword and continue on failure
    ...  Should Not Be Empty
    ...  ${values}
    ...  Expected Stage picklist values to be returned but received an empty list

    Run keyword and continue on failure
    ...  List Should Contain Value
    ...  ${values}
    ...  Prospecting
    ...  Expected Stage picklist to contain 'Prospecting' but values were '${values}'