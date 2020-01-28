*** Settings ***

Resource        cumulusci/robotframework/Salesforce.robot
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

Show translated locator on error
    [Documentation]
    ...  Verify the translated locator appears in the error message

    [Setup]     Register keyword to run on failure  NONE
    [Teardown]  Register keyword to run on failure  Capture page screenshot

    ${expected error}=  Catenate  SEPARATOR=${\n}
    ...  Element with locator 'B:appname:Sorry Charlie' not found
    ...  translated: '//div[contains(@class, 'appName') and .='Sorry Charlie']'

    Run keyword and expect error  EQUALS:${expected error}
    ...  Page should contain element  B:appname:Sorry Charlie
