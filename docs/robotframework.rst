===============
Robot Framework
===============

This document provides details about CumulusCI's integration with Robot Framework for automating tests using the CumulusCI, Salesforce API's, and Selenium.

Why Robot Framework?
====================

Robot Framework provides an abstraction layer for writing automated test scenarios in Python and via text keywords in .robot files.  Since Robot Framework is written in Python (like CumulusCI) and has a robust SeleniumLibrary for automated browser testing, it was an easy integration providing a lot of power.

CumulusCI's integration with Robot Framework allows building automated test scenarios useful to Salesforce projects:

* Browser testing with Selenium
* API only tests interacting with the Salesforce REST, Bulk, and Tooling API's
* Complex org automation via CumulusCI
* Combinations of all of the above

The ability to create rich, single file integration tests that interact with CumulusCI's project specific automation, Salesforce's APIs, and the Salesforce UI in a browser is the most exciting feature of the integration with Robot Framework.

The integration with Robot Framework adds a new dimension to CumulusCI.  Before, automating the recreation of a test environment for an edge case bug reported in a custom org would have required creating new tasks in cumulusci.yml which pollute the project's task list used by everyone on the project for an obscure scenario needed only for regression testing.  Now, you can create the test scenario in a .robot test file and run it through the standard **robot** task in CumulusCI.  Adding a new test scenario just adds a new file in the repository rather than a new task in CumulusCI.

Example Robot Test
==================

The following test file placed under **tests/create_contact.robot** in your project's repository automates the testing of creating a Contact through the Salesforce UI in a browser and via the API.  As an added convenience, it automatically deletes the created Contacts in the Suite Teardown step:

.. code-block:: robotframework
   
   *** Settings ***
   
   Resource        cumulusci/robotframework/Salesforce.robot
   Suite Setup     Open Test Browser
   Suite Teardown  Delete Records and Close Browser
   
   *** Test Cases ***
   
   Via API
       ${first_name} =       Generate Random String
       ${last_name} =        Generate Random String
       ${contact_id} =       Salesforce Insert  Contact
       ...                     FirstName=${first_name}
       ...                     LastName=${last_name}
       &{contact} =          Salesforce Get  Contact  ${contact_id}
       Validate Contact      ${contact_id}  ${first_name}  ${last_name}
   
   Via UI
       ${first_name} =       Generate Random String
       ${last_name} =        Generate Random String
       Go To Object Home     Contact
       Click Object Button   New
       Populate Form
       ...                   First Name=${first_name}
       ...                   Last Name=${last_name}
       Click Modal Button    Save
       Wait Until Modal Is Closed
       ${contact_id} =       Get Current Record Id
       Store Session Record  Contact  ${contact_id}
       Validate Contact      ${contact_id}  ${first_name}  ${last_name}
        
   
   *** Keywords ***
   
   Validate Contact
       [Arguments]          ${contact_id}  ${first_name}  ${last_name}
       # Validate via UI
       Go To Record Home    Contact  ${contact_id}
       Page Should Contain  ${first_name} ${last_name}
       # Validate via API
       &{contact} =     Salesforce Get  Contact  ${contact_id}
       Should Be Equal  ${first_name}  &{contact}[FirstName]
       Should Be Equal  ${last_name}  &{contact}[LastName]


NOTE: In the example output, the WARN line shows functionality from the Salesforce Library which helps handle retry scenarios common to testing against Salesforce's Lightning UI.  In this case, it automatically retried the wait for the modal window to close after creating a contact in a browser.

Settings
--------

The Settings section of the robot file sets up the entire test suite.  By including the Resource cumulusci/robotframework/Salesforce.robot which comes with CumulusCI, we inherit a lot of useful configuration and keywords for Salesforce testing automatically.

The Suite Setup and Suite Teardown are run at the start and end of the entire test suite.  In the example test, we're using the **Open Test Browser** keyword from the Salesforce.robot file to open a test browser.  We're also using the **Delete Records and Close Browser** keyword from Salesforce.robot to automatically delete all records created in the org during the session and close the test browser.

Test Cases
----------

The two test cases test the same operation done through two different paths: the Salesforce REST API and the Salesforce UI in a browser.

Via API
^^^^^^^

This test case uses the **Generate Random String** keyword to create random strings for the contact's first and last name.  It then uses the **Salesforce Insert** keyword from the Salesforce Library (included via Salesforce.robot) to insert a Contact using the random first and last names.  Next, it uses **Salesforce Get** to retrieve the Contact's information as a dictionary.

Finally, the test calls the **Validate Contact** keyword explained in the Keywords section below.

Via UI
^^^^^^

This test case also uses **Generate Random String** for the first and last name, but instead uses the test browser to create a Contact via the Salesforce UI.  Using keywords from the Salesforce Library, it navigates to the Contact home page and clicks the **New** button to open a modal form.  It then uses **Populate Form** to fill in the First Name and Last Name fields (selected by field label) and uses **Click Modal Button** to click the **Save** button and **Wait Until Modal Is Closed** to wait for the modal to close.

At this point, we should be on the record view for the new Contact.  We use the **Get Current Record Id** keyword to parse the Contact's ID from the url in the browser and the **Store Session Record** keyword to register the Contact in the session records list.  The session records list stores the type and id of all records created in the session which is used by the **Delete Records and Close Browser** keyword on Suite Teardown to delete all the records created during the test.  In the **Via API** test, we didn't have to register the record since the **Salesforce Insert** keyword does that for us automatically.  In the **Via UI** test, we created the Contact in the browser and thus need to store its ID manually for it to be deleted.

Keywords
--------

The **Keywords** section allows you to define keywords useful in the context of the current test suite.  This allows you to encapsulate logic you want to reuse in multiple tests.  In this case, we've defined the **Validate Contact** keyword which accepts the contact id, first, and last names as argument and validates the Contact via the UI in a browser and via the API via **Salesforce Get**.  By abstracting out this keyword, we avoid duplication of logic in the test file and ensure that we're validating the same thing in both test scenarios.

Running the Test Suite
----------------------

This simple test file can then be run via the **robot** task in CumulusCI:

.. code-block:: console

   $ cci task run robot -o suites tests/create_contact.robot -o vars BROWSER:firefox
   2018-03-12 12:43:35: Getting scratch org info from Salesforce DX
   2018-03-12 12:43:37: Beginning task: Robot
   2018-03-12 12:43:37:        As user: test-zel2batn5wud@example.com
   2018-03-12 12:43:37:         In org: 00D3B0000004X9z
   2018-03-12 12:43:37:
   2018-03-12 12:43:38: Getting scratch org info from Salesforce DX
   ==============================================================================
   Create Contact
   ==============================================================================
   Via API                                                               | PASS |
   ------------------------------------------------------------------------------
   [ WARN ] Retrying call to method _wait_until_modal_is_closed
   Via UI                                                                | PASS |
   ------------------------------------------------------------------------------
   Create Contact                                                        | PASS |
   2 critical tests, 2 passed, 0 failed
   2 tests total, 2 passed, 0 failed
   ==============================================================================
   Output:  /Users/jlantz/dev/HEDAP/output.xml
   Log:     /Users/jlantz/dev/HEDAP/log.html
   Report:  /Users/jlantz/dev/HEDAP/report.html

CumulusCI Library
=================

The CumulusCI Library for Robot Framework provides access to CumulusCI's functionality from inside a robot test.  It is mostly used to get credentials to a Salesforce org and to run more complex automation to set up the test environment in the org.

Logging Into An Org
-------------------

The **Login Url*** keyword returns a url with an updated OAuth access token to automatically log into the CumulusCI org from CumulusCI's project keychain.

Run Task
--------

The **Run Task** keyword is used to run named CumulusCI tasks configured for the project.  These can be any of CumulusCI's built in tasks as well as project specific custom tasks from the project's cumulusci.yml file.

**Run Task** accepts a single argument, the task name.  It optionally accepts task options in the format **option_name=value**.

Run Task Class
--------------

The **Run Task Class** keyword is for use cases where you want to use one of CumulusCI's Python task classes to automate part of a test scenario but don't want to have to map a custom named task at the project level.

**Run Task Class** accepts a single argument, the **class_path** like would be entered into cumulusci.yml such as **cumulusci.tasks.salesforce.Deploy**.  Like **Run Task**, you can also optionally pass task options in the format **option_name=value**.

Full Documentation
------------------

Use the following links to download generated documentation for the CumulusCI Library and Resource file:

* :download:`CumulusCI Robot Library <../docs/robot/CumulusCI_Library.html>`
* :download:`CumulusCI Robot Resource <../docs/robot/CumulusCI_Resource.html>`

Salesforce Library
==================

The Salesforce Library provides a set of useful keywords for interacting with Salesforce's Lightning UI and Salesforce's APIs to test Salesforce applications.

UI Keywords
-----------

The goal of the UI keywords in the Salesforce Library is to abstract out common interactions with Salesforce from interactions with your application's UI.  The Salesforce Library itself has an extensive suite of robot tests which are regularly run to alert us to any changes in the base Salesforce UI.  By centralizing these interactions and regularly testing them, the Salesforce Library provides a more stable framework on which to build your product tests.

There are too many keywords relating to UI interactions to cover here.  Please reference the full Salesforce Library documentation below.

API Keywords
------------
In addition to browser interactions, the Salesforce Library also provides the following keywords for interacting with the Salesforce REST API:

* **Salesforce Delete**: Deletes a record using its type and ID
* **Salesforce Get**: Gets a dictionary of a record from its ID
* **Salesforce Insert**: Inserts a record using its type and field values.  Returns the ID.
* **Salesforce Query**: Runs a simple query using the object type and field=value syntax.  Returns a list of matching record dictionaries.
* **Salesforce Update**: Updates a record using its type, ID, and field=value syntax
* **SOQL Query**: Runs a SOQL query and returns a REST API result dictionary

Full Documentation
------------------

Use the following links to download generated documentation for the Salesforce Library and Resource file:

* :download:`Salesforce Robot Library <../docs/robot/Salesforce_Library.html>`
* :download:`Salesforce Robot Resource <../docs/robot/Salesforce_Resource.html>`

CumulusCI Robot Tasks
=====================

CumulusCI includes two tasks for working with Robot Framework tests and keyword libraries:

* **robot**: Runs robot test suites.  By default, recursively runs all tests located under tests/.  Test suites can be overridden via the **suites** keyword and variables inside robot files can be overridden using the **vars** option with the syntax VAR:value (ex: BROWSER:firefox).
* **robot_testdoc**: Generates html documentation of your whole robot test suite and writes to tests/test_suite.html.

Additionally, the RobotLibDoc task class can be wired up to generate library documentation if you choose to create a library of robot keywords for your project using the following added to the cumulusci.yml file:

.. code-block:: yaml

   tasks:
       robot_libdoc:
           description: Generates HTML documentation for the MyProject Robot Framework library
           options:
               path: tests/MyProject.robot
               output: tests/MyProject_Library.html
 
Creating Project Tests
======================

Like in the example above, all project tests live in .robot files stored under the tests/ directory in the project.  You can choose how you want to structure the .robot files into directories by just moving the files around.  Directories are treated by robot as a parent test suite so a directory named "standard_objects" would become the "Standard Objects" test suite.

The following document is recommended reading:
https://github.com/robotframework/HowToWriteGoodTestCases/blob/master/HowToWriteGoodTestCases.rst
