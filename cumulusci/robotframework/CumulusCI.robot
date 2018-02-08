*** Settings ***
Library        Selenium2Library                    implicit_wait=5.0
Library        cumulusci.robotframework.CumulusCI  ${ORG}
Test Setup     Test Set Up
Test Teardown  Close Browser

*** Keywords ***

Test Set Up
    Set Login Url

*** Test Cases ***
Test Log In
    Open Browser  ${LOGIN_URL}  chrome
    Run Task  create_package  package=TestPackage
    Capture Page Screenshot
    Page Should Contain  Home
