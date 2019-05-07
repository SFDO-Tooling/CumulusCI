*** Settings ***
Resource        cumulusci/robotframework/Salesforce.robot
Library         cumulusci.robotframework.PageObjects
Library         Dialogs

Suite Setup     Open Test Browser
Suite Teardown  Delete Records and Close Browser

*** Test Cases ***
Go to page 
    Go to page              Home  Contact
    Current page should be  Listing  Contact  # due to automatic redirect

Error when no page object can be found
    Run keyword and expect error
    ...  Unable to find a page object for 'Foo Bar'
    ...  Go to page  Foo  Bar
    