*** Settings ***
Resource        cumulusci/robotframework/Salesforce.robot
Library         Collections
Library         cumulusci.robotframework.PageObjects
...  ${CURDIR}/example_page_object.py

Suite Setup     Run keywords
...  Create test data
...  AND  Open Test Browser
Suite Teardown  Delete Records and Close Browser

*** Keywords ***
Create Test Data
    [Documentation]
    ...  Create contacts used by tests in this suite

    # Delete all cases, in case they are holding on to some contacts
    ${records}=  Salesforce Query  Case
    FOR  ${record}  IN  @{records}
        Salesforce Delete  Case  ${record['Id']}
    END

    # Next, delete all existing contacts
    ${records}=  Salesforce Query  Contact
    FOR  ${record}  IN  @{records}
        Salesforce Delete  Contact  ${record['Id']}
    END

    # Next, add the ones we need
    Salesforce Insert  Contact  LastName=MacLeod  FirstName=Connor  Phone=555-123-1000
    Salesforce Insert  Contact  LastName=Doe      Phone=555-123-1001
    Salesforce Insert  Contact  LastName=Doe      Phone=555-123-1002

Status info should contain
    [Documentation]
    ...  Verifies that the status info contains the given text
    [Arguments]  ${expected}

    ${text}=  Get text  sf:object_list.status_info
    Should contain  ${text}  ${expected}
    ...  msg=Element text '${text}' does not contain '${expected}'
    ...  values=False

*** Test Cases ***
ListingPage - Smoke test
    [Documentation]
    ...  Verify we can go to the generic Listing page
    ...  (assuming we don't have an explicit TaskListingPage)
    Go to page              Listing  Task
    Current page should be  Listing  Task

ListingPage - Select Rows
    [Documentation]
    ...  Verify that the 'Select Rows' keyword works
    [Setup]  Run keywords
    ...  Go to page              Listing  Contact
    ...  AND  wait until element is not visible   sf:spinner

    Select rows  Doe
    Status info should contain  2 items selected

ListingPage - Select Rows when already selected
    [Documentation]
    ...  Verify that the 'Select Rows' keyword doesn't toggle
    ...  already selected rows
    [Setup]  Run keywords
    ...  Go to page              Listing  Contact
    ...  AND  wait until element is not visible   sf:spinner

    Select rows  Doe
    Status info should contain  2 items selected

    Select rows  Doe
    Status info should contain  2 items selected

ListingPage - Select Rows - No matching rows
    [Documentation]
    ...  Verify that 'Select Rows' raises an appropriate error
    ...  when no rows can be found
    [Setup]  Run keywords
    ...  Go to page              Listing  Contact
    ...  AND  wait until element is not visible   sf:spinner

    Run keyword and expect error
    ...  No rows matched 'Bogus'
    ...  Select rows  Bogus

ListingPage - Deselect Rows
    [Documentation]
    ...  Verify that the 'Deselect Rows' keyword works
    [Setup]  Run keywords
    ...  Go to page              Listing  Contact
    ...  AND  wait until element is not visible   sf:spinner

    Select rows  Doe  Connor MacLeod
    Status info should contain  3 items selected

    # deselect via name column
    Deselect rows  Doe
    Status info should contain  1 item selected

    # deselect one more via phone column
    Deselect rows  555-123-1000
    Status info should contain  3 items

ListingPage - Deselect Rows - No matching rows
    [Documentation]
    ...  Verify that the 'Deselect Rows' keyword raises an appropriate error
    [Setup]  Run keywords
    ...  Go to page              Listing  Contact
    ...  AND  wait until element is not visible   sf:spinner

    Run keyword and expect error
    ...  No rows matched 'Bogus'
    ...  Select rows  Bogus
