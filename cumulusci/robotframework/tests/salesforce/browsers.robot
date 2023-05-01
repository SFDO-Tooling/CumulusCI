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
    Open test browser  alias=browser2
    Assert active browser count  2

Browser aliases
    [Documentation]  Verify that aliases are properly handled in Open Test Browser
    [Tags]  issue:1068
    [Teardown]  Close all browsers

    # Open the default browser, go to a specific page and
    # save the location
    Open test browser  alias=browser1
    Go to setup home
    ${browser1 location}=  get location

    # open a second browser to a different specific page
    Open test browser  alias=browser2
    Go to  about:blank

    # Switch back to the first to verify that the location
    # hasn't changed
    Switch browser  browser1
    Location should be  ${browser1 location}

    # Go to a new location in the first browser,
    Go to setup object manager

    # ... and then verify the location of the second
    # browser hasn't changed.
    Switch browser  browser2
    Location should be  about:blank


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

    Reset test listener message log
    Set test variable  ${BROWSER}  headlesschrome
    Open test browser  alias=chrome
    Assert robot log   selenium browser capabilities:  INFO
    Assert robot log   browserName.*chrome

    # Make sure we don't just log the capabilities of the
    # first browser that was opened
    Reset test listener message log
    Set test variable  ${BROWSER}  headlessfirefox
    Open test browser  alias=firefox
    Assert robot log   selenium browser capabilities:  INFO
    Assert robot log   browserName.*firefox


Initializing selenium speed via global variable
    [Documentation]
    ...  Verify that the `Set Selenium Speed` is called when Open Test browser is called
    [Setup]     Close all browsers
    [Teardown]  Close all browsers

    # First, verify that this variable has been initialized
    # The default value is set in Salesforce.robot.
    Variable should exist  ${SELENIUM_SPEED}

    Open test browser
    Assert keyword status  PASS  SeleniumLibrary.Set Selenium Speed  \${SELENIUM_SPEED}

Select Window calls Switch Window
    [Documentation]  Verify that 'Select Window' calls 'Switch Window'
    ...              and also that it logs a deprecation warning
    [Setup]          Run keywords
    ...  Open test browser
    ...  AND  go to setup home
    ...  AND  execute javascript  window.open("about:blank", "window1")
    [Teardown]       Close all browsers


    Reset test listener message log
    Select Window       window1
    Assert robot log    'Select Window' is deprecated; use 'Switch Window' instead  WARN
    location should be  about:blank

    Reset test listener message log
    Select Window       # defaults to the original window
    Assert robot log    'Select Window' is deprecated; use 'Switch Window' instead  WARN
    # let's make sure we actually are at the main window's location
    Wait until location contains  /lightning/setup/SetupOneHome/home
