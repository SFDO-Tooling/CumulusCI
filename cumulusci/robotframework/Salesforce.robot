*** Settings ***

Library        Collections
Library        String
Library        SeleniumLibrary  implicit_wait=${IMPLICIT_WAIT}  timeout=${TIMEOUT}
Library        cumulusci.robotframework.CumulusCI  ${ORG}
Library        cumulusci.robotframework.Salesforce  debug=${DEBUG}

*** Variables *** 
${BROWSER}          chrome
${BROWSER_VERSION}  latest
${DEBUG}            ${false}
${CAPABILITIES}     ${empty}
${IMPLICIT_WAIT}    7.0
${TIMEOUT}          7.0

*** Keywords ***

Delete Records and Close Browser
    Close Browser
    Delete Session Records

Open Test Browser
    ${login_url} =  Login Url
    Open Browser  ${login_url}  ${BROWSER}  desired_capabilities=version:${BROWSER_VERSION}${CAPABILITIES}
    Sleep  2
    Wait Until Loading Is Complete
    #Run Keyword If  '${BROWSER}' == 'chrome'  Open Test Browser Chrome
    #...    ELSE IF  '${BROWSER}' == 'firefox'  Open Test Browser Firefox
    #Go To  ${LOGIN_URL}

Open Test Browser Chrome
    ${chrome_options} =  Evaluate  sys.modules['selenium.webdriver'].ChromeOptions()  sys
    Call Method  ${chrome_options}  add_argument  --disable-notifications
    Create Webdriver  Chrome  timeout=${IMPLICIT_WAIT}  chrome_options=${chrome_options}

Open Test Browser Firefox
    Create Webdriver  Firefox
