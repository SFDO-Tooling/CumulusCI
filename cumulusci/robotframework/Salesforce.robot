*** Settings ***

Library        Collections
Library        String
Library        SeleniumLibrary  implicit_wait=${IMPLICIT_WAIT}  timeout=${TIMEOUT}
Library        cumulusci.robotframework.CumulusCI  ${ORG}
Library        cumulusci.robotframework.Salesforce  debug=${DEBUG}

*** Variables *** 
${BROWSER}          chrome
${DEBUG}            ${false}
${CHROME_BINARY}    ${empty}
${ORG}              ${empty}
${IMPLICIT_WAIT}    7.0
${TIMEOUT}          7.0

*** Keywords ***

Delete Records and Close Browser
    Close Browser
    Delete Session Records

Open Test Browser
    ${login_url} =  Login Url
    Run Keyword If  '${BROWSER}' == 'chrome'  Open Test Browser Chrome  ${login_url}
    ...    ELSE IF  '${BROWSER}' == 'firefox'  Open Test Browser Firefox  ${login_url}
    ...    ELSE IF  '${BROWSER}' == 'headlesschrome'  Open Test Browser Chrome  ${login_url}
    ...    ELSE IF  '${BROWSER}' == 'headlessfirefox'  Open Test Browser Headless Firefox  ${login_url}
    ...    ELSE  Open Browser  ${login_url}  ${BROWSER}  desired_capabilities=version:${BROWSER_VERSION}
    Sleep  2
    Wait Until Loading Is Complete

Open Test Browser Chrome
    [Arguments]     ${login_url}
    ${options} =                Get Chrome Options
    Create Webdriver            Chrome  options=${options}
    Set Selenium Implicit Wait  ${IMPLICIT_WAIT}
    Set Selenium Timeout        ${TIMEOUT}
    Go To                       ${login_url}

Open Test Browser Firefox
    [Arguments]     ${login_url}
    Open Browser  ${login_url}  firefox
 
Open Test Browser Headless Firefox
    [Arguments]     ${login_url}
    Open Browser  ${login_url}  headlessfirefox
 
Get Chrome Options
    ${options} =     Evaluate  selenium.webdriver.ChromeOptions()  modules=selenium
    Set Variable If  '${CHROME_BINARY}' != '${empty}'
    ...              ${options.binary_location}  ${CHROME_BINARY} 
    Run Keyword If   '${BROWSER}' == 'headlesschrome'
    ...              Call Method  ${options}  set_headless  ${true}
    [return]  ${options}

