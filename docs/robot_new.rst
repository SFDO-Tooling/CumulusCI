=======================================
Acceptance Testing with Robot Framework
=======================================

In addition to the process of building packages, CumulusCI also provides the ability to create and run automated acceptance testing using Robot Framework. This document provides details about CumulusCI's integration with `Robot Framework <http://robotframework.org>`_ for automating tests using CumulusCI, Salesforce APIs, and Selenium. 

Robot Framework (or simply "robot") is a keyword-driven acceptance testing framework. *Keyword-driven* means that test cases are made up of high-level keywords that allow acceptance tests to be written in an intuitive, human-readable language ("Open browser", "Click link", "Insert text") rather than in a programming language. *Acceptance testing* refers to the process of testing an application from the user's perspective as the final proof that the product meets its requirements.

For example, here's a basic robot test case for creating a new Contact object.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot

   *** Test Cases ***
   Create a contact using the API

      # Create a new Contact
      ${contact id}=   Salesforce Insert  Contact
      ...  FirstName=Eleanor
      ...  LastName=Rigby

      # Get the new Contact and examine the contact object
      &{contact}=      Salesforce Get  Contact  ${contact id}
      Should be equal  ${contact}[FirstName]    Eleanor
      Should be equal  ${contact}[LastName]     Rigby

.. note::
    This test will be discussed in further detail later in this documentation.



Why Robot?
----------

What makes Robot Framework an ideal acceptance testing framework for Salesforce?

* Human readable test cases: Robot uses *domain-specific language*, or DSL, for testing in a browser. A DSL takes a complex set of instructions and presents them in a human-readable language. In the instance of Robot, instead of writing elaborate code for your test cases, you use basic, digestible keywords that don't require code syntax or functions.
* Test cases use keywords: Robot helps circumvent the actual writing of code (or, more accurately, writing as much code as previously required) by instead relying on reuseable keywords.
* Libraries provide keywords: Salesforce has a comprehensive standard library of Robot keywords created specifically to anticipate the needs of testers.

Existing testing tools like Apex and JEST are good for writing unit tests and low-level integration tests. However, it can be difficult to separate the intent of the test, and the features being tested, from the implementation of the test when using those tools.

Here's how robot was designed specifically to address problems associated with writing high-level acceptance tests using technology designed for unit and integration tests.

* Tests are written as a sequence of keywords that together form a domain-specific language tailored to testing Salesforce applications. In the previous test example, ``Salesforce Insert``, ``Salesforce Get`` and ``Should be equal`` are all keywords. 
* Keywords allow implementation details to be hidden from the test. In the previous test example, a new contact is created with the ``Salesforce Insert Contact`` keyword without the user seeing all the steps required to make an API call to create a contact.
* Robot organizes keywords into libraries, which provides a simple and effective method of organizing and sharing keywords between tests, and projects. In the previous example, defining ``Salesforce.robot`` as a resource automatically pulls in dozens of Salesforce-specific keywords.
* Robot tests can be easily read and understood by all stakeholders of a project (such as a product manager, scrum master, doc writer, and so on), not solely by the person who wrote the test.



Robot & CumulusCI
-----------------
 
CumulusCI's integration with robot builds automated acceptance test scenarios useful to Salesforce projects, such as:
 
* Browser testing with Selenium
* API-only tests interacting with the Salesforce REST, Bulk, and Tooling APIs
* Complex org automation via CumulusCI
* Combinations of all of the above
 
The ability to create rich, single-file acceptance tests that interact with CumulusCI's project-specific automation, Salesforce's APIs, and the Salesforce UI in a browser is the most exciting feature of the integration with robot. Robot also makes it easy to automate even complex regression scenarios and tests for edge-case bugs just by writing robot test suites, and with no need to change project automation in the ``cumulusci.yml`` file.


Custom Tasks
^^^^^^^^^^^^

CumulusCI integrates robot via custom tasks. The most common task is named ``robot``, but there are others that also make use of Robot Framework. Like with any task, you can get documentation and a list of arguments with the ``cci task info`` command. For example, ``cci task info robot_libdoc`` will display documentation for the ``robot_libdoc`` task.

Robot tasks include:

* ``robot``: Runs one or more robot tests.
* ``robot_libdoc``: Runs the `libdoc <http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#library-documentation-tool-libdoc>`_ command, which creates an HTML file with documentation for all the keywords that are passed to it.
* ``robot_testdoc``: Runs the `testdoc <http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#test-data-documentation-tool-testdoc>`_ command, which creates an HTML file with documentation for one or more test cases. 
* ``robot_lint``: Runs the static analysis tool `rflint <https://github.com/boakley/robotframework-lint/>`_, which is useful for validating robot tests against a set of rules related to code quality.


Custom Keywords
^^^^^^^^^^^^^^^

CumulusCI provides for acceptance testing a set of keywords unique to both Salesforce and CumulusCI, such as running other tasks, interacting with Salesforce applications, and calling Salesforce APIs. If you want to take a look at these keywords before diving into the examples featured here, see `Keywords.html <Keywords.html>`_.



Robot Directory Structure
-------------------------

When you initialize a project with ``cci project init``, several folders are created specifically for robot tests and resources. This is the folder structure.

.. code-block:: console

   ProjectName/
   ├── robot
   │   └── ProjectName
   │       ├── doc
   │       ├── resources
   │       ├── results
   │       └── tests

Though the examples and exercies in this documentation will illustrate the use of most of these folders, see `Advanced Robot <LINK TODO>` for more details on each one.



Robot Test Breakdown
--------------------

Again, here's the basic robot test case for creating a new Contact object. To follow along, save this code in a file named ``create_contact.robot`` in the ``robot/<ProjectName>/tests`` folder of your project's repository. This file is considered to be a test suite by virtue of having  the ``.robot`` extension with a ``Test Cases`` section.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot

   *** Test Cases ***
   Create a contact using the API

      # Create a new Contact
      ${contact id}=   Salesforce Insert  Contact
      ...  FirstName=Eleanor
      ...  LastName=Rigby

      # Get the new Contact and examine the contact object
      &{contact}=      Salesforce Get  Contact  ${contact id}
      Should be equal  ${contact}[FirstName]    Eleanor
      Should be equal  ${contact}[LastName]     Rigby

The test itself creates the ``Contact`` object, and then confirms that the object has the correct first and last names, by making a call to a Salesforce API. One of the strengths of robot is hiding the complexity of making an API call behind a keyword, so that in a test you only have to describe what is being created without exposing all the work necessary to actually create it, such as getting an access token, creating an API payload, making the API call, and parsing the results.

To run this test from the command line:

.. code-block:: console

   $ cci task run robot --suites robot/<ProjectName>/tests/create_contact.robot

.. note::
   Make sure to `set a default org <https://cumulusci.readthedocs.io/en/main/scratch_orgs.html#set-a-default-org>`_, or supply the ``--org`` argument on the command line. If you haven't created a scratch org yet, running the ``robot`` task creates one for you. 

The output will be similar to this.

.. code-block:: console

   $ cci task run robot --suites robot/CumulusCI-Test/create_contact.robot

   ==============================================================================
   Create Contact                                                                
   ==============================================================================
   Create a contact using the API                                        | PASS |
   ------------------------------------------------------------------------------
   Create Contact                                                        | PASS |
   1 test, 1 passed, 0 failed
   ==============================================================================
   Output:  /Users/boakley/dev/CumulusCI-Test/output.xml
   Log:     /Users/boakley/dev/CumulusCI-Test/log.html
   Report:  /Users/boakley/dev/CumulusCI-Test/report.html

In this example, robot creates an ``output.xml`` file and generates ``log.html`` and ``report.html`` files from that and stores them in the ``results`` folder. ``log.html`` contains details about executed test cases, such as statistics on every keyword that is run. ``report.html`` contains an overview of test execution results.


Syntax
^^^^^^

Here's a quick primer for the robot syntax in the ``create_contact.robot`` test case.

+--------+-------------------+----------------------------------------------------------------------------+
| Symbol | Name              | Description & Usage                                                        |
+========+===================+============================================================================+
| ``***``| Section Heading   | By convention, three stars on both sides of a heading designate a section  |
|        |                   | heading. Sections headings include ``Settings``, ``Test Cases``,           |
|        |                   | ``Keywords``, ``Variables``, ``Comments`` and ``Tasks``.                   |
+--------+-------------------+----------------------------------------------------------------------------+
| #      | Hash              | Designates comments.                                                       |
+--------+-------------------+----------------------------------------------------------------------------+
| ${}    | Variable          | Curly brackets with a name placed inside designates a variable.            |
|        |                   |                                                                            |
|        |                   | Inside ``{}``, variable names are case-insensitive. Spaces and underscores |
|        |                   | are treated as the same value, and also optional.                          |
|        |                   |                                                                            | 
|        |                   | The leading ``$`` character refers to a single value.                      |
+--------+-------------------+----------------------------------------------------------------------------+
| &{}    | Dictionary or Map | The leading ``&`` character refers to a dictionary or map for              |
|        |                   | key-value pairs, such as ``&{contact}``, which this test has defined       |
|        |                   | values for the keys ``FirstName`` and ``LastName``.                        |
+--------+-------------------+----------------------------------------------------------------------------+
| =      | Assignation       | Equals sign assigns a new value to the variable. It is allowed up to one   |
|        |                   | space before its placement but allowed more than two after, which is       |
|        |                   | helpful in formatting test cases into readable columns. It is entirely     |
|        |                   | optional.                                                                  |
+--------+-------------------+----------------------------------------------------------------------------+
| ...    | Ellipses          | Ellipses designate the continuation of a single-line command broken up     | 
|        |                   | over several lines for easier readability.                                 |
+--------+-------------------+----------------------------------------------------------------------------+
|        | Space             | Two or more spaces separate arguments from the keyword(s), and arguments   |
|        |                   | from each other. They can also align data for readability.                 |
+--------+-------------------+----------------------------------------------------------------------------+

For more details on robot syntax, visit the official `robot syntax documentation <http://robotframework.org/robotframework/2.9.2/RobotFrameworkUserGuide.html#test-data-syntax>`_.


Settings
^^^^^^^^

The Settings section of the ``.robot`` file sets up the entire test suite. Configurations established under Settings affect all test cases, including:

* `Suite Setup/Teardown`_
* Documentation, which describes the purpose of the test suite
* Tags, which allow a user to associate individual test cases with a label

By including the resource ``cumulusci/robotframework/Salesforce.robot``, which comes with CumulusCI, we inherit useful configuration and keywords for Salesforce testing automatically. The ``cumulusci/robotframework/Salesforce.robot`` file was designed to be the primary method of importing all keywords and variables provided by CumulusCI, so it's best practice for the file to be the first item imported in a test file under Settings. The ``Salesforce.robot`` file automatically imports the `CumulusCI Library <LINK TODO>`, the `Salesforce Library <LINK TODO>`, the third-party `SeleniumLibrary <http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html>`_ for browser testing via Selenium, and these most commonly used robot libraries. 

* `Collections <http://robotframework.org/robotframework/latest/libraries/Collections.html>`_
* `OperatingSystem <http://robotframework.org/robotframework/latest/libraries/OperatingSystem.html>`_
* `String <http://robotframework.org/robotframework/latest/libraries/String.html>`_
* `XML <http://robotframework.org/robotframework/latest/libraries/XML.html>`_
 
In addition to these Robot libraries, CumulusCI comes bundled with these third-party keyword libraries, which must be explicitly imported by any test suite that needs them.
 
* `RequestsLibrary <https://marketsquare.github.io/robotframework-requests/doc/RequestsLibrary.html>`_  for testing REST APIs. To use ``RequestsLibrary``, explicitly import it under the ``Settings`` section of your robot test.
* `All other robot libraries <https://robotframework.org/#libraries>`_. (Select the ``Standard`` tab.)


Test Cases
^^^^^^^^^^

The ``Test Cases`` section of the ``.robot`` file is where test cases are stored. To write a test case, its name is the first line of the code block, and placed in the far left margin of the test code block. All indented text under the test case name is the body of the test case. You can have multiple test cases under the ``Test Case`` section, but each test case must start in the left margin.

The keywords in the test cases are separated by two or more spaces from arguments. In this example, thanks to the ``Resource`` called in the ``Settings`` sections, keywords already stored within CumulusCI's Salesforce library are used.

* ``Salesforce Insert`` creates a new Contact object to insert inside Contacts, and is being given arguments for the Salesforce field names ``FirstName`` and ``LastName``.
* ``Salesforce Get`` retrieves an object based on its ID, in this instance the Contact object. 
* ``Should Be Equal`` compares objects, in this instance the ``FirstName`` and ``LastName`` fields of the Contact object.


Suite Setup/Teardown
--------------------

Most real-world tests require setup before the test begins (such as opening a browser, or creating test data), and cleanup after the test finishes (such as closing the browser, or deleting test data). Robot has support for both suite-level setup and teardown (such as open the browser before the first test, *and* close the browser after the last test) and test-level setup and teardown (such as open and close the browser at the start *and* the end of the test).

If you run the ``create_contact.robot`` test case several times, take notice that each time it runs, you add a new contact to your scratch org. If you have a test that depends on a specific number of contacts, the test could fail the second time you run it. To prevent this, you can create a teardown that will delete any contacts created during the test when the test is run.

Let's modify the ``create_contact.robot`` test case by adding a ``Suite Teardown`` that deletes the contacts created by any tests in the suite.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot
   Suite Teardown  Delete session records

   *** Test Cases ***
   Create a contact using the API

      # Create a new Contact
      ${contact id}=   Salesforce Insert  Contact
      ...  FirstName=Eleanor
      ...  LastName=Rigby

      # Get the new Contact and examine the contact object
      &{contact}=      Salesforce Get  Contact  ${contact id}
      Should be equal  ${contact}[FirstName]    Eleanor
      Should be equal  ${contact}[LastName]     Rigby

.. note:: 
    The ``Salesforce Insert`` keyword is designed to keep track of the IDs of the objects created. The ``Delete session records`` keyword deletes those objects.

To run this test from the command line:

.. code-block:: console

   $ cci task run robot --suites robot/<ProjectName>/tests/create_contact.robot



Generate Fake Data with Faker
-----------------------------

Rather than require a user to hard-code test data for robot tests, CumulusCI makes it simpler to generate the data you need with the ``get fake data`` keyword, which comes from the Faker library already installed with CumulusCI. ``Get fake data`` does much more than just return random strings; it generates strings in an appropriate format. We can ask it for a name, address, date, phone number, credit card number, and so on, and the data it returns will be in the proper format for acceptance testing.

Let's modify the ``create_contact.robot`` test case by generating a fake name with the ``get fake data`` keyword. Since the new ``Contact`` name is going to be random in this updated example, we can't hard-code an assertion on the name of the created contact. Instead, for illustrative purposes, this test simply logs the contact name. 

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot
   Suite Teardown  Delete session records

   *** Test Cases ***
   Create a contact with a generated name
      [Teardown]       Delete session records
      
      # Generate a name to use for our contact
      ${first name}=   Get fake data  first_name
      ${last name}=    Get fake data  last_name

      # Create a new Contact
      ${contact id}=   Salesforce Insert  Contact
      ...  FirstName=${first name}
      ...  LastName=${last name}

      # Get the new Contact and add their name to the log
      &{contact}=      Salesforce Get  Contact  ${contact id}
      Log  Contact name: ${contact}[Name]

To run this test from the command line:

.. code-block:: console

   $ cci task run robot --suites robot/<ProjectName>/tests/create_contact.robot



Create Custom Keywords
----------------------

Because robot uses domain-specific language, you can create your own custom keywords specific to your project's needs. This example shows how to move the creation of a test ``Contact`` into a keyword, which can then be used as a setup in multiple tests. 

For this example, let's create new robot test that generates a custom keyword called ``Create a test contact``. To follow along, save this code in a file named ``custom_keyword.robot`` in the ``robot/<ProjectName>/tests`` folder of your project's repository.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot
   Suite Teardown  Delete session records

   *** Test Cases ***
   Example of using a custom keyword in a setup step
      [Setup]      Create a test contact

      # Get the new Contact and add their name to the log
      &{contact}=      Salesforce Get  Contact  ${contact id}
      Log  Contact name: ${contact}[Name]

   *** Keywords ***
   Create a test contact
      [Documentation]  Create a temporary contact and return contact object
      [Return]         ${contact}

      # Generate a name to use for our contact
      ${first name}=   Get fake data  first_name
      ${last name}=    Get fake data  last_name

      # Create a new Contact
      ${contact id}=   Salesforce Insert  Contact
      ...  FirstName=${first name}
      ...  LastName=${last name}

      # Fetch the contact object to be returned
      &{contact} = Salesforce Get Contact ${contact_id}

To run this test from the command line:

.. code-block:: console

   $ cci task run robot --suites robot/<ProjectName>/tests/custom_keyword.robot

Test cases and keywords have the concept of settings specified by square brackets, which means test cases can have their own individual setups, teardowns, documentation, and returns. This is how Robot knows you're not referring to the keyword but rather a specific test case setting.



Use a Resource File
-------------------

Now that you know how to create a custom keyword that is reusable within a test file, you can build up a body of custom keywords to be shared project-wide by creating a resource file.

A resource file is similar to a normal test suite file, except there are no tests, only references to your project's personal library of custom keywords.

To follow along, save this code in a file named ``<ProjectName>.robot`` in the ``robot/<ProjectName>/resources`` folder of your project's repository. (Although it's not required to name the resource file after the project you're working in, it is considered an established best practice.)

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot

   *** Keywords ***
   Create a test contact
      [Documentation]  Create a temporary contact and return the id
      [Return]         ${contact id}

      # Generate a name to use for our contact
      ${first name}=   Get fake data  first_name
      ${last name}=    Get fake data  last_name

      # Create a new Contact
      ${contact id}=   Salesforce Insert  Contact
      ...  FirstName=${first name}
      ...  LastName=${last name}

.. note::
    Along with moving the ``Keywords`` section in the ``Custom Keyword`` robot test to this file, you must also import ``Salesforce.robot``, where the Faker library is defined.

Next, remove the ``Keywords`` section from the ``custom_keyword.robot`` test case. Then add an import statement referring to your ``<ProjectName>.robot`` resource file under the ``Settings`` section.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot
   Resource        <ProjectName>/resources/<ProjectName>.robot

   Suite Teardown  Delete session records

   *** Test Cases ***
   Example of using a custom keyword in a setup step
      [Setup]      Create a test contact

      # Get the new Contact and add their name to the log
      &{contact}=      Salesforce Get  Contact  ${contact id}
      Log  Contact name: ${contact}[Name]

.. note::
    Variables defined in resource files are accessible to all tests in a suite that imports the resource file.



Simple Browser Test
-------------------

Now that you know how to create objects using the API, let's explore how to use those objects in a browser test.

Let's create a robot test that uses ``Suite Setup`` to call the ``Open test browser`` keyword. To follow along, save this code in a file named ``ui.robot`` in the ``robot/<ProjectName>/tests`` folder of your project's repository.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot

   Suite Setup     Open test browser
   Suite Teardown  Delete records and close browser

   *** Test Cases ***
   Take screenshot of landing page
      Capture page screenshot

When the browser opens, the test case takes a screenshot, which can be a useful tool when trying to debug your tests (though it should only be used when necessary since screenshots can take up a lot of disk space). ``Suite Teardown`` then calls the ``Delete records and close browser`` keyword to complete the test. These simple yet foundational steps are essential to effective browser testing with robot.

.. note::
    Because this test case calls ``Open test browser``, a window appears on your screen while the test is running.

To run this test from the command line:

.. code-block:: console

   $ cci task run robot --suites robot/<ProjectName>/tests/ui.robot

In this example, robot creates an ``output.xml`` file, a ``log.html``, a ``report.html`` file, and a screenshot, and stores them in the ``results`` folder. If you open up the ``log.html`` file, you can scroll down to see whether each step of the test case passed or failed. Toggle the ``+`` tab of the ``Take screenshot of landing page`` test header to examine the results of the test. Toggle the ``+`` tab of the ``Capture page screenshot`` keyword to examine the screenshot taken of the landing page.

The keywords in this robot test are stored inside CumulusCI's Salesforce library. ``Open test browser`` comes from the ``Salesforce.robot`` file, and it does so much more than open the browser. For example, it logs the user into their org, and it uses the browser defined by the ${BROWSER} variable rather than requiring a test what browser is to be used.

Variables can be set in cumulusci.yml, or specified with the ``vars`` option under the robot task. For example, ${BROWSER} defaults to ``chrome`` but it can be set to ``firefox``. 
   
To set the browser to Firefox in the ``cumulusci.yml`` file:
 
.. code-block:: robot
      
   tasks:
      robot:
         options:
         vars:
            - BROWSER:firefox

To set the browser to Firefox from the command line *for a single test run*:
   
.. code-block:: console

   $ cci task run robot --vars BROWSER:firefox


Supported Browsers
^^^^^^^^^^^^^^^^^^

The ``robot`` task supports both Chrome and Firefox browsers, and the "headless" variations of these browsers, ``headlesschrome`` and ``headlessfirefox``. Using the headless version, browser tests will run without opening a browser window on the display. The tests still use a browser, but you can't see it while the test is running. This is most useful when running a test on a CI server such as MetaCI where there isn't a physical display connected to the server. 

The headless versions of the browsers are specified by prepending "headless" to the browser name. For example, the command line option to specify the headless version of chrome would be ``--var BROWSER:headlesschrome``.

.. tip::
    When running in headless mode, you can still capture screenshots of the browser window. The ``Capture Page Screenshot`` keyword becomes an indispensable tool when trying to debug tests that failed in headless mode.



Combine API Keywords and Browser Tests
--------------------------------------

In robot, API and browser keywords can be used together, which gives the user options for building more elaborate acceptance tests. 

In this example, let's build upon the original ``create_contact.robot`` test that integrates all the previous configurations covered in this document. To follow along, replace the code in the ``create_contact.robot`` test case in the ``robot/<ProjectName>/tests`` folder of your project's repository with this.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot

   Suite Setup     Open test browser
   Suite Teardown  Delete records and close browser

   *** Test Cases ***
   Take screenshot of list of contacts
      [Setup]  Create a test contact

      Go to object home  Contact
      Capture page screenshot

   *** Keywords ***
   Create a test contact
      [Documentation]  Create a temporary contact and return the id
      [Return]         ${contact id}

      # Generate a name to use for our contact
      ${first name}=   Get fake data  first_name
      ${last name}=    Get fake data  last_name

      # Create a new Contact
      ${contact id}=   Salesforce Insert  Contact
      ...  FirstName=${first name}
      ...  LastName=${last name}

The ``create_contact.robot`` test case not only creates a contact, it also opens up the browser to see that the contact appears in a list of contacts, takes a screenshot of the list, then deletes all new records created during the test run, and closes the browser.

To run this test from the command line:

.. code-block:: console

   $ cci task run robot --suites robot/<ProjectName>/tests/create_contact.robot



Run an Entire Suite of Tests
----------------------------

If you've followed along, you have the files ``create_contact.robot``, ``custom_keyword.robot`` and ``ui.robot`` saved in your ``tests`` folder. Up to this point, you ran these tests one file at a time. While a single .robot file is considered to be a test suite, robot also considers *folders* to be suites. You can pass a folder to robot, and robot will run all tests stored in that folder.

If you've saved all of the example files to the ``tests`` folder, you can run all of the tests in the command line.

.. code-block:: console
   $ cci task run robot --suites robot/<ProjectName>/tests

In the output you can see all of the tests written to this point have been run.

.. tip:: 
    Test suite folders can also contain nested folders of tests, making it easy to organize tests into functional groups. For example, you could store all API tests in a ``tests/api`` folder and all UI tests in a ``tests/ui`` folder.

Because running everything in the ``tests`` folder is such common practice for users running tests for a project, it is the default process for the ``robot`` task.

To run an entire suite of tests with the ``robot`` task:

.. code-block:: console
   $ cci task run robot

