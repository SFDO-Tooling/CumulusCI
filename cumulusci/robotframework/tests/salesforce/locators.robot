*** Settings ***

Resource        cumulusci/robotframework/Salesforce.robot
Library         cumulusci/robotframework/tests/salesforce/TestListener.py
Library         TestLibraryA.py
Library         TestLibraryB.py
Library         Dialogs

Suite Setup     Open test browser
Suite Teardown  Close all browsers

*** Test Cases ***
Locator strategy 'text'
    [Documentation]
    ...  Test that the 'text' location strategy has been added
    [Setup]  Go to setup home

    # Try to use the locator strategy on an element
    # we know should be on the page.
    Wait until page contains element     text:Mobile Publisher

Locator strategy 'title'
    [Documentation]
    ...  Test that the 'title' location strategy has been added
    [Setup]  Go to setup home

    # Try to use the locator strategy on an element
    # we know should be on the page.
    Wait until page contains element     title:Object Manager

Locator strategy 'label'
    [Documentation]
    ...  Test that the 'label' location strategy has been added
    [Setup]  Run keywords
    ...  Go To Object Home           Contact
    ...  AND  Click Object Button    New
    [Teardown]  Close Modal

    # Try to use the locator strategy on an element
    # we know should be on the page.
    Wait until page contains element    label:Phone

Keyword library locators
    [Documentation]
    ...  Test that we can use custom locators with Selenium keywords

    ...  Both of the test libraries should have registered their own
    ...  locators. This test makes sure both of them were registered
    ...  and available for use.

    [Setup]  Go to setup home

    Wait until page contains element  A:breadcrumb: Home
    Wait until page contains element  B:appname:Setup

Invalid locator
    [Documentation]
    ...  Verify we give a reasonable error message if the locator
    ...  isn't found

    # Note: a:breadcrumb is valid, but it doesn't have a child
    # locator named 'bogus'
    Run keyword and expect error
    ...  locator A:breadcrumb.bogus not found
    ...  Page should not contain element  a:breadcrumb.bogus

Not enough arguments in locator
    [Documentation]
    ...  Verify that we give a reasonable error message if a locator
    ...  requires more arguments than it gets

    # Note: a:breadcrumb requires an argument
    Run keyword and expect error
    ...  Not enough arguments were supplied
    ...  Page should not contain element  a:breadcrumb


Show translated locator in the log
    [Documentation]
    ...  Verify the translated locator appears in the log

    Page should not contain element  A:something
    assert robot log                 locator: 'A:something' => '//whatever'

Page should not contain custom locator
    [Documentation]
    ...  Verify that a custom locator can be used in a context where
    ...  the locator doesn't exist.
    ...
    ...  It used to be that the locator manager would itself throw
    ...  an error if it couldn't find a locator. Now, it returns None
    ...  so that the keyword can be responsible for deciding if an
    ...  error should be thrown or not

    # we know this locator doesn't exist, but the keyword should
    # pass. Prior to the fix when this test was introduced, this would
    # give an error

    Page should not contain element  B:appname:Sorry Charlie


Get Webelement (singlular)
    [Documentation]
    ...  A smoke test to verify that we can get an element with a custom locator
    [Setup]  Go to setup home

    ${element}=        Get webelement  A:breadcrumb:Home
    # Different browsers return different classes of objects so we
    # can't easily do a check for the returned object type that works
    # for all browsers. We'll just have to assume that if the element
    # isn't None then it's a web element
    Should be true     $element is not None


Get Webelements (plural) - no matching elements

    [tags]   W-10187485

    # this is a locator which shouldn't match anything on the page
    ${locator}=   Get Locator  modal.button  Bogus
    ${elements}=  Get webelements  ${locator}

    # same locator, but using the custom locator strategy
    ${elements_via_locator_manager}=  Get webelements  sf:modal.button:Bogus

    # the two lists of elements should be identical. The bug reported
    # in W-10187485 caused the locator strategy to return [None]
    # instead of []. This verifies that we fixed that bug.
    Should be equal  ${elements}  ${elements via locator manager}

    # In addition to getting an empty list when trying to fetch
    # non-existing elements, this verifies that we can use the
    # locator in a negative test.
    Page should not contain  sf:modal.button:Bogus

Get Webelements (plural) with custom locator
    [Setup]  Run keywords
    ...  Go to object home  Contact
    ...  AND  Click object button  New

    # Get the web element with the xpath directly, then verify
    # that Get Webelements returns a list with just that element
    # when using the custom locator
    ${element}=  Get webelement  //div[contains(@class,'uiModal')]//button[.='Save & New']
    @{expected elements}=  Create list  ${element}

    ${actual elements}=  Get webelements  sf:modal.button:Save & New

    Should be equal  ${actual elements}  ${expected elements}
