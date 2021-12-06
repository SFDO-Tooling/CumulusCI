*** Settings ***

Resource  cumulusci/robotframework/CumulusCI.robot
Force Tags  no-browser

*** Test Cases ***

Test Set Login Url 
    Set Login Url
    Variable Should Exist  ${LOGIN_URL}

Test Login Url
    ${login_url} =  Login Url
    Should Contain  ${login_url}  secur/frontdoor.jsp?sid=

Test Get Org Info
    &{org_info} =  Get Org Info
    Dictionary Should Contain Key  ${org_info}  org_id
    Dictionary Should Contain Key  ${org_info}  username

Test Get Namespace Prefix
    ${ns} =  Get Namespace Prefix
    Should Be Empty  ${ns}

Test Run Task
    Run Task  create_package

Test Run Task With Options
    Run Task  create_package  package=Test Package

Test Run Task Missing
    Run Keyword And Expect Error
    ...  TaskNotFoundError: Task not found: does_not_exist
    ...  Run Task  does_not_exist

Test Run Task Class
    Run Task Class  cumulusci.tasks.salesforce.CreatePackage

Test Run Task Class With Options
    Run Task Class  cumulusci.tasks.salesforce.CreatePackage  package=Test Package
