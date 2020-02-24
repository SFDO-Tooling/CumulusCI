*** Settings ***

Documentation
...  This resource file imports the Salesforce and CumulusCI
...  keyword libraries, along with several other commonly used
...  libraries (Collections, OperatingSystem, String, XML). In
...  addition, it defines several other keywords.
...
...  This resource file also defines several global variables,
...  including ``${BROWSER}``, ``${ORG}``, and ``${DEFAULT_BROWSER_SIZE}``
...
...  This resource file should be included in every test suite,
...  like in the following example (note: there should be two
...  or more spaces after ``Resource``):
...
...  | ``*** Settings ***``
...  | ``Resource   cumulusci/robotframework/Salesforce.robot``

Library        Collections
Library        OperatingSystem
Library        String
Library        XML
Library        SeleniumLibrary  implicit_wait=${IMPLICIT_WAIT}  timeout=${TIMEOUT}
Library        cumulusci.robotframework.CumulusCI  ${ORG}
Library        cumulusci.robotframework.Salesforce  debug=${DEBUG}

*** Variables ***
${BROWSER}          chrome
${SELENIUM_SPEED}   0
${DEBUG}            ${false}
${CHROME_BINARY}    ${empty}
${ORG}              ${empty}
${IMPLICIT_WAIT}    7.0
${INITIAL_TIMEOUT}  180.0
${TIMEOUT}          30.0
${LOCATION STRATEGIES INITIALIZED}  ${False}
${DEFAULT BROWSER SIZE}  1280x1024

*** Keywords ***

Delete Records and Close Browser
    [Documentation]
    ...  This will close all open browser windows and then delete
    ...  all records created with the Salesforce API during this
    ...  testing session.
    Close All Browsers
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
    [Documentation]
    ...  Opens a test browser to the org.
    ...
    ...  The variable ${BROWSER} determines which browser should
    ...  open. The following four browsers are explicitly supported:
    ...  chrome, firefox, headlesschrome, and headlessfirefox. Any
    ...  other value will be passed directly to the SeleniumLibrary
    ...  'Open Browser' keyword.
    ...
    ...  Once the browser has been opened, it will be set to the given
    ...  size (default=${DEFAULT BROWSER SIZE})
    ...
    ...  The keyword `Log Browser Capabilities` will automatically be called.

    [Arguments]  ${size}=${DEFAULT BROWSER SIZE}  ${alias}=${NONE}
    ${login_url} =  Login Url
    Run Keyword If  '${BROWSER}' == 'chrome'  Open Test Browser Chrome  ${login_url}  alias=${alias}
    ...    ELSE IF  '${BROWSER}' == 'firefox'  Open Test Browser Firefox  ${login_url}  alias=${alias}
    ...    ELSE IF  '${BROWSER}' == 'headlesschrome'  Open Test Browser Chrome  ${login_url}  alias=${alias}
    ...    ELSE IF  '${BROWSER}' == 'headlessfirefox'  Open Test Browser Headless Firefox  ${login_url}  alias=${alias}
    ...    ELSE  Open Browser  ${login_url}  ${BROWSER}  alias=${alias}
    Wait Until Salesforce Is Ready  timeout=180
    Set Selenium Timeout  ${TIMEOUT}
    Initialize Location Strategies
    ${width}  ${height}=  split string  ${size}  separator=x  max_split=1
    Set window size  ${width}  ${height}
    Set selenium speed  ${SELENIUM_SPEED}
    Log browser capabilities

Open Test Browser Chrome
    [Arguments]     ${login_url}  ${alias}=${NONE}
    ${options} =                Get Chrome Options
    Create Webdriver With Retry  Chrome  options=${options}  alias=${alias}
    Set Selenium Implicit Wait  ${IMPLICIT_WAIT}
    Set Selenium Timeout        ${TIMEOUT}
    Go To                       ${login_url}

Open Test Browser Firefox
    [Arguments]     ${login_url}  ${alias}=${NONE}
    Open Browser  ${login_url}  firefox  alias=${alias}

Open Test Browser Headless Firefox
    [Arguments]     ${login_url}  ${alias}=${NONE}
    Open Browser  ${login_url}  headlessfirefox  alias=${alias}

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
