*** Settings ***

Library        Collections
Library        String
Library        SeleniumLibrary  implicit_wait=${IMPLICIT_WAIT}  timeout=${TIMEOUT}
Library        cumulusci.robotframework.CumulusCI  ${ORG}
Library        cumulusci.robotframework.Salesforce  debug=${DEBUG}
Suite Setup    Set Login Url

*** Variables *** 
${BROWSER}  chrome
${DEBUG}  ${false}
${IMPLICIT_WAIT}  10.0
${TIMEOUT}  10.0

*** Keywords ***

Open Test Browser
    Open Browser  ${LOGIN_URL}  ${BROWSER}
    #Run Keyword If  '${BROWSER}' == 'chrome'  Open Test Browser Chrome
    #...    ELSE IF  '${BROWSER}' == 'firefox'  Open Test Browser Firefox
    #Go To  ${LOGIN_URL}

Open Test Browser Chrome
    ${chrome_options} =  Evaluate  sys.modules['selenium.webdriver'].ChromeOptions()  sys
    Call Method  ${chrome_options}  add_argument  --disable-notifications
    Create Webdriver  Chrome  timeout=${IMPLICIT_WAIT}  chrome_options=${chrome_options}

Open Test Browser Firefox
    Create Webdriver  Firefox

Create Random Contact
    ${first_name} =  Generate Random String
    ${last_name} =  Generate Random String
    ${contact_id} =  Salesforce Insert  Contact  FirstName=${first_name}  LastName=${last_name}
    Set Test Variable  ${first_name}  ${first_name}
    Set Test Variable  ${last_name}  ${last_name}
    Set Test Variable  ${contact_id}  ${contact_id}

*** Test Cases ***

Test Log In
    Open Test Browser
    Page Should Contain  Home
    [Teardown]  Close Browser

Test SOQL Query
    Create Random Contact
    &{result} =  Soql Query  Select Id, FirstName, LastName from Contact WHERE Id = '${contact_id}'
    @{records} =  Get From Dictionary  ${result}  records
    Log Variables
    &{contact} =  Get From List  ${records}  0
    Should Be Equal  &{result}[totalSize]  ${1}
    Should Be Equal  &{contact}[FirstName]  ${first_name}
    Should Be Equal  &{contact}[LastName]  ${last_name}
    [Teardown]  Salesforce Delete  Contact  ${contact_id}

Test Salesforce Delete
    Log Variables
    Create Random Contact
    Salesforce Delete  Contact  ${contact_id}
    &{result} =  SOQL Query  Select Id from Contact WHERE Id = '${contact_id}'
    Should Be Equal  &{result}[totalSize]  ${0}

Test Salesforce Insert
    Create Random Contact
    &{contact} =  Salesforce Get  Contact  ${contact_id}
    Should Be Equal  &{contact}[FirstName]  ${first_name}
    Should Be Equal  &{contact}[LastName]  ${last_name}
    [Teardown]  Salesforce Delete  Contact  ${contact_id}
    
Test Salesforce Update
    Create Random Contact
    ${new_last_name} =  Generate Random String
    Salesforce Update  Contact  ${contact_id}  FirstName=${first_name}  LastName=${new_last_name}
    &{contact} =  Salesforce Get  Contact  ${contact_id}
    Should Be Equal  &{contact}[FirstName]  ${first_name}
    Should Be Equal  &{contact}[LastName]  ${new_last_name}
    [Teardown]  Salesforce Delete  Contact  ${contact_id}
