*** Settings ***

Library        SeleniumLibrary  implicit_wait=${IMPLICIT_WAIT}  timeout=${TIMEOUT}
Library        cumulusci.robotframework.CumulusCI  ${ORG}
Library        cumulusci.robotframework.Salesforce  debug=${DEBUG}
Suite Setup    Set Login Url
Test Setup     Open Test Browser
Test Teardown  Close Browser

*** Variables *** 
${BROWSER}  chrome
${DEBUG}  ${false}
${IMPLICIT_WAIT}  5.0
${TIMEOUT}  7.0

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

Test SOQL Query
    ${result} =  Soql Query  Select Id, FirstName, LastName from Contact

Test App Launcher Tab
    Select App Launcher Tab  Contracts

Test App Launcher App
    Select App Launcher App  Service
    Current App Should Be  Service

Test App Launcher App and Tab
    Select App Launcher App  Service
    Current App Should Be  Service
    Select App Launcher Tab  Contracts
