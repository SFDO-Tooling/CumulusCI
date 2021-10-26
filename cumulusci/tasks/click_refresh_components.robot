*** Settings ***
Resource        cumulusci/robotframework/Salesforce.robot
Suite Setup     Open test browser
Suite Teardown  Close All Browsers
Library  Dialogs

*** Tasks ***

Click refresh components

    ${allPackageId}=  Get APID
    Go to org URL   /${allPackageId}?tab=PackageComponents

    If we are on the bad references page
    ...  click recompile all

    Page should be package detail page

    If the refresh components button is available
    ...  click refresh components

    log  Success!


*** Keywords ***

Get APID
    ${result}=  SOQL Query
    ...  SELECT NamespacePrefix FROM Organization
    ${organization}=  Get from list  ${result['records']}  0
    ${namespace}=  Get from dictionary  ${organization}  NamespacePrefix
    ${packages}=  SOQL Query
    ...  SELECT Id FROM MetadataPackage WHERE NamespacePrefix = '${namespace}'
    ${package}=  Get from list  ${packages['records']}  0
    [return]  ${package['Id']}

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

If the refresh components button is available
    [Arguments]  ${keyword}
    ${status}=   Run Keyword And Return Status
    ...  Page should contain element  ViewAllPackage:theForm:mainDetailBlock:refreshComponentListButton
    Return from keyword if  not $status

    # There exists a Refresh Components button, so click it.
    Run keyword  ${keyword}


Click recompile all
    Click button  Recompile All

Click refresh components
    Wait until element is enabled  ViewAllPackage:theForm:mainDetailBlock:refreshComponentListButton
    Click button  ViewAllPackage:theForm:mainDetailBlock:refreshComponentListButton

    Wait Until Keyword Succeeds
    ...  20x  1 second
    ...  Refresh Components button is disabled


Refresh Components button is disabled
    Element should be disabled  ViewAllPackage:theForm:mainDetailBlock:refreshComponentListButton
