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

Test Perf Set Elapsed Time
    [Tags]  perf
    Set Test Elapsed Time       11655.9   #  3:14:15.9

Test Perf Set Elapsed Time String
    [Tags]  perf
    Log                 A
    Set Test Elapsed Time       5 hours   #  5:00:00

Test Perf Measure Elapsed
    [Setup]       Log             Before
    [Teardown]    Log             After
    Log                 B
    Start Perf Timer
    Sleep       1
    Log         Noop
    End Perf Timer

# Make sure parser doesn't choke on this.
Test Perf - Parser does not choke with no keywords - Should Fail
    [Tags]      noncritical

Test Perf Measure Other Metric
    Set Test Metric    Max_CPU_Percent    30

Mismatched End Perf Timer - Should Fail
    Run Keyword and Expect Error
    ...         *Elapsed time clock was not*
    ...         End Perf Timer

Test Elapsed Time For Last Record
    # This test uses contacts as if they were "jobs" becaues they are
    # easy to insert. I don't currently have a better alternative 
    # for a job-like objects which is easy to create in a vanilla
    # SF org
    ${contact_id} =  Salesforce Insert  Contact  FirstName=Dummy1  LastName=Dummy2
    sleep   1
    Salesforce Update   Contact     ${contact_id}       LastName=Dummy3
    ${Elapsed}=     Elapsed Time For Last Record    
    ...             obj_name=Contact
    ...             where=Id='${contact_id}'
    ...             start_field=CreatedDate
    ...             end_field=LastModifiedDate
    ...             order_by=LastModifiedDate
    Should Be True      ${Elapsed} > 0

    ${contact2_id} =  Salesforce Insert  Contact  FirstName=Dummy1  LastName=Dummy2
    Salesforce Update   Contact     ${contact_id}       LastName=Dummy3
    ${Elapsed_2}=     Elapsed Time For Last Record    
    ...             obj_name=Contact
    ...             where=Id='${contact_id}'
    ...             start_field=CreatedDate
    ...             end_field=LastModifiedDate
    ...             order_by=LastModifiedDate

    ${Elapsed_latest}=     Elapsed Time For Last Record    
    ...             obj_name=Contact
    ...             start_field=CreatedDate
    ...             end_field=LastModifiedDate
    ...             order_by=LastModifiedDate

    Should Be Equal         ${Elapsed_2}    ${Elapsed_latest}
    Set Test Elapsed Time        ${Elapsed}


Test Elapsed Time For Last Record - Failure
    Run Keyword and expect Error   *Matching record not found*   
    ...     Elapsed Time For Last Record    
    ...             obj_name=AsyncApexJob
    ...             where=ApexClass.Name='BlahBlah'
    ...             start_field=CreatedDate
    ...             end_field=CompletedDate
    ...             order_by=CompletedDate
