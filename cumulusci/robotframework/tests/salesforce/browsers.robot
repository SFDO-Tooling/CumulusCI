*** Settings ***

Resource        cumulusci/robotframework/Salesforce.robot
Suite Teardown  Close all browsers


*** Variables ***
${DEFAULT WINDOW SIZE}  1280x1024

*** Keywords ***
Assert active browser count
    [Documentation]   Assert that an expected number of browsers are active
    [Arguments]       ${expected count}

    @{browsers}=      get active browser ids
    ${actual count}=  get length  ${browsers}
    Length should be  ${browsers}  ${expected count}
    ...  Expected to find ${expected count} open browsers, found ${actual count}


*** Test Cases ***
Open Test Browser Twice
    [Documentation]  Verify that we can open two browsers in a single test
    [Tags]  issue:1068
    [Teardown]  Close all browsers

    Assert active browser count  0
    Open test browser
    Open test browser
    Assert active browser count  2

Browser aliases
    [Documentation]  Verify that aliases are properly handled in Open Test Browser
    [Tags]  issue:1068
    [Setup]  Run keywords
    ...  Open test browser  alias=browser1
    ...  AND  Go to  https://metadeploy.herokuapp.com/products
    ...  AND  Open test browser  alias=browser2
    ...  AND  Go to  https://mrbelvedereci.herokuapp.com/
    [Teardown]  Close all browsers

    Switch browser  browser1
    Location should be  https://metadeploy.herokuapp.com/products
    Capture page screenshot

    Switch browser  browser2
    Location should be  https://mrbelvedereci.herokuapp.com/
    Capture page screenshot


Default browser size
    [Documentation]  Verify that we automatically resize browser to minimum supported size
    [Teardown]  Close all browsers

    Open test browser
    ${width}  ${height}=  Get window size
    Should be equal as strings  ${width}x${height}  ${DEFAULT WINDOW SIZE}
    ...  Expected window size to be ${DEFAULT WINDOW SIZE} but it was ${width}x${height}

Explicit browser size
    [Documentation]  Verify we can set an explicit browser size when opening the window
    [Teardown]  Close all browsers

    Open test browser           size=1400x1200

    ${width}  ${height}=        Get window size
    Should be equal as strings  ${width}x${height}  1400x1200
    ...  Expected window size to be 1400x1200 but it was ${width}x${height}
