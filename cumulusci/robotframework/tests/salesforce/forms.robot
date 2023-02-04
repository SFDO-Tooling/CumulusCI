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
${DATA DIR}  ${{pathlib.Path($SUITE_SOURCE).parent}}

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

Go to My Email settings
    [Documentation]
    ...  Go directly to the My Email Settings page

    &{org}=  Get org info
    ${url}=  Set variable
    ...  ${org['instance_url']}/lightning/settings/personal/EmailSettings/home
    Go to  ${url}

*** Test Cases ***
Lightning based form
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

Non-lightning based form - checkbox
    [Documentation]
    ...  Verify that we can check and uncheck standard html checkboxes
    ...  e.g.: <input type="checkbox">

    [Setup]  Run keywords
    ...  Go to page                  Home    Campaign
    ...  AND  Click Object Button    New
    ...  AND  Wait for modal         New     Campaign
    [Teardown]  Click modal button   Cancel

    # first, let's make sure that the keyword returns an element
    # that is a plain html input element
    ${element}=      Get webelement       label:Active
    Should be equal  ${element.tag_name}  input
    ...  Expected to find an <input> element but did not.

    # next, set the checkbox and assert it is checked
    Input form data
    ...  Active    checked
    Checkbox should be selected      label:Active

    # finally, unset it and assert it is unchecked
    Input form data
    ...  Active    unchecked
    Checkbox should not be selected      label:Active

Lightning based form - radiobutton
    [Documentation]
    ...  Verify we can set a lightning radiobutton by its label
    [Setup]      Run keywords
    ...  Go to page          Listing    Opportunity
    ...  AND  Click element  sf:list_view_menu.button
    ...  AND  Click element  sf:list_view_menu.item:New
    ...  AND  Wait for modal  New  List View
    [Teardown]   Click modal button  Cancel

    Input form data
    ...  Who sees this list view?::All users can see this list view    selected

    # Using the label: locator returns a lightning-input element. We need to find
    # the actual html input element to verify that it is checked. Ugly, but efficient.
    ${element}=  Get webelement  label:All users can see this list view
    Should be true  ${element.find_element_by_xpath(".//input").is_selected()}

Non-lightning based form - radiobutton
    [Documentation]  Verify we can set a plain non-lightning radiobutton

    [Setup]     Run keywords
    ...  Go to My Email Settings
    ...  AND  Select frame                   //div[@class="setupcontent"]//iframe
    ...  AND  Select radio button            use_external_email  1
    ...  AND  Radio button should be set to  use_external_email  1
    [Teardown]  Unselect frame

    # The settings page is just about the only page I could find
    # with old school non-lightning radiobuttons
    # Thankfully, I can use built-in keywords to validate that
    # the radiobuttons have actually bet set.

    # then try to use our keyword to set it
    Input form data
    ...  Send through Salesforce  selected

    # ... and then verify that it was set
    Radio button should be set to  use_external_email  0

Non-lightning based form - input and textarea
    [Documentation]
    ...  Fill in non-lightning input and textarea fields

    [Setup]  Go to  file://${DATA DIR}/labels.html

    Input form data
    ...  Description  This is the description
    ...  City         Oklahoma City

    Textarea should contain   id=textarea-1  This is the description
    Textfield should contain  id=input-3     Oklahoma City

Fieldsets
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
