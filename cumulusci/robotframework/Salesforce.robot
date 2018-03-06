*** Settings ***

Library        Collections
Library        String
Library        SeleniumLibrary  implicit_wait=${IMPLICIT_WAIT}  timeout=${TIMEOUT}
Library        cumulusci.robotframework.CumulusCI  ${ORG}
Library        cumulusci.robotframework.Salesforce  debug=${DEBUG}

*** Variables *** 
${BROWSER}  chrome
${DEBUG}  ${false}
${IMPLICIT_WAIT}  5.0
${TIMEOUT}  5.0

*** Keywords ***

Open Test Browser
    Open Browser  ${LOGIN_URL}  ${BROWSER}
    Sleep  2
    #Run Keyword If  '${BROWSER}' == 'chrome'  Open Test Browser Chrome
    #...    ELSE IF  '${BROWSER}' == 'firefox'  Open Test Browser Firefox
    #Go To  ${LOGIN_URL}

Open Test Browser Chrome
    ${chrome_options} =  Evaluate  sys.modules['selenium.webdriver'].ChromeOptions()  sys
    Call Method  ${chrome_options}  add_argument  --disable-notifications
    Create Webdriver  Chrome  timeout=${IMPLICIT_WAIT}  chrome_options=${chrome_options}

Open Test Browser Firefox
    Create Webdriver  Firefox
