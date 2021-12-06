*** Settings ***
Documentation
...  Tests for auto-detecting classic mode in a scratch org

Resource  cumulusci/robotframework/Salesforce.robot
Library   cumulusci/robotframework/tests/salesforce/TestListener.py

Suite Setup  Run keywords
...  Get URLs for switching
...  AND  Open test browser  wait=False
...  AND  Switch to classic

Suite Teardown  Run keywords
...  Switch to lightning
...  AND  Close all browsers

*** Keywords ***
Get current user experience
    log  not implemented yet

Switch to classic
    Go to  ${switcher classic url}
    Wait for aura

Switch to lightning
    ${org info}=  Get org info
    Go to  ${switcher lex url}
    Wait for aura

Get urls for switching
    ${org info}=  Get org info
    set suite variable  ${switcher lex url}
    ...  ${org info['instance_url']}/ltng/switcher?destination=lex
    set suite variable  ${switcher classic url}
    ...  ${org info['instance_url']}/ltng/switcher?destination=classic

*** Test Cases ***
Auto-switch to lightning
    [Setup]  Run keywords
    ...  Close all browsers
    ...  Reset test listener keyword log
    ...  Reset test listener message log

    Open Test Browser
    Assert keyword status
    ...  PASS
    ...  cumulusci.robotframework.Salesforce.Wait Until Salesforce Is Ready
    ...  timeout=180

    Assert robot log  It appears we are on a classic page   WARN
    capture page screenshot