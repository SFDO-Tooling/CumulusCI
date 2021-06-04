*** Settings ***
Resource  cumulusci/robotframework/Salesforce.robot
Library   cumulusci.robotframework.utam.UTAMLibrary

Suite Setup     Open Browser  https://lwc.dev
Suite Teardown  Close all browsers

*** Test Cases ***
Example
    log  hello, world

    # Load the root Utam Page Object
    import utam  lwc-home

    # Get the header element
    ${header}=  lwc-home  header

    # Assert the header text is what we expect
    # this part isn't very human-readable :-\
    Should be equal  ${header.getText()}  Lightning Web Components
