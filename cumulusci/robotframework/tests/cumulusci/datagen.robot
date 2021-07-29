*** Settings ***

Resource       cumulusci/robotframework/Salesforce.robot
Resource  cumulusci/robotframework/CumulusCI.robot

Force Tags    bulkdata  no-browser

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

Attempt To Load Snowfakery
    Import Library      snowfakery
    Return From Keyword     True


*** Test Cases ***

Test Run Bulk Data Generation
    Run Task Class   cumulusci.tasks.bulkdata.delete.DeleteData
    ...         objects=Account
    ...         where=BillingStreet='Baker St.'
    Run Task Class   cumulusci.tasks.bulkdata.delete.DeleteData
    ...         objects=Contact
    ...         where=MailingStreet='Baker St.'
    Run Task Class   cumulusci.tasks.bulkdata.generate_and_load_data.GenerateAndLoadData
    ...     num_records=20
    ...     mapping=cumulusci/tasks/bulkdata/tests/mapping_vanilla_sf.yml
    ...     data_generation_task=cumulusci.tasks.bulkdata.tests.dummy_data_factory.GenerateDummyData
    Assert Row Count  20  Account   BillingStreet=Baker St.
    Assert Row Count  15  Contact  MailingStreet=Baker St.

Test Batching
    Run Task Class   cumulusci.tasks.bulkdata.delete.DeleteData
    ...         objects=Account
    ...         where=BillingStreet='Baker St.'
    Run Task Class   cumulusci.tasks.bulkdata.delete.DeleteData
    ...         objects=Contact
    ...         where=MailingStreet='Baker St.'
    Run Task Class   cumulusci.tasks.bulkdata.generate_and_load_data.GenerateAndLoadData
    ...     num_records=20
    ...     mapping=cumulusci/tasks/bulkdata/tests/mapping_vanilla_sf.yml
    ...     batch_size=4
    ...     data_generation_task=cumulusci.tasks.bulkdata.tests.dummy_data_factory.GenerateDummyData
    Assert Row Count  20  Account   BillingStreet=Baker St.
    Assert Row Count  15  Contact  MailingStreet=Baker St.

Test Error Handling
    Run Keyword and Expect Error    STARTS:TaskOptionsError
    ...  Run Task Class   cumulusci.tasks.bulkdata.generate_and_load_data.GenerateAndLoadData
    ...     num_records=20
    ...     mapping=cumulusci/tasks/bulkdata/tests/mapping_vanilla_sf.yml
    ...     batch_size=5
    ...     database_url=sqlite:////tmp/foo.db



Test Snowfakery
    ${status}        ${retVal}=     Run Keyword And Ignore Error          Attempt To Load Snowfakery
    Log     ${status}

    Run Keyword Unless	    $status == 'PASS'       Log     Snowfakery is not available

    Run Keyword If	    $status == 'PASS'       Run Task Class
    ...     cumulusci.tasks.bulkdata.generate_and_load_data_from_yaml.GenerateAndLoadDataFromYaml
    ...     num_records=20
    ...     num_records_tablename=Account
    ...     batch_size=5
    ...     generator_yaml=cumulusci/tasks/bulkdata/tests/snowfakery/simple_snowfakery.recipe.yml
