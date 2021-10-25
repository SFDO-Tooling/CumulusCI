*** Settings ***
Resource        cumulusci/robotframework/Salesforce.robot
Suite Setup     Open test browser
Suite Teardown  Close All Browsers
Library  Dialogs

*** Tasks ***

Click refresh components

    Go to org URL   /udd/AllPackage/viewAllPackage.apexp

    If we are on the bad references page
    ...  click recompile all

    Page should be package detail page

    Wait until element is enabled  Refresh Components
    Click button  Refresh Components

    Wait Until Keyword Succeeds
    ...  10x  1 second
    ...  Refresh Components button is disabled

    log  Success!


*** Keywords ***

Go to org URL
    [Arguments]  ${path}
    [Documentation]
    ...  Prefix the org instance url the URL fragment, and go to that page.

    ${org_info}=   Get org info
    Go to  ${org_info['instance_url']}${path}

Page should be package detail page
    ${status}=  Run keyword and return status
    ...  Page should contain  Notify on Apex Error
    return from keyword if  $status

    Capture page screenshot
    Fail  It doesn't appear that we are on the package detail page

If we are on the bad references page
    [Arguments]  ${keyword}
    ${status}=   Run Keyword And Return Status
    ...  Location should contain  badExternalRefs.apexp
    Return from keyword if  not $status

    # We are on the badExternalRefs page, so try to run the given keyword
    Run keyword  ${keyword}

Click recompile all
    Click button  Recompile All

Refresh Components button is disabled
    Element should be disabled  Refresh Components
