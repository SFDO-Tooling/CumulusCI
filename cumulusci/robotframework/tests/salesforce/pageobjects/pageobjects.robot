*** Settings ***
Resource        cumulusci/robotframework/Salesforce.robot
Library         cumulusci.robotframework.PageObjects
...  ${CURDIR}/example_page_object.py

Suite Setup     Run keywords
...  Create test data
...  AND  Open Test Browser
Suite Teardown  Delete Records and Close Browser

*** Keywords ***
Create Test Data
    Salesforce Insert  Contact  FirstName=Inigo  LastName=Montoya

*** Test Cases ***
Go to page and current page should be, using defined page object
    [Documentation]  Verify we can go to an implemented page object
    Go to page              About  Blank
    Current page should be  About  Blank

Go to page, using generic page object
    [Documentation]
    ...  Verify we can go to a page object for which there is
    ...  no explicit definition, but for which there is a generic
    ...  (base) class.
    Go to page    Listing  Contact
    Current page should be  Listing  Contact

Call keyword of defined page object
    # verify we can call the keyword in that page object
    load page object  About  Blank
    ${result}=  Hello  world
    should be equal  ${result}  About:Blank Page says Hello, world

Load page object, using defined page object
    Load page object  About  Blank

Load page object, using generic page object
    [Documentation]
    ...  Verify that 'load page object' works when using a generic
    ...  page object
    Load page object  Listing  Contact

Current page should be, using generic page object
    [Documentation]
    ...  Verify that 'current page should be' works when
    ...  using a generic page object
    [Setup]  Go to page  Listing  Task

    Current page should be  Listing  Task
    Location should contain  /lightning/o/Task/list

Current page should be throws appropriate error
    [Documentation]
    ...  Verifies the error that is thrown when 'current page should be'
    ...  is false
    [Setup]  load page object  Listing  Contact

    ${location}=  get location
    run keyword and expect error   Expected location to be 'about:blank' but it was '${location}'
    ...  current page should be  About  Blank

Error when no page object can be found
    [Documentation]
    ...  Verify we get an error if no page object exists, and
    ...  there is no suitable base class

    Run keyword and expect error
    ...  Unable to find a page object for 'Foo Bar'
    ...  Go to page  Foo  Bar

Log page object keywords
    [Documentation]  Verify that 'log page object keywords' doesn't throw an error
    # All we're doing here is verifying it doesn't throw an error.
    # Unfortunately there's no way to verify the robot log message
    # was called (or is there...???)
    [Setup]  Load Page Object  About  Blank

    log page object keywords

Base class: HomePage
    [Documentation]
    ...  Verify we can go to the generic Home page
    ...  (assuming we don't have an explicit TaskHomePage)
    go to page  Home  Task
    Current page should be  Home  Task

Base class: ListingPage
    [Documentation]
    ...  Verify we can go to the generic Listing page
    ...  (assuming we don't have an explicit TaskListingPage)
    Go to page              Listing  Task
    Current page should be  Listing  Task

Base class: DetailPage
    [Documentation]
    ...  Verify we can go to the generic Detail page
    ...  (assuming we don't have an explicit TaskDetailPage)

    Go to page  Detail  Contact  firstName=Inigo  lastName=Montoya
    Current page should be  Detail  Contact  firstName=Inigo  lastName=Montoya

Base class: DetailPage with no matches

    run keyword and expect error  no Contact matches firstName=Nobody, lastName=Nobody
    ...  Go to page  Detail  Contact  firstName=Nobody  lastName=Nobody

Base class: DetailPage with more than one match
    [Setup]  run keywords
    ...  Salesforce Insert  Contact  FirstName=John  LastName=Smith
    ...  AND  Salesforce Insert  Contact  FirstName=John  LastName=Jones

    run keyword and expect error  Query returned 2 objects
    ...  Go to page  Detail  Contact  firstName=John
