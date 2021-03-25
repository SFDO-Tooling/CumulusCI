** Settings ***

Resource        cumulusci/robotframework/Salesforce.robot
Library         cumulusci.robotframework.PageObjects
Library         DateTime
Suite Setup     Run keyword  Open Test Browser
Suite Teardown  Delete Records and Close Browser

*** Keywords ***

Create Opportunity
    [Arguments]
    ${date} =        Get Current Date  result_format=%Y-%m-%d
    ${account_id} =  Salesforce Insert  Account
    ...  Name=Celebration
    ${opp_id} =      Salesforce Insert  Opportunity
    ...  Name=Celebration
    ...  AccountId=${account_id}
    ...  StageName=Prospecting
    ...  CloseDate=${date}
    [return]  ${opp_id}

Celebrate
    Click Element  text=Closed
    Click Element  text=Change Closed Stage
    Click Element  text=Save
    Debug

*** Test Cases ***

Celebrate
    ${opp_id} =             Create Opportunity
    Go To Record Home       ${opp_id}
    Celebrate
