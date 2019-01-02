*** Settings ***

Library        Collections
Library        OperatingSystem
Library        String
Library        XML
Library        SeleniumLibrary  implicit_wait=${IMPLICIT_WAIT}  timeout=${TIMEOUT}
Library        cumulusci.robotframework.CumulusCI  ${ORG}
Library        cumulusci.robotframework.Salesforce  debug=${DEBUG}

*** Variables *** 
${BROWSER}          chrome
${DEBUG}            ${false}
${CHROME_BINARY}    ${empty}
${ORG}              ${empty}
${IMPLICIT_WAIT}    7.0
${INITIAL_TIMEOUT}  180.0
${TIMEOUT}          30.0

*** Keywords ***

Delete Records and Close Browser
    Close Browser
    Delete Session Records

Locate Element By Text
    [Arguments]  ${browser}  ${locator}  ${tag}  ${constraints}
    ${element}=  Get WebElement  //*[text()='${locator}']
    [Return]  ${element}

Locate Element By Title
    [Arguments]  ${browser}  ${locator}  ${tag}  ${constraints}
    ${element}=  Get WebElement  //*[@title='${locator}']
    [Return]  ${element}

Open Test Browser
    ${login_url} =  Login Url
    Run Keyword If  '${BROWSER}' == 'chrome'  Open Test Browser Chrome  ${login_url}
    ...    ELSE IF  '${BROWSER}' == 'firefox'  Open Test Browser Firefox  ${login_url}
    ...    ELSE IF  '${BROWSER}' == 'headlesschrome'  Open Test Browser Chrome  ${login_url}
    ...    ELSE IF  '${BROWSER}' == 'headlessfirefox'  Open Test Browser Headless Firefox  ${login_url}
    ...    ELSE  Open Browser  ${login_url}  ${BROWSER}
    Set Selenium Timeout  ${INITIAL_TIMEOUT}
    Wait Until Loading Is Complete
    Set Selenium Timeout  ${TIMEOUT}
    Add Location Strategy  text  Locate Element By Text
    Add Location Strategy  title  Locate Element By Title

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
    ${options} =    Evaluate  selenium.webdriver.ChromeOptions()  modules=selenium
    Run Keyword If  '${BROWSER}' == 'headlesschrome'
    ...             Chrome Set Headless  ${options}
    Run Keyword If  '${CHROME_BINARY}' != '${empty}'
    ...             Chrome Set Binary  ${options}
    Call Method  ${options}  add_argument  --disable-notifications
    [return]  ${options}

Chrome Set Binary
    [Arguments]  ${options}
    ${options.binary_location} =  Set Variable  ${CHROME_BINARY}
    [return]  ${options}

Chrome Set Headless
    [Arguments]  ${options}
    Call Method  ${options}  set_headless  ${true}
    Call Method  ${options}  add_argument  --disable-dev-shm-usage
    Call Method  ${options}  add_argument  --disable-background-timer-throttling
    [return]  ${options}
