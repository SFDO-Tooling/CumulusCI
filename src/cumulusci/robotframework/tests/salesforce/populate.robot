*** Settings ***
Documentation
...  This suite tests the `Populate Field` keyword.
...  Specifically, it verifies that the keyword properly
...  overwrites previous values. We had some bugs where
...  new values were getting appended rather than replacing
...  existing values.
...
...  This suite uses an opportunity, since the edit dialog
...  has several different field types on it.

Library   String
Library   DateTime
Resource  cumulusci/robotframework/Salesforce.robot

Suite Setup     run keywords
...  Open test browser
...  Create opportunity
Suite Teardown  Delete Records and Close Browser

*** Keywords ***
Create opportunity
    [Documentation]
    ...  Creates a test opportunity with a random name and a close
    ...  date 30 days in the future. A reference to the created
    ...  opportunity will be stored in the suite variable ${opportunity},
    ...  and be return as the result of this keyword.

    ${30 days from now}=  Get Current Date  increment=30 days  result_format=%Y-%m-%d
    ${random}=  Generate random string  8  [NUMBERS]
    ${opportunity_id}=    Salesforce Insert  Opportunity
    ...                   Name=Test Opportunity ${random}
    ...                   CloseDate=${30 days from now}
    ...                   Amount=100000
    ...                   Probability=42
    ...                   StageName=Prospecting
    ...                   Description=Clever description here
    &{opportunity}=       Salesforce Get  Opportunity  ${opportunity_id}
    set suite variable    ${opportunity}
    [Return]  ${opportunity}

Verify "populate field" replaces previous value
    [Arguments]  ${field name}  ${new value}
    [Documentation]
    ...  Verify that a field has the expected value after calling 'populate field'
    ...  This keyword will NOT cause the test to fail immediately, so that we can
    ...  check multiple fields before the test completes

    populate field      ${field name}    ${new value}
    ${actual value}=    get field value  ${field name}

    run keyword and continue on failure
    ...  should be equal as strings  ${new value}  ${actual value}
    ...  Expected modal field ${field name} to be '${new value}' but it was '${actual value}'

*** Test cases ***
Test Populate ability to clear a field
    [Documentation]
    ...  We've had problems with the populate keyword not always
    ...  clearing the field before inserting text. This will try
    ...  to set various fields to a new value and verify that the
    ...  new value overwrites the old rather than append to it

    [Setup]  run keywords
    ...  go to object home     Opportunity
    ...  AND  click link            ${opportunity['Name']}
    ...  AND  click object button   Edit
    ...  AND  wait until modal is open

    ${60 days from now}=  Get Current Date  increment=60 days  result_format=%Y-%m-%d

    ## currency / number
    Verify "populate field" replaces previous value  Amount            90000

    ## string
    Verify "populate field" replaces previous value  Next Step         whatever

    ## percentage / number
    Verify "populate field" replaces previous value  Probability (%)   99

    ## multi-line text field
    Verify "populate field" replaces previous value  Description       yada yada yada

    ## date field
    # N.B. Close date is last because it pops up a date dialog. If there
    # are more fields after, we have to wait for the dialog to be dismissed.
    # This test is just easier if we modify the date last so we don't have to
    # deal with that.
    Verify "populate field" replaces previous value  Close Date        ${60 days from now}
