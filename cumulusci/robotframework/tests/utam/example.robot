*** Settings ***
Resource  cumulusci/robotframework/Salesforce.robot
Library   cumulusci.robotframework.UTAMLibrary
Library    SeleniumLibrary

Suite Setup     Open Browser  https://lwc.dev
Suite Teardown  Close browser

Default tags    utam

*** Test Cases ***
Smoke Test
    [Documentation]  Basic smoke test to see if we can load and use a UTAM page object

    get utam object  lwc-home
    ${header}=       lwc-home  getHeader

    Should be equal  ${header.text}  Lightning Web Components

Error when calling getter on bogus element
    get utam object  lwc-home
    run keyword and expect error
    ...  Unknown method name 'getBogusElement'. Must be 'getHeader'.
    ...  lwc-home  getBogusElement
