*** Settings ***

Resource       cumulusci/robotframework/Salesforce.robot
Resource  cumulusci/robotframework/CumulusCI.robot

Force Tags    bulkdata

*** Keywords ***
Assert Row Count
    [Arguments]     ${count}        ${object_name}      &{kwargs}

    ${status}     ${result} =   Run Keyword And Ignore Error
    ...           Salesforce Query  ${object_name}  
    ...           select=COUNT(Id)
    ...           &{kwargs}

    Run Keyword If      '${status}' != 'PASS'
    ...           Log    
    ...           Salesforce query failed: probably timeout. ${object_name} ${result}
    ...           console=True

    Should Be Equal    PASS    ${status}

    ${matching_records} =   Set Variable    ${result}[0][expr0]
    Should Be Equal As Numbers        ${matching_records}     ${count}

*** Test Cases ***

Test Run Bulk Data Deletion With Error

    ${account_name} =  Generate Random String
    ${account_id} =  Salesforce Insert  Account
    ...  Name=${account_name}
    ...  BillingStreet=Baker St.

    ${contract_id} =    Salesforce Insert  Contract
    ...  AccountId=${account_id}

    Salesforce Update    Contract    ${contract_id}
    ...     status=Activated

    ${opportunity} =    Salesforce Insert   Opportunity
    ...  AccountId=${account_id}
    ...  StageName=Prospecting
    ...  Name=${account_name}
    ...  CloseDate=2025-05-05

    Run Keyword and Expect Error        *BulkDataException*
    ...     Run Task Class   cumulusci.tasks.bulkdata.delete.DeleteData
    ...         objects=Account
    ...         where=BillingStreet='Baker St.'

