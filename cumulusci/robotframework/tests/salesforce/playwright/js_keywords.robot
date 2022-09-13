*** Settings ***
Resource  cumulusci/robotframework/SalesforcePlaywright.robot

Suite Setup     Open test browser
Suite Teardown  Close browser  ALL

*** Test Cases ***
Example
    # create a page object without args just to prove we can.
    ${po}=  accountSettingsPage
    log  page object: ${po}

    # call a method on the page object
    ${result}=  accountSettingsPage  doSomething  hello  world
    Should be equal as strings
    ...  ${result}
    ...  arg1: hello arg2: world

    accountSettingsPage  goto  Advanced User Details
    Sleep  5 seconds
    take screenshot