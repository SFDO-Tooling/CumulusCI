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

    ...  Unfortunately, selenium doesn't provide introspection
    ...  so we'll just try a locator that should work

    [Setup]  Go to setup home

    Wait until page contains element     text:Mobile Publisher

Locator strategy 'title'
    [Documentation]
    ...  Test that the 'title' location strategy has been added

    ...  Unfortunately, selenium doesn't provide introspection
    ...  so we'll just try a locator that should work

    [Setup]  Go to setup home

    Wait until page contains element     title:Object Manager

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
