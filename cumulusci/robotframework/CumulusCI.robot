*** Settings ***

Library        SeleniumLibrary                    implicit_wait=5.0
Library        cumulusci.robotframework.CumulusCI  ${ORG}
Library        cumulusci.robotframework.Salesforce
Suite Setup    Set Login Url
#Test Teardown  Close Browser

*** Variables ***

${BROWSER}  chrome

*** Keywords ***

Open Test Browser
    Run Keyword If  '${BROWSER}' == 'chrome'  Open Test Browser Chrome
    ...    ELSE IF  '${BROWSER}' == 'firefox'  Open Test Browser Firefox
    Go To  ${LOGIN_URL}

Open Test Browser Chrome
    ${chrome_options} =  Evaluate  sys.modules['selenium.webdriver'].ChromeOptions()  sys
    Call Method  ${chrome_options}  add_argument  --disable-notifications
    Create Webdriver  Chrome  chrome_options=${chrome_options}

Open Test Browser Firefox
    Create Webdriver  Firefox

*** Test Cases ***

Test Log In
    Open Test Browser
    Capture Page Screenshot
    Page Should Contain  Home
    Open App Launcher
    Select App Launcher App  Service
    Open App Launcher
    Select App Launcher Tab  Contracts
