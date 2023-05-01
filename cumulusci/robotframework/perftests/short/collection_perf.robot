*** Settings ***
Documentation   Tests of collections of records based on Jess Lopez's recommendations
...             Note that keywords referenced in Setup are NOT performance measured.
Library         DateTime
Resource        cumulusci/robotframework/Salesforce.robot
# Suite Teardown  Delete Session Records
Force Tags      api200

*** Keywords ***
Insert 200 Contacts
    [Documentation]  Create 200 Contacts in CONTACTS suite variable
    @{objects}=  Generate Test Data  Contact  200  
        ...  FirstName=User {{number}}
        ...  LastName={{fake.last_name}}
    Salesforce Collection Insert  ${objects}
    Set Suite Variable      @{CONTACTS}      @{objects}
    [return]    ${objects}

Create Accounts If Necessary
    [Documentation]  Create 200 Accounts corresponding to CONTACTS suite variable
    ...              and update the contacts to connect to them
    ${idlist} =     Evaluate    ",".join([f"'{contact['id']}'" for contact in $CONTACTS])
    ${query} =      Set Variable   SELECT id FROM Contact WHERE AccountId=null AND id in (${idlist})
    ${query_results} =   SOQL Query    ${query}
    ${contacts_without_accounts} =    Set Variable    ${query_results}[records]
    ${numobjects} =    Get Length     ${contacts_without_accounts}
    ${newobjects} =     Generate Test Data     Account    ${numobjects} 
        ...                                          Name={{fake.name}}

    ${created_records}=     Salesforce Collection Insert  ${newobjects}

    FOR     ${index}  IN RANGE    ${numobjects}
        ${contact} =   Set Variable    ${contacts_without_accounts}[${index}]
        ${account_id} =    Set Variable    ${created_records}[${index}][id]
        Set To Dictionary   ${contact}    'AccountId'     ${account_id}
    END

    Salesforce Collection Update  ${CONTACTS}


Insert 200 Prospecting Opportunities
    [Documentation]  Create 200 Opportunities in OPPORTUNITIES suite variable
    ...             Associate with accounts queried from Salesforce
    ...             These may have been created by ``Create Accounts If Necessary``
    ...             or may have been created automatically by a package like NPSP.
    Create Accounts If Necessary
    @{accounts}=    Salesforce Query    Account

    ${date}=    Get Current Date     result_format=%Y-%m-%d
    @{objects}=  Generate Test Data  Opportunity  200  
        ...  Name=Opp {{number}}
        ...  StageName=Prospecting
        ...  Amount={{1000 + number}}
        ...  CloseDate=${date}
    ${numobjects}=  Get Length     ${objects}
    FOR     ${index}   IN RANGE   ${numobjects}
        ${object}=  Set Variable    ${objects}[${index}]
        ${account}=     Set Variable    ${accounts}[${index}]
        ${account_id}=  Set Variable    ${account}[Id]
        set to dictionary   ${object}   AccountId   ${account_id}
    END

    Salesforce Collection Insert  ${objects}
    Set Suite Variable      @{OPPORTUNITIES}      @{objects}

*** Test Cases ***

Perftest - Insert 200 Contacts
    Start Performance Timer
    Insert 200 Contacts
    Stop Performance Timer

Perftest - Insert 200 Contacts With Addresses
    Start Performance Timer
    @{objects}=  Generate Test Data  Contact  200  
        ...  FirstName={{fake.first_name}}
        ...  LastName={{fake.last_name}}
        ...  MailingStreet={{fake.street_address}}
        ...  MailingCity=New York
        ...  MailingState=NY
        ...  MailingPostalCode=12345
        ...  Email={{fake.email(domain="salesforce.com")}}
    Salesforce Collection Insert  ${objects}
    Stop Performance Timer

Perftest - Insert 200 Prospecting Opportunities
    Start Performance Timer
    [Setup]   Run Keywords
    ...             Insert 200 Contacts
    ...     AND     Create Accounts If Necessary
    Insert 200 Prospecting Opportunities
    Stop Performance Timer

Perftest - Change 200 Opportunity States to Closed-Won
    Start Performance Timer
    [Setup]   Run Keywords
    ...             Insert 200 Contacts
    ...     AND     Create Accounts If Necessary
    ...     AND     Insert 200 Prospecting Opportunities

    FOR     ${record}   IN  @{OPPORTUNITIES}
        Set To Dictionary   ${record}   StageName   Closed Won
    END
    Salesforce Collection Update    ${OPPORTUNITIES}
    Stop Performance Timer
