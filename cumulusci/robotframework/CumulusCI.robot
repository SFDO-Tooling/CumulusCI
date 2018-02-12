*** Settings ***

Library        SeleniumLibrary                    implicit_wait=5.0
Library        cumulusci.robotframework.CumulusCI  ${ORG}
Suite Setup    Set Login Url
Test Teardown  Close Browser

*** Variables ***

${BROWSER}  chrome

*** Test Cases ***

Test Log In
    Run Task  create_package  package=TestPackage
    Open Browser  ${LOGIN_URL}  ${BROWSER}
    Capture Page Screenshot
    Page Should Contain  Home
