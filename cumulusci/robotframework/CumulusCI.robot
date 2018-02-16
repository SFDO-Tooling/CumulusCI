*** Settings ***

Library        SeleniumLibrary                    implicit_wait=${IMPLICIT_WAIT}
Library        cumulusci.robotframework.CumulusCI  ${ORG}
Library        cumulusci.robotframework.Salesforce
Suite Setup    Set Login Url
Test Setup     Open Test Browser
Test Teardown  Close Browser

*** Variables *** 
${BROWSER}  chrome
${IMPLICIT_WAIT}  5.0

*** Keywords ***

Open Test Browser
    Open Browser  ${LOGIN_URL}  ${BROWSER}
    #Run Keyword If  '${BROWSER}' == 'chrome'  Open Test Browser Chrome
    #...    ELSE IF  '${BROWSER}' == 'firefox'  Open Test Browser Firefox
    #Go To  ${LOGIN_URL}

Open Test Browser Chrome
    ${chrome_options} =  Evaluate  sys.modules['selenium.webdriver'].ChromeOptions()  sys
    Call Method  ${chrome_options}  add_argument  --disable-notifications
    Create Webdriver  Chrome  timeout=${IMPLICIT_WAIT}  chrome_options=${chrome_options}

Open Test Browser Firefox
    Create Webdriver  Firefox

*** Test Cases ***

Test Log In
    Page Should Contain  Home

Test App Launcher App
    Open App Launcher
    Select App Launcher App  Service
    Current App Should Be  Service

Test App Launcher Tab
    Open App Launcher
    Select App Launcher Tab  Contracts

Test App Launcher App and Tab
    Open App Launcher
    Select App Launcher App  Service
    Current App Should Be  Service
    Open App Launcher
    Select App Launcher Tab  Contracts
