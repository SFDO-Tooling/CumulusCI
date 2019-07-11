*** Settings ***
Documentation   Tests of collections of records based on Jess Lopez's work here: 
...             https://salesforce.quip.com/dsUXAOxiKz28  (Salesforce Internal)
...             Note that keywords referenced in Setup are NOT performance measure.
Library         DateTime
Resource        cumulusci/robotframework/Salesforce.robot
# Suite Teardown  Delete Session Records
Force Tags      api200

*** Keywords ***
Insert 200 Contacts
    [Documentation]  Create 200 Contacts in CONTACTS suite variable
    @{objects}=  Salesforce Init Objects  Contact  200  
        ...  FirstName="User {number}"
        ...  LastName="{random_str}"
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
    ${newobjects} =     Create List
    FOR     ${index}  IN RANGE    ${numobjects}
        ${account_name} =     Generate Random String
        ${new_account}=   Salesforce Init Object     Account   
        ...                                          Name=${account_name}
        Append to list      ${newobjects}       ${new_account}
    END

    ${created_records}=     Salesforce Collection Insert  ${newobjects}

    FOR     ${index}  IN RANGE    ${numobjects}

        ${contact} =   Set Variable    ${contacts_without_accounts}[${index}]
        ${account_id} =    Set Variable    ${created_records}[${index}][id]
        Set To Dictionary   ${contact}    'AccountId'     ${account_id}
    END

    Salesforce Collection Update  ${CONTACTS}


Insert 200 Pledged Opportunities
    [Documentation]  Create 200 Opportunities in OPPORTUNITIES suite variable
    ...             Associate with accounts queried from Salesforce
    ...             These may have been created by ``Create Accounts If Necessary``
    ...             or may have been created automatically by a package like NPSP.
    Create Accounts If Necessary
    @{accounts}=    Salesforce Query    Account

    ${date}=    Get Current Date     result_format=%Y-%m-%d
    @{objects}=  Salesforce Init Objects  Opportunity  200  
        ...  Name= Opp {number}
        ...  StageName= Pledged
        ...  Amount= {int}
        ...  CloseDate=${date}
    ${numobjects}=  Get Length     ${objects}
    FOR     ${index}   IN RANGE   ${numobjects}
        ${object}=  Set Variable    @{objects}[${index}]
        ${account}=     Set Variable    @{accounts}[${index}]
        ${account_id}=  Set Variable    ${account}[Id]
        set to dictionary   ${object}   AccountId   ${account_id}
    END

    Salesforce Collection Insert  ${objects}
    Set Suite Variable      @{OPPORTUNITIES}      @{objects}

*** Test Cases ***

Perftest - Insert 200 Contacts
    Insert 200 Contacts

Perftest - Insert 200 Contacts With Addresses
    @{objects}=  Salesforce Init Objects  Contact  200  
        ...  FirstName="User {number}"
        ...  LastName="{random_str}"
        ...  MailingStreet="{number} Main Street"
        ...  MailingCity='New York'
        ...  MailingState='NY',
        ...  MailingPostalCode='12345'
    Salesforce Collection Insert  ${objects}

Perftest - Insert 200 Pledged Opportunities
    [Setup]   Run Keywords
    ...             Insert 200 Contacts
    ...     AND     Create Accounts If Necessary
    Insert 200 Pledged Opportunities

Perftest - Change 200 Opportunity States to Closed-Won
    [Setup]   Run Keywords
    ...             Insert 200 Contacts
    ...     AND     Create Accounts If Necessary
    ...     AND     Insert 200 Pledged Opportunities

    FOR     ${record}   IN  @{OPPORTUNITIES}
        Set To Dictionary   ${record}   StageName   Closed Won
    END
    Salesforce Collection Update    ${OPPORTUNITIES}
