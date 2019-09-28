*** Settings ***

Resource       cumulusci/robotframework/Salesforce.robot
Resource  cumulusci/robotframework/CumulusCI.robot

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

Test Run Task Class
    Run Task Class   cumulusci.tasks.bulkdata.delete.DeleteData
    ...         objects=Account
    ...         where=BillingStreet='Baker St.'
    Run Task Class   cumulusci.tasks.bulkdata.delete.DeleteData
    ...         objects=Contact
    ...         where=MailingStreet='Baker St.'
    Run Task Class   tasks.generate_and_load_data.GenerateAndLoadData
    ...     num_records=20
    ...     mapping=cumulusci/tasks/bulkdata/tests/mapping_vanilla_sf.yml
    ...     data_generation_task=cumulusci.tasks.bulkdata.tests.dummy_data_factory.GenerateDummyData
    Assert Row Count  20  Account   BillingStreet=Baker St.
    Assert Row Count  15  Contact  MailingStreet=Baker St.