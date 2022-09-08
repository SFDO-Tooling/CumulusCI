*** Settings ***
Resource  cumulusci/robotframework/SalesforcePlaywright.robot

#Suite Setup     Open test browser
#Suite Teardown  Close browser  ALL

*** Test Cases ***
Example
    # create a page object (not strictly necessary)
    ${po}=  myPageobject
    log  po: ${po}

    # call a method on the page object
    ${result}=  myPageObject  doSomething  hello  world
    Should be equal as strings
    ...  ${result}
    ...  arg1: hello arg2: world
