*** Settings ***

Resource        cumulusci/robotframework/Salesforce.robot
Library         TestLibrary.py
Library         Dialogs

Suite setup     Open test page in browser  ${BROWSER}
Suite teardown  Close all browsers


*** Variables ***

${BROWSER}  chrome

*** Keywords ***

Open test page in browser
    [Documentation]
    ...  This opens a browser and loads the file 'testpage.html',
    ...  which is in the same folder as this test case
    [Arguments]  ${BROWSER}

    ${here}=      evaluate  os.path.dirname($suite_source)        modules=os
    ${testfile}=  evaluate  os.path.join($here, "testpage.html")  modules=os
    open browser  file://${testfile}  ${BROWSER}


*** Test Cases ***

Verify that TestLibrary is initialized
    [Documentation]
    ...  Verify that the library is initialized. This test was aded
    ...  when I was refactoring RetryingSeleniumLibraryMixin and
    ...  Salesforce.py, and discovered that the __init__ wasn't being
    ...  called after some of my changes. This test exists to make
    ...  sure that doesn't happen again.

    ${testlib}=  get library instance  TestLibrary
    Should be true  ${testlib.initialized}
    ...  Expected TestLibrary.initialized value: "${testlib.initialized}"

Verify BaseLibrary properties are inherited
    [Documentation]
    ...  Verify that all of the BaseLibrary properties are inherited
    ...  by TestLibrary
    ${testlib}=  get library instance  TestLibrary
    Variable should exist  ${testlib.builtin}
    Variable should exist  ${testlib.cumulusci}
    Variable should exist  ${testlib.salesforce}
    Variable should exist  ${testlib.salesforce_api_version}

Verify automatic selenium retry on undecorated keyword
    [Documentation]
    ...  This test verifies that methods in the library have the retry
    ...  behavior added by default when inheriting from BaseLibrary

    [Setup]  Reload page

    # assert that the green div isn't clickable
    # note: chrome and firefox throw different errors, so we have to
    # be a bit loosey-goosey with the expected error.

    run keyword and expect error  *Element*green-div*is not clickable*
    ...  click element  id:green-div

    # Now, arrange for the element to be clickable in the near future
    # and try again. This time, we should automatically wait for two
    # seconds, and the click should succeed

    ${testlib}=  get library instance  TestLibrary
    ${expected_retry_count}=  evaluate  $testlib.retry_count + 1
    execute javascript        return setTimeout(raise_green, 500)
    click element with default retry  id:green-div

    # assert that the retry happened
    ${duration}=  get duration of previous keyword
    should be true  $duration > 2.0
    should be equal as numbers  ${testlib.retry_count}  ${expected_retry_count}

Verify @selenium_retry(True) keyword decorator
    [Documentation]
    ...  This test verifies that we automatically retry selenium
    ...  instructions that fail under certain circumstances when the
    ...  keyword is explicitly decorated with @selenium_retry(True)

    [Setup]  Reload page

    # assert that the green div isn't clickable
    # note: chrome and firefox throw different errors, so we have to
    # be a bit loosey-goosey with the expected error.

    run keyword and expect error  *Element*green-div*is not clickable*
    ...  click element  id:green-div

    # Now, arrange for the element to be clickable in the near future
    # and try again. This time, we should automatically wait for two
    # seconds, and the click should succeed

    ${testlib}=  get library instance  TestLibrary
    ${expected_retry_count}=  evaluate  $testlib.retry_count + 1
    execute javascript        return setTimeout(raise_green, 500)
    click element with explicit retry  id:green-div

    # assert that the retry happened
    ${duration}=  get duration of previous keyword
    should be true  $duration > 2.0
    should be equal as numbers  ${testlib.retry_count}  ${expected_retry_count}

Verify @selenium_retry(False) decorator
    [Documentation]
    ...  Verify that a keyword which uses the @selenium_retry(False)
    ...  decorator does not attempt a retry
    [Setup]  reload page

    # try to click the hidden green div and verify
    # that no retry was attempted
    ${testlib}=  get library instance  TestLibrary
    ${expected_retry_count}=  evaluate  $testlib.retry_count

    run keyword and expect error  *Element*green-div*is not clickable*
    ...  click element without retry  id:green-div
    should be equal as numbers  ${testlib.retry_count}  ${expected_retry_count}
