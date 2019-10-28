*** Settings ***
Resource        cumulusci/robotframework/Salesforce.robot
Library         Collections
Library         cumulusci.robotframework.PageObjects
...  ${CURDIR}/example_page_object.py

Suite Setup     Open Test Browser
Suite Teardown  Delete Records and Close Browser

*** Test Cases ***
Load page object, using defined page object
    [Documentation]
    ...  If we can't do this, all hope is lost!
    Load page object  About  Blank

Go to page automatically loads page object
    [Documentation]  Verify that 'go to page' automatically loads the page object
    Go to page    About  Blank
    ${pobj}=  log current page object
    Should not be equal  ${pobj}  ${None}

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

Go to page, using multiple generic pages
    [Documentation]
    ...  Verify we can use multiple generic page objects in the same
    ...  test. Earlier versions of the library had a bug that
    ...  prevented this from working. What was happening is that we
    ...  were giving the library a generic name like "DetailPage"
    ...  rather than a name that included the object type such as
    ...  "ContactDetailPage".

    Go to page  Listing  Contact
    Current page should be  Listing  Contact
    Go to page  Listing  Task
    Current page should be  Listing  Task
    Go to page  Detail  Contact
    Current page should be  Detail   Contact

Get page object
    [Documentation]
    ...  Verify that we can call the `get page object` keyword and that
    ...  it returns a page object
    [Setup]  Load page object     About  Blank

    ${pobj}=  Get page object  About  Blank
    Should not be equal  ${pobj}  ${NONE}

    @{keywords}=  Call method  ${pobj}  get_keyword_names

    # The page object should have three keywords we defined, plus
    # one from the base class
    ${expected}=  Create list  hello  keyword_one  keyword_two  log_current_page_object
    Lists should be equal  ${keywords}  ${expected}

Call keyword of defined page object
    [Documentation]
    ...  Verify we can call a keyword in a defined page object
    Load page object  About  Blank

    # "Hello" is a keyword in AboutBlankPage
    ${result}=  Hello  world
    should be equal  ${result}  About:Blank Page says Hello, world

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

    log current page object
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

Load multiple page objects in library search order
    [Documentation]
    ...  Loading a page object inserts it at the start of the
    ...  library search order. Verify that that happens properly.

    # Note: the library search order persists for the life of a suite
    # Therefore we need to reset it before running this test since
    # other tests will be loading page objects
    [Setup]  Set library search order  PageObjects

    Go to page   About     Blank
    Go to page   Home      Task
    Go to page   Listing   Contact

    # This should move HomeTask to the front. It should not
    # end up in the search order twice.
    Go to page   Home      Task

    # Note: the order is a list of strings, not actual libraries.
    ${actual_order}=       Set library search order
    ${expected_order}=     Create list  TaskHomePage  ContactListingPage  AboutBlankPage  PageObjects
    log  actual order: ${actual_order}
    Lists should be equal  ${actual_order}  ${expected_order}

Wait for page object
    Go to page    Listing  Contact
    Click object button  New

    Wait for page object  New  Contact

Wait for page object exception
    [Documentation]  Verify we throw an error if page object isn't found
    Go to page    Listing  Contact
    Run keyword and expect error
    ...  Unable to find a page object for 'BogusType BogusObject'
    ...  Wait for page object  BogusType  BogusObject

Wait for modal
    [Documentation]  Verify that the 'wait for modal' keyword works
    Go to page    Listing  Contact
    Click object button  New

    Wait for modal  New  Contact

Wait for modal exception
    [Documentation]  Verify we throw an error if page object isn't found
    Go to page    Listing  Contact
    Click object button  New

    Run keyword and expect error
    ...  Unable to find a page object for 'BogusType BogusObject'
    ...  Wait for modal  BogusType  BogusObject
