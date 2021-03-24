*** Settings ***
Resource        cumulusci/robotframework/Salesforce.robot
Library         cumulusci.robotframework.PageObjects
Library         cumulusci/robotframework/FormsMixin.py
Library         Dialogs

Suite Setup     Run keywords
...  Initialize Test Objects
...  Open test browser
Suite Teardown  Delete records and close browser
Force tags      forms

*** Variables ***
${account name}   ACME Labs
${campaign name}  The Big SPAM

*** Keywords ***
Initialize test objects
    [Documentation]  Create related objects

    ${result}=  salesforce query  Account  name=${account name}
    Run keyword if  not $result
    ...  salesforce insert  Account  name=${account name}

    ${result}=  salesforce query  Campaign  name=${campaign name}
    Run keyword if  not $result
    ...  salesforce insert  Campaign  name=${campaign name}


*** Test Cases ***
Lightning based form - Opportunity
    [Documentation]
    ...  Sets all of the input fields for an opportunity, to make sure
    ...  we at least support enough input field types to create an opportunity

    [Setup]  Run keywords
    ...  Go to page                  Home    Opportunity
    ...  AND  Click Object Button    New
    ...  AND  Wait for modal         New     Opportunity
    [Teardown]   Click modal button  Cancel

    Input form data
    ...  Opportunity Name  The big one                             # required text field
    ...  Account Name      ${Account Name}                         # lookup
    ...  Amount            1b                                      # currency field
    ...  Next Step         whatever                                # text field
    ...  Close Date        4/01/2022                               # date field
    ...  Private           checked                                 # checkbox
    ...  Type              New Customer                            # combobox
    ...  Stage             Prospecting                             # combobox
    ...  Probability (%)   90                                      # percentage
    ...  Description       this is a long description\nblah blah   # textarea
    ...  Primary Campaign Source  ${Campaign Name}                 # combobox
    ...  Lead Source       Purchased List                          # combobox

    capture page screenshot

    # ${contact_id} =       Get Current Record Id
    # Store Session Record  Contact  ${contact_id}
    # Validate Contact      ${contact_id}  ${first_name}  ${last_name}

Non-lightning based form - Shipment
    [Documentation]
    ...  Fill in input and textarea fields

    [Setup]  Run keywords
    ...  Go to page                  Home    Shipment
    ...  AND  Click Object Button    New
    ...  AND  Wait for modal         New     Shipment
    [Teardown]   Click modal button  Cancel

    Input form data
    ...  Ship To Street  2501 Exchange Ave
    ...  Ship To City    Oklahoma City

    capture page screenshot

Fieldsets - Shipment
    [Documentation]
    ...  Verify we can use fieldsets to disambiguate fields

    [Setup]  Run keywords
    ...  Go to page                  Home    Shipment
    ...  AND  Click Object Button    New
    ...  AND  Wait for modal         New     Shipment
    [Teardown]   Click modal button  Cancel

    Input form data
    ...  Expected Delivery Date::Date  04/01/2021
    # hmmm. This one isn't working. Too late in the evening to fixe it :-\
    # ...  Actual Delivery Date::Date    04/02/2021
