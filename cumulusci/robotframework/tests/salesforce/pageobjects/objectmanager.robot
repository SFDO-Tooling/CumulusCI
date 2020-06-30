*** Settings ***

Resource        cumulusci/robotframework/Salesforce.robot
Library         cumulusci.robotframework.PageObjects
...  ${CURDIR}/ObjectManagerPageObject.py


Suite Setup     Run keywords  Open Test Browser
Suite Teardown  Delete Records and Close Browser

*** Keywords ***
Create Customfield In Object Manager
    [Documentation]        Reads key value pair arguments.
    ...                    Navigates to Object Manager page and load fields and relationships for the specific object
    ...                    Runs keyword to create custom field
    ...                    Example key,value pairs
    ...                            Object=Payment
    ...                            Field_Type=Formula
    ...                            Field_Name=Is Opportunity From Prior Year
    ...                            Formula=YEAR( npe01__Opportunity__r.CloseDate ) < YEAR( npe01__Payment_Date__c )
    [Arguments]            &{fields}
    Load Page Object                                     Custom                           ObjectManager
    Open Fields And Relationships                        &{fields}[Object]
    Create Custom Field                                  &{fields}

*** Test Cases ***

Create Custom Lookup Field Using Object Manager
    [Documentation]     To test the ability of creating a custom lookup field

    Create Customfield In Object Manager
    ...                                                    Object=Contact
    ...                                                    Field_Type=Lookup
    ...                                                    Field_Name=Last Soft Credit Opportunity
    ...                                                    Related_To=Opportunity

