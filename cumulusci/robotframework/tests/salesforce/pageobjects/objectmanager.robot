*** Settings ***

Resource        cumulusci/robotframework/Salesforce.robot
Library         cumulusci.robotframework.PageObjects
Suite Setup     Run keywords  Open Test Browser
Suite Teardown  Delete Records and Close Browser

*** Keywords ***
Create Custom Field In Object Manager
    [Documentation]
    ...  Reads key value pair arguments.
    ...
    ...  Navigates to Object Manager page and load fields and relationships for the specific object
    ...  Runs keyword to create custom field
    ...
    ...  Example:
    ...
    ...  | Create custom field in object manager
    ...  | ...  Object=Payment
    ...  | ...  Field_Type=Formula
    ...  | ...  Field_Name=Is Opportunity From Prior Year
    ...  | ...  Formula=YEAR( npe01__Opportunity__r.CloseDate ) < YEAR( npe01__Payment_Date__c )

    [Arguments]                                    &{fields}
    Go To Page                                     ObjectManager                           ${fields}[Object]
    Switch Tab To                                  Fields & Relationships
    Create Custom Field                            &{fields}

*** Test Cases ***

Navigate To The Object Manager page For Specified Object
    [Documentation]     Smoke Test For validating the behavior of navigating to the ObjectManager Page for a specified object

    Go To Page                                             ObjectManager                              Contact
    Current page should be                                 ObjectManager                              Contact


Create Custom Lookup Field Using Object Manager
    [Documentation]     To test the ability of creating a custom lookup field using object manager and verify field got created

    Create Custom Field In Object Manager
    ...                                                    Object=Contact
    ...                                                    Field_Type=Lookup
    ...                                                    Field_Name=Last Soft Credit Opportunity
    ...                                                    Related_To=Opportunity
    Go To Page                                             ObjectManager                               Contact
    Switch Tab To                                          Fields & Relationships
    Is Field Present                                       Last Soft Credit Opportunity
    Delete Custom Field                                    Last Soft Credit Opportunity

Create Custom Text Field Using Object Manager
    [Documentation]     To test the ability of creating a custom text field using object manager and verify field got created

    Create Custom Field In Object Manager
    ...                                                    Object=Contact
    ...                                                    Field_Type=Text
    ...                                                    Field_Name=This Is A Text Field
    Go To Page                                             ObjectManager                               Contact
    Switch Tab To                                          Fields & Relationships
    Is Field Present                                       This Is A Text Field
    Delete Custom Field                                    This Is A Text Field


Create Custom Currency Field Using Object Manager
    [Documentation]     To test the ability of creating a custom currency field and verify field got created

    Create Custom Field In Object Manager
    ...                                                    Object=Account
    ...                                                    Field_Type=Currency
    ...                                                    Field_Name=This Year Payments on Past Year Pledges
    Go To Page                                             ObjectManager                               Account
    Switch Tab To                                          Fields & Relationships
    Is Field Present                                       This Year Payments on Past Year Pledges
    Delete Custom Field                                    This Year Payments on Past Year Pledges
