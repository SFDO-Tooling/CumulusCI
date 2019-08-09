*** Settings ***

Resource        cumulusci/robotframework/Salesforce.robot
Library         TestListener.py
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

Assert window size
    [Documentation]
    ...  Verify the actual window size is the expected size
    ...  give or take a pixel or five.
    [Arguments]  ${expected width}  ${expected height}

    # On circleci, the browser size is sometimes off by a pixel. How rude!
    # Since we don't so much care about the precise size as we do that
    # we are able to change the size, we'll allow a tiny bit of wiggle room.
    ${actual width}  ${actual height}=  Get window size
    ${xdelta}=  evaluate  abs(int($actual_width)-int($expected_width))
    ${ydelta}=  evaluate  abs(int($actual_height)-int($expected_height))
    Run keyword if  $xdelta > 5 or $ydelta > 5
    ...  Fail  Window size of ${actual width}x${actual height} is not close enough to expected ${expected width}x${expected height}

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
    ...  AND  Open test browser  alias=browser2
    ...  AND  Go to  about:blank
    [Teardown]  Close all browsers

    # This also doubles as a test which verifies the default
    # landing page is the Setup home page
    Switch browser  browser1
    Location should contain  /lightning/setup/SetupOneHome/home
    Capture page screenshot

    Switch browser  browser2
    Location should be  about:blank
    Capture page screenshot


Default browser size
    [Documentation]  Verify that we automatically resize browser to minimum supported size
    [Teardown]  Close all browsers

    Open test browser
    Assert window size  1280  1024

Explicit browser size
    [Documentation]  Verify we can set an explicit browser size when opening the window
    [Teardown]  Close all browsers

    Open test browser           size=1400x1200
    Assert window size  1400  1200

Open Test Browser calls Log Browser Capabilities
    [Documentation]
    ...  Verify that browser capabilities are logged when we call
    ...  Open Test Browser
    [Teardown]  Close all browsers

    Reset robot log cache
    Set test variable  ${BROWSER}  headlesschrome
    Open test browser  alias=chrome
    Assert robot log   selenium browser capabilities:  INFO
    Assert robot log   browserName.*chrome

    # Make sure we don't just log the capabilities of the
    # first browser that was opened
    Reset robot log cache
    Set test variable  ${BROWSER}  headlessfirefox
    Open test browser  alias=firefox
    Assert robot log   selenium browser capabilities:  INFO
    Assert robot log   browserName.*firefox
