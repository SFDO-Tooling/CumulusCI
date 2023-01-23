*** Settings ***
Documentation
...  Tests for auto-detecting classic mode in a scratch org

Resource  cumulusci/robotframework/SalesforcePlaywright.robot
Library   cumulusci/robotframework/tests/salesforce/TestListener.py
Library   Dialogs

Suite Setup  Run keywords
...  Get URLs for switching
...  AND  Open test browser  wait=False
...  AND  switch to classic
...  AND  close browser  ALL

Suite Teardown  Close Browser  ALL

*** Keywords ***
Switch to classic
    Go to  ${switcher classic url}
    Wait for elements state  a.switch-to-lightning  visible

Switch to lightning
    Go to  ${switcher lex url}
    Wait until loading is complete

Get urls for switching
    ${org info}=  Get org info
    set suite variable  ${switcher lex url}
    ...  ${org info['instance_url']}/ltng/switcher?destination=lex
    set suite variable  ${switcher classic url}
    ...  ${org info['instance_url']}/ltng/switcher?destination=classic

*** Test Cases ***
Auto-switch to lightning
    [Documentation]  Verify that if we land on a classic page that we auto-switch to lightning

    [Setup]  Run keywords
    ...  Close browser  ALL
    ...  AND  Reset test listener message log

    Open Test Browser  wait=True
    take screenshot

    # verify that we detected a classic page
    Assert robot log  It appears we are on a classic page   WARN

    # verify we landed on a lightning page
    ${url}=  Get URL  $=  /lightning/setup/SetupOneHome/home
