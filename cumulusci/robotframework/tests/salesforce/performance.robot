*** Settings ***

Resource        cumulusci/robotframework/Salesforce.robot
Library         cumulusci.robotframework.Performance
Test Teardown   Delete Session Records
Force Tags      api  no-browser

*** Test Cases ***

Test Elapsed Time For Last Record
    # This test uses contacts as if they were "jobs" because they are
    # easy to insert. I don't currently have a better alternative
    # for a job-like objects which is easy to create in a vanilla
    # SF org. The underlying keyword only cares that it has two
    # datetime fields.

    ${contact_id} =  Salesforce Insert  Contact
    ...         FirstName=Dummy1
    ...         LastName=Dummy2
    ...         EmailBouncedDate=2030-01-01T00:00:00

    ${Elapsed}=     Elapsed Time For Last Record
    ...             obj_name=Contact
    ...             where=Id='${contact_id}'
    ...             start_field=CreatedDate
    ...             end_field=EmailBouncedDate
    ...             order_by=EmailBouncedDate
    Should Be True      ${Elapsed} >= 100_000

    # This is an "earlier" record than the other
    ${contact2_id} =  Salesforce Insert  Contact
    ...         FirstName=Dummy1
    ...         LastName=Dummy2
    ...         EmailBouncedDate=2029-01-01T00:00:00

    ${Elapsed_latest}=     Elapsed Time For Last Record
    ...             obj_name=Contact
    ...             start_field=CreatedDate
    ...             end_field=EmailBouncedDate
    ...             order_by=EmailBouncedDate

    # The "latest" record should be the original
    Should Be Equal         ${Elapsed}    ${Elapsed_latest}
    Set Test Elapsed Time        ${Elapsed}


Test Elapsed Time For Last Record - Failure No Record
    Run Keyword and expect Error   *Matching record not found*
    ...     Elapsed Time For Last Record
    ...             obj_name=AsyncApexJob
    ...             where=ApexClass.Name='BlahBlah'
    ...             start_field=CreatedDate
    ...             end_field=CompletedDate
    ...             order_by=CompletedDate

Test Elapsed Time For Last Record - Failure Bad Fields
    ${contact_id} =  Salesforce Insert  Contact
    ...         LastName=Dummy2
    ...         EmailBouncedDate=2030-01-01T00:00:00
    Run Keyword and Expect Error   *Date parse error*
    ...     Elapsed Time For Last Record
    ...             obj_name=Contact
    ...             start_field=EmailBouncedDate
    ...             end_field=LastName
    ...             order_by=LastName

    Run Keyword and Expect Error   *Date parse error*
    ...     Elapsed Time For Last Record
    ...             obj_name=Contact
    ...             start_field=EmailBouncedDate
    ...             end_field=FirstName     # None/NULL
    ...             order_by=FirstName      # None/NULL

Test Perf Set Elapsed Time
    [Tags]  perf
    Set Test Elapsed Time       11655.9   #  3:14:15.9

Test Perf Set Elapsed Time Twice
    [Tags]  perf
    Set Test Elapsed Time       11655.9
    Set Test Elapsed Time       53

Test Perf Set Elapsed Time String
    [Tags]  perf
    Log                 A
    Set Test Elapsed Time       5 hours   #  5:00:00

Test Perf Measure Elapsed
    [Setup]       Log             Before
    [Teardown]    Log             After
    Log                 B
    Start Performance Timer
    Sleep       1
    Log         Noop
    Stop Performance Timer

Set Time and Also Metric
    Start Performance Timer
    Log         Noop
    Stop Performance Timer
    Set Test Metric   number of records  100

Test Perf Measure Other Metric
    Set Test Metric    Max_CPU_Percent    30

Mismatched Stop Performance Timer
    Run Keyword and Expect Error
    ...         *Elapsed time clock was not*
    ...         Stop Performance Timer
