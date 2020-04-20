*** Settings ***

Resource       cumulusci/robotframework/Salesforce.robot
Resource  cumulusci/robotframework/CumulusCI.robot

Force Tags    bulkdata  no-browser

*** Test Cases ***

Test Run Bulk Data Deletion With Error

    ${account_name} =  Get fake data  company
    ${account_id} =  Salesforce Insert  Account
    ...  Name=${account_name}
    ...  BillingStreet=Granville Ave., SFDO

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
    ...         where=BillingStreet='Granville Ave., SFDO'

    Salesforce Delete   Contract     ${contract_id}

    Run Task Class   cumulusci.tasks.bulkdata.delete.DeleteData
    ...         objects=Account
    ...         where=BillingStreet='Granville Ave., SFDO'