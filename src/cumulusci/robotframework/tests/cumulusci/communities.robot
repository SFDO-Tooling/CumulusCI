*** Settings ***
Resource  cumulusci/robotframework/CumulusCI.robot
Library   Collections
Force Tags  no-browser

Suite Setup  run keywords
     # Note: the first community name intentionally includes a unicode
     # character to make sure we can handle it.
...  Ensure community exists       Kōkua   kokua
...  AND  Ensure community exists  Ohana   ohana

*** Keywords ***
Ensure community exists
    [Arguments]      ${community name}  ${url prefix}
    [Documentation]  Creates a community with the given name if it doesn't exist

    ${passed}=  run keyword and return status
    ...  get community info  ${community name}

    run keyword if  not $passed  run task  create_community
    ...  template=VF Template
    ...  name=${community name}
    ...  url_path_prefix=${url prefix}

*** Test Cases ***
Get community info for specific community
    # we'll just spot-check a few keys. I don't see a point
    # in testing them all, since the API is either going to
    # return everything or nothing
    ${info}=  get community info               Kōkua
    Dictionary should contain key  ${info}     name
    Dictionary should contain key  ${info}     loginUrl
    Dictionary should contain key  ${info}     siteUrl
    Should be equal  ${info['name']}           Kōkua
    Should be equal  ${info['urlPathPrefix']}  kokua

    # now get info for another community, to make sure
    # it doesn't return the data from the previous community
    ${info}=  get community info  Ohana
    Should be equal  ${info['name']}  Ohana
    Should be equal  ${info['urlPathPrefix']}  ohana

Get community info for non-existing community throws error
    [Documentation]  Verify that an unknown community name throws a reasonable error message
    run keyword and expect error
    ...  Unable to find community information for 'bōgusCommunity'
    ...  get community info  bōgusCommunity

Get community info with key
    [Documentation]  Verify we can Fetch data for a single key
    ${loginUrl}=  get community info  Kōkua  loginUrl
    Should match regexp  ${loginUrl}  https://.*/kokua/login

Get community info with unknown key throws error
    [Documentation]  Verify that an unknown key throws a reasonable error message
    run keyword and expect error  Invalid key 'bōgus'
    ...  get community info  Kōkua  bōgus
