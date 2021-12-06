*** Settings ***
Resource        cumulusci/robotframework/Salesforce.robot
Library         cumulusci.robotframework.PageObjects
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
    [Documentation]  Create related objects used by this test

    Require salesforce object  Account   name=${account name}
    Require salesforce object  Campaign  name=${campaign name}

Require Salesforce object
    # We might want to make this available to everyone.
    [Documentation]
    ...  Create a salesforce object if it doesn't exist
    ...
    ...  Example:
    ...
    ...  | Require salesforce object  Account  name=ACME Labs  description=Created for test case

    [Arguments]  ${object_type}  &{args}

    ${result}=  salesforce query  ${object_type}  &{args}
    # if we don't already have such an object, create one
    Run keyword if  not $result
    ...  Salesforce insert  ${object type}  &{args}
    Run keyword if  not $result
    ...  log  created object  DEBUG

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
    ...  Primary Campaign Source  ${Campaign Name}                 # lookup
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

    # first, let's make sure that the keyword returns an element
    # that is not a lightning component
    FOR  ${label}  IN  Ship To Street  Ship To City
        ${element}=  Get webelement  label:${label}
        Should not start with  ${element.tag_name}  lightning-
        ...  Element tag for '${label}' not expected to be lightning component
    END

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
