*** Settings ***

Resource  cumulusci/robotframework/CumulusCI.robot
Resource  cumulusci/robotframework/Salesforce.robot
Force Tags  no-browser

*** Test Cases ***

# Make sure elapsed time log parser doesn't choke on this.
Test Perf - Parser does not choke with no keywords - Should Fail
    [Tags]      noncritical


Test Set Test Elapsed Time
    Set Test Elapsed Time       11655.9
    Set Test Metric       Donuts        42.3
