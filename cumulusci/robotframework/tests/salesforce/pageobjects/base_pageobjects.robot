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
    ...  Create a Contact for Connor MacLeod if there isn't one. If there's
    ...  already more than one, it's a fatal error since some tests depend
    ...  on their being only one.
    ${result}=  Salesforce Query  Contact  Firstname=Connor  LastName=MacLeod
    run keyword if  len($result) > 1
    ...  Fatal Error  Expected to find only one contact named Connor MacLeod, found several
    run keyword if  len($result) == 0
    ...  Salesforce Insert  Contact  FirstName=Connor  LastName=MacLeod

*** Test Cases ***
HomePage
    [Documentation]
    ...  Verify we can go to the generic Home page
    ...  (assuming we don't have an explicit TaskHomePage)
    go to page  Home  Task
    Current page should be  Home  Task

DetailPage
    [Documentation]
    ...  Verify we can go to the generic Detail page
    ...  (assuming we don't have an explicit TaskDetailPage)

    Go to page  Detail  Contact  firstName=Connor  lastName=MacLeod
    # It is assumed only one contact will match. If there are several,
    # you might need to recreate your scratch org to clear out the duplicates
    Current page should be  Detail  Contact  firstName=Connor  lastName=MacLeod

DetailPage with no matches
    [Documentation]
    ...  Verify that we get an error if we try to go to a page for
    ...  an object that doesn't exist.

    run keyword and expect error  no Contact matches firstName=Nobody, lastName=Nobody
    ...  Go to page  Detail  Contact  firstName=Nobody  lastName=Nobody

DetailPage with more than one match
    [Documentation]
    ...  Verify that we get an error if we try to go to a detail
    ...  page that matches more than a single record

    [Setup]  run keywords
    ...  Salesforce Insert  Contact  FirstName=John  LastName=Smith
    ...  AND  Salesforce Insert  Contact  FirstName=John  LastName=Jones

    ${records}=   Salesforce query  Contact  firstName=John
    ${expected}=  get length  ${records}

    run keyword and expect error  Query returned ${expected} objects
    ...  Go to page  Detail  Contact  firstName=John

NewModal
    [Documentation]
    ...  Verify that we can use the NewModal page object keywords

    [Setup]  Go to page  Home  Contact
    Click object button  New
    Wait for modal      New  Contact
    Close the modal

NewModal - click modal button
    [Documentation]
    ...  Verify that we can use the NewModal 'click modal button' keyword

    [Setup]  Run keywords
    ...  Go to page  Home  Contact
    ...  AND  Click object button  New
    ...  AND  Wait for modal      New  Contact

    Click modal button  Cancel
    Wait until modal is closed

NewModal - Modal errors
    [Documentation]
    ...  Verify that we can detect errors in the model
    ...  with 'modal should contain errors' keyword (API < 51)
    ...  or 'Modal should show edit error for fields' (API >= 51)

    [Setup]  Run keywords
    ...  Go to page  Home  Contact
    ...  AND  Click object button  New
    ...  AND  Wait for modal      New  Contact

    Click modal button  Save
    capture page screenshot
    ${api}=   Get latest API version
    Modal should show edit error for fields   Name
