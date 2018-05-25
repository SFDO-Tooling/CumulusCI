*** Settings ***

Library        Collections
Library        String
Library        SeleniumLibrary  implicit_wait=${IMPLICIT_WAIT}  timeout=${TIMEOUT}
Library        cumulusci.robotframework.CumulusCI  ${ORG}
Library        cumulusci.robotframework.Salesforce  debug=${DEBUG}

*** Variables *** 
${BROWSER}          chrome
${BROWSER_VERSION}  ${empty}
${DEBUG}            ${false}
${CHROME_BINARY}    ${empty}
${FIREFOX_BINARY}   ${empty}
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
    ...    ELSE IF  '${BROWSER}' == 'headlesschrome'  Open Test Browser Headless Chrome  ${login_url}
    ...    ELSE IF  '${BROWSER}' == 'headlessfirefox'  Open Test Browser Headless Firefox  ${login_url}
    ...    ELSE  Open Browser  ${login_url}  ${BROWSER}  desired_capabilities=version:${BROWSER_VERSION}
    Sleep  2
    Wait Until Loading Is Complete

Open Test Browser Chrome
    [Arguments]     ${login_url}
    Run Keyword If  '${CHROME_BINARY}' == ''  Open Browser  ${login_url}  chrome  desired_capabilities=version:${BROWSER_VERSION}
    ...       ELSE  Open Browser  ${login_url}  chrome  desired_capabilities=version:${BROWSER_VERSION},chrome.binary:${CHROME_BINARY}

Open Test Browser Firefox
    [Arguments]     ${login_url}
    Run Keyword If  '${FIREFOX_BINARY}' == ''  Open Browser  ${login_url}  firefox  desired_capabilities=version:${BROWSER_VERSION}
    ...       ELSE  Open Browser  ${login_url}  firefox  desired_capabilities=version:${BROWSER_VERSION},firefox_binary:${FIREFOX_BINARY}

Open Test Browser Headless Chrome
    [Arguments]     ${login_url}
    Run Keyword If  '${CHROME_BINARY}' == ''  Open Browser  ${login_url}  headlesschrome  desired_capabilities=version:${BROWSER_VERSION}
    ...       ELSE  Open Browser  ${login_url}  headlesschrome  desired_capabilities=version:${BROWSER_VERSION},chrome.binary:${CHROME_BINARY}
 
Open Test Browser Headless Firefox
    [Arguments]     ${login_url}
    Run Keyword If  '${FIREFOX_BINARY}' == ''  Open Browser  ${login_url}  headlessfirefox  desired_capabilities=version:${BROWSER_VERSION}
    ...       ELSE  Open Browser  ${login_url}  headlessfirefox  desired_capabilities=version:${BROWSER_VERSION},firefox_binary:${FIREFOX_BINARY}
 
