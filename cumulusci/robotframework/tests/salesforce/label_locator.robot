*** Settings ***
Documentation
...  Tests for the custom locator strategy "label:"
...  These tests were created to catch the various ways form fields
...  and labels are marked up on Salesforce pages.

Resource        cumulusci/robotframework/Salesforce.robot
Library         OperatingSystem

Suite Setup     Open test browser
Suite Teardown  Delete records and close browser
Test Teardown   Log failure conditions

*** Variables ***

${DATA DIR}  ${{pathlib.Path($SUITE_SOURCE).parent}}
${TEST URL}  file://${DATA DIR}/labels.html


*** Keywords ***

Log failure conditions
    [Documentation]
    ...  Do some extra reporting when a test fails

    Run keyword if test failed
    ...  Run keywords
    ...  Log Location
    ...  Log Source
    ...  Capture page screenshot

Returned element should have id
    [Documentation]
    ...  This is the main assertion in a test case. It gets a webelement
    ...  using the label: locator and asserts that the correct element is
    ...  returned.
    [Arguments]  ${expected id}  ${locator}
    ${actual id}=  SeleniumLibrary.Get element attribute  ${locator}  id

    Should be equal  ${actual id}  ${expected id}
    ...  Expected the element id to be '${expected id}' but it was '${actual id}'
    ...  values=False

With HTML:
    [Documentation]
    ...  Inject html into our test document
    ...  Input is one or more string arguments that will be joined
    ...  and then inserted into the current document in a div
    ...  with the id 'input-data'
    [Arguments]  @{lines}

    ${html}=  Catenate  SEPARATOR=${\n}  @{lines}
    execute javascript
    ...  ARGUMENTS
    ...  ${HTML}
    ...  JAVASCRIPT
    ...  var element=document.querySelector('#test-data');
    ...  element.innerHTML = arguments[0];


*** Test Cases ***

Label pointing to input
    [Documentation]
    ...  Verify we can find input elements

    [Setup]  Go to  ${TEST URL}

    With HTML:
    ...  <label for='input-1'>Zipcode</label>
    ...  <input id='input-1'>

    Returned element should have id  input-1  label:Zipcode

Label pointing to textarea
    [Documentation]
    ...  Verify we can find textarea elements

    [Setup]  Go to  ${TEST URL}

    With HTML:
    ...  <label for='textarea-1'>Zipcode</label>
    ...  <textarea id='textarea-1'>

    Returned element should have id  textarea-1  label:Zipcode

Label inside a lightning component
    [Documentation]
    ...  Verify we can find a lightning component

    [Setup]  Go to  ${TEST URL}

    With HTML:
    ...  <lightning-combobox id='combobox-1'>
    ...      <label for='input-1'>Zipcode</label>
    ...      <input id='input-1'>
    ...  </lightning-combobox>

    Returned element should have id  combobox-1  label:Zipcode

Nested Lightning Components
    [Documentation]
    ...  Verify that the inner-most component is returned

    [Setup]  Go to  ${TEST URL}

    With HTML:
    ...  <lightning-picklist id='picklist-1'>
    ...      <lightning-combobox id='combobox-1'>
    ...          <label>Salutation</label>
    ...      </lightning-combobox>
    ...  <lightning-picklist>

    Returned element should have id  combobox-1  label:Salutation

Label with a single quote
    [Documentation]
    ...  Verify that labels with apostrophes don't trip us up

    [Setup]  Go to  ${TEST URL}

    With HTML:
    ...  <label for='input-1'>foo'bar</label>
    ...  <input id='input-1'>

    Returned element should have id  input-1  label:foo'bar

Simple label spread across multiple lines
    [Documentation]
    ...  Verify that label text spread across multiple lines is recognized

    [Setup]  Go to  ${TEST URL}

    With HTML:
    ...  <label for='input-1'>
    ...      Hello,
    ...      world
    ...  </label>
    ...  <input id='input-1'>

    Returned element should have id  input-1  label:Hello, world

Label with leading and trailing whitespace
    [Documentation]
    ...  Verify that we aren't tripped up by leading or trailing spaces

    [Setup]  Go to  ${TEST URL}

    With HTML:
    ...  <label for='input-1'> email </label>
    ...  <input id='input-1'>

    Returned element should have id  input-1  label:email

Label with inner span BEFORE the label text, simulating a required field
    [Documentation]
    ...  Verify we can find a label when there's additional elements
    ...  before the label text
    ...
    ...  Note: the assistiveText span is how some required fields are marked up

    [Setup]  Go to  ${TEST URL}

    With HTML:
    ...  <label for='input-1'>
    ...      <span class="assistiveText"> * </span>
    ...      Company Name
    ...  </label>
    ...  <input id='input-1'>

    Returned element should have id  input-1  label:Company Name

Label with inner span AFTER the label text, simulating a required field
    [Documentation]
    ...  Verify we can find a label when there's additional elements
    ...  after the label text
    ...
    ...  Note: the assistiveText span is how some required fields are marked up

    [Setup]  Go to  ${TEST URL}

    With HTML:
    ...  <label for='input-1'>
    ...      Street Address
    ...      <span class="assistiveText"> * </span>
    ...  </label>
    ...  <input id='input-1'>

    Returned element should have id  input-1  label:Street Address

Label that doesn't exist yields an appropriate error
    [Documentation]
    ...  Verify we get an appropriate exception when we can't find the label

    [Setup]  Go to  ${TEST URL}

    With HTML:
    ...  <label for='input-1'>
    ...      Whatever
    ...  </label>
    ...  <input id='input-1'>

    Run keyword and expect error
    ...  Element with locator 'label:Bogus' not found.
    ...  Get Webelement  label:Bogus

Label where text is in a span
    [Documentation]
    ...  Verify that we can find a label when the text is in a span

    [Setup]  Go to  ${TEST URL}

    With HTML:
    ...  <label for='input-1'
    ...      <span>Ship To Street</span>
    ...  </label>
    ...  <input id='input-1'>

    Returned element should have id  input-1  label:Ship To Street

Multiple identical labels in fieldsets
    [Documentation]
    ...  Verify that we can distinguish between similar labels
    ...  in different fieldsets

    [Setup]  Go to  ${TEST URL}

    With HTML:
    ...  <fieldset><div>Section 1</div>
    ...      <label for='input-1'>
    ...          Name
    ...      </label>
    ...      <input id='input-1'>
    ...  </fieldset>
    ...  <fieldset><div>Section 2</div>
    ...      <label for='input-2'>
    ...          Name
    ...      </label>
    ...      <input id='input-2'>
    ...  </fieldset>

    Returned element should have id  input-1  label:Section 1::Name
    Returned element should have id  input-2  label:Section 2::Name

