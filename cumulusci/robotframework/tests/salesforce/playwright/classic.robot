*** Settings ***
Documentation    Verify that `open test browser` handles classic pages
Resource         cumulusci/robotframework/SalesforcePlaywright.robot
Library          cumulusci/robotframework/tests/salesforce/TestListener.py


*** Keywords ***
Switch to classic
    ${org}=  Get org info
    # we don't need to wait for the page to fully render
    run keyword and ignore error
    ...  Go to  ${org}[instance_url]/ltng/switcher?destination=classic

Configure browser and test listener
    Open test browser
    Switch to classic
    Close browser
    Reset test listener keyword log

*** Test Cases ***
Check opening to classic page
    [Documentation]  Verify that we automatically switch from classic to lightning
    [Setup]          Configure browser and test listener
    [Teardown]       Close Browser

    # Assuming the setup worked, opening the browser should initially
    # land on a classic page. `Open test browser` will automatically
    # switch to the lightning page and issue a warning.
    Open test browser

    # assert that the warning was logged
    Assert robot log  It appears we are on a classic page   WARN

    # Assert we are no longer on a classic page, by checking
    # for the link at the top to switch to lightning
    Get element states
    ...  div.navLinks a.switch-to-lightning
    ...  not contains  visible
