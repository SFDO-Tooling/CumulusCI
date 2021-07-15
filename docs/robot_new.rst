=======================================
Acceptance Testing with Robot Framework
=======================================

CumulusCI can help automate another important aspect of building packages: acceptance testing. It's the process of testing an application from the user's perspective as the final proof that the product meets its requirements.While there are plenty of testing tools, we're partial to Robot Framework, an acceptance testing framework that you can use with and within CumulusCI to create and run automated acceptance tests for your Salesforce projects.

Robot Framework (or just Robot) is a keyword-driven acceptance testing framework. *Keyword-driven* means that users can write test cases in an intuitive, human-readable language made up of high-level, reusable keywords (``Open test browser``, ``Delete records and close browser``) rather than in a programming language. 

For example, in this basic Robot test case that creates a new ``Contact`` record, you can see how straightforward the keyword syntax is. Practically anyone can understand ``Salesforce Insert``, ``Salesforce Get``, and ``Should be equal``, even if someone is brand new to test automation.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot

   *** Test Cases ***
   Create a Contact using the API

      # Create a new Contact
      ${contact id}=   Salesforce Insert  Contact
      ...  FirstName=Eleanor
      ...  LastName=Rigby

      # Get the new Contact and examine it
      &{contact}=      Salesforce Get  Contact  ${contact id}
      Should be equal  ${contact}[FirstName]    Eleanor
      Should be equal  ${contact}[LastName]     Rigby



The Versatile Acceptance Tester
-------------------------------

Acceptance testing touches on multiple aspects of an application such as the data model, custom APIs, performance, and the user experience in the browser. Existing testing tools like Apex and Jest are good for writing unit tests and low-level integration tests. However, it can be difficult to understand the intent of a test, and the features being tested, when the test itself involves multiple lines of code detailing where to fetch data from, and how, and other such implementation details.

Robot was designed specifically to address these problems associated with writing high-level acceptance tests for every aspect of an application, often in a single test suite. Here’s how:

* Human-readable test cases: Robot lets you create a domain-specific language (DSL), which takes a complex set of instructions and presents them in a human-readable language. In the case of Robot, this DSL is built upon reusable keywords that help design test cases that can be easily understood by all project stakeholders--not solely by the person who wrote the test.
* Keyword libraries: Robot organizes keywords into libraries, which provide a simple, effective method to organize and share keywords between tests and projects. CumulusCI comes with a comprehensive standard library of Robot keywords created specifically to anticipate the needs of Salesforce testers. In the previous example, when you define ``Salesforce.robot`` as a resource, it automatically pulls in dozens of Salesforce-specific keywords.
* Streamlined test cases: Keywords allow implementation details to be handled by the test but not explicitly itemized in the test. In the previous example, a new ``Contact`` record is created with the ``Salesforce Insert`` keyword, but we don't see all the steps required to make an API call to create the record.


Custom Tasks
^^^^^^^^^^^^

CumulusCI integrates with Robot via custom tasks. The most common task is named ``robot``, which runs one or more Robot tests. Here's a sampling of other Robot tasks.

* ``robot_libdoc``: Runs the `libdoc <http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#library-documentation-tool-libdoc>`_ command, which creates an HTML file with documentation about all the keywords that are passed to it.
* ``robot_testdoc``: Runs the `testdoc <http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#test-data-documentation-tool-testdoc>`_ command, which creates an HTML file with documentation about one or more test cases.
* ``robot_lint``: Runs the static analysis tool `rflint <https://github.com/boakley/robotframework-lint/>`_, which can validate Robot tests against a set of rules related to code quality.

Like with any CumulusCi task, you can get documentation and a list of arguments with the ``cci task info`` command. For example, ``cci task info robot_libdoc`` displays documentation for the ``robot_libdoc`` task.


Custom Keywords
^^^^^^^^^^^^^^^

CumulusCI provides a set of keywords unique to both Salesforce and CumulusCI for acceptance testing. These keywords can run other tasks, interact with Salesforce applications, call Salesforce APIs, and so on. To learn more about these keywords, see `Keywords.html <https://cumulusci.readthedocs.io/en/stable/Keywords.html>`_.



Robot Directory Structure
-------------------------

When a project is initialized with ``cci project init``, this folder structure is created for Robot tests and resources.

.. code-block:: console

   ProjectName/
   ├── robot
   │   └── ProjectName
   │       ├── doc
   │       ├── resources
   │       ├── results
   │       └── tests

Though the examples and exercises in this documentation illustrate the use of these folders, see `Advanced Robot <LINK TODO>` for more details on each one.



Robot Test Breakdown
--------------------

Again, here's the basic Robot test case to create a new ``Contact`` record. Save this code in a file named ``create_contact.robot`` in the ``robot/<ProjectName>/tests`` folder of your project's repository. This file is a test suite by virtue of the ``.robot`` extension with a ``Test Cases`` section stored inside.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot

   *** Test Cases ***
   Create a Contact using the API

      # Create a new Contact
      ${contact id}=   Salesforce Insert  Contact
      ...  FirstName=Eleanor
      ...  LastName=Rigby

      # Get the new Contact and examine it
      &{contact}=      Salesforce Get  Contact  ${contact id}
      Should be equal  ${contact}[FirstName]    Eleanor
      Should be equal  ${contact}[LastName]     Rigby

The test makes two calls to the Salesforce API: one to create the ``Contact`` record, and another to confirm that the record has the correct first and last names. Robot hides the complexity of making an API call behind a keyword, so in a test you only describe what is created without exposing all the work necessary to actually create it, such as getting an access token, creating an API payload, making the API call, and parsing the results.

To run this test from the command line:

.. code-block:: console

   $ cci task run robot --suites robot/<ProjectName>/tests/create_contact.robot

.. note::
   Make sure to `set a default org <https://cumulusci.readthedocs.io/en/main/scratch_orgs.html#set-a-default-org>`_, or supply the ``--org`` argument on the command line. If you haven't created a scratch org yet, the ``robot`` task creates one for you. 

The output is similar to this.

.. code-block:: console

   $ cci task run robot --suites robot/CumulusCI-Test/create_contact.robot

   ==============================================================================
   Create Contact                                                                
   ==============================================================================
   Create a Contact using the API                                        | PASS |
   ------------------------------------------------------------------------------
   Create Contact                                                        | PASS |
   1 test, 1 passed, 0 failed
   ==============================================================================
   Output:  /Users/boakley/dev/CumulusCI-Test/output.xml
   Log:     /Users/boakley/dev/CumulusCI-Test/log.html
   Report:  /Users/boakley/dev/CumulusCI-Test/report.html

Each time Robot runs, it creates new iterations of the files ``output.xml``, ``log.html`` and ``report.html`` in the ``results`` folder. ``log.html`` contains details about executed test cases, such as statistics on every keyword that is run. ``report.html`` contains an overview of test execution results.


Syntax
^^^^^^

Here's a quick primer for the Robot syntax in the ``create_contact.robot`` test case.

+--------+-------------------+----------------------------------------------------------------------------+
| Symbol | Name              | Description & Usage                                                        |
+========+===================+============================================================================+
| ``***``| Section Heading   | By convention, three stars on both sides of a heading designate a section  |
|        |                   | heading. Section headings include ``Settings``, ``Test Cases``,            |
|        |                   | ``Keywords``, ``Variables``, ``Comments``, and ``Tasks``.                  |
+--------+-------------------+----------------------------------------------------------------------------+
| #      | Hash              | Designates comments.                                                       |
+--------+-------------------+----------------------------------------------------------------------------+
| ${}    | Variable          | Curly brackets with a name placed inside designates a variable.            |
|        |                   |                                                                            |
|        |                   | Inside ``{}``, variable names are case-insensitive. Spaces and underscores |
|        |                   | are treated as the same value, and also optional.                          |
|        |                   |                                                                            | 
|        |                   | The lead ``$`` character refers to a single value.                         |
+--------+-------------------+----------------------------------------------------------------------------+
| &{}    | Dictionary or Map | The lead ``&`` character refers to a dictionary or map for key-value       |
|        |                   | pairs, such as ``&{contact}``, which in this test has defined values for   |
|        |                   | the keys ``FirstName`` and ``LastName``.                                   |
+--------+-------------------+----------------------------------------------------------------------------+
| =      | Assignment        | Equals sign assigns a new value to the variable. It is given up to one     |
|        |                   | space before its placement but more than two after, which is helpful       |
|        |                   | to format test cases into readable columns. It is entirely optional.       |
+--------+-------------------+----------------------------------------------------------------------------+
| ...    | Ellipses          | Ellipses designate the continuation of a single-line command broken up     | 
|        |                   | over several lines for easier readability.                                 |
+--------+-------------------+----------------------------------------------------------------------------+
|        | Space             | Two or more spaces separate arguments from the keyword(s), and arguments   |
|        |                   | from each other. They can also align data for readability.                 |
+--------+-------------------+----------------------------------------------------------------------------+

For more details on Robot syntax, visit the official `robot syntax documentation <http://robotframework.org/robotframework/2.9.2/RobotFrameworkUserGuide.html#test-data-syntax>`_.


Settings
^^^^^^^^

The Settings section of the ``.robot`` file sets up the entire test suite. Configurations established under ``Settings`` affect all test cases, such as:

* `Suite Setup/Teardown`_
* ``Documentation``, which describes the purpose of the test suite
* ``Tag``, which lets a user associate individual test cases with a label

The resource ``cumulusci/robotframework/Salesforce.robot`` comes with CumulusCI and automatically inherits useful configuration and keywords for Salesforce testing. The ``Salesforce.robot`` file is the primary method of importing all keywords and variables provided by CumulusCI, so it's best practice for the file to be the first item imported in a test file under ``Settings``. It also imports the `CumulusCI Library <Keywords.html#file-cumulusci.robotframework.CumulusCI>`_, the `Salesforce Library <LINK TODO>`, the third-party `SeleniumLibrary <http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html>`_ for browser testing via Selenium, and these most commonly used Robot libraries. 

* `Collections <http://robotframework.org/robotframework/latest/libraries/Collections.html>`_
* `OperatingSystem <http://robotframework.org/robotframework/latest/libraries/OperatingSystem.html>`_
* `String <http://robotframework.org/robotframework/latest/libraries/String.html>`_
* `XML <http://robotframework.org/robotframework/latest/libraries/XML.html>`_
 
CumulusCI also comes bundled with these third-party keyword libraries, which must be explicitly imported by any test suite that needs them.
 
* `RequestsLibrary <https://marketsquare.github.io/robotframework-requests/doc/RequestsLibrary.html>`_  for testing REST APIs. To use ``RequestsLibrary``, explicitly import it under the ``Settings`` section of your Robot test.
* `All other Robot libraries <https://robotframework.org/#libraries>`_. (Select the "Standard" tab.)


Test Cases
^^^^^^^^^^

The ``Test Cases`` section of the ``.robot`` file is where test cases are stored. The name of a test case is the first line of a code block placed in the far left margin. All indented text under the test case name is the body of the test case. You can have multiple test cases under the ``Test Case`` section, but each test case must start in the far left margin.

Keywords in the test cases are separated by two or more spaces from arguments. In the ``create_contact.robot`` test case, thanks to the ``Resource`` called in the ``Settings`` sections, these keywords already stored within CumulusCI's Salesforce library are used.

* ``Salesforce Insert`` creates a new ``Contact`` record, and is given arguments for the Salesforce field names ``FirstName`` and ``LastName``.
* ``Salesforce Get`` retrieves a record based on its ID, in this instance the ``Contact`` record. 
* ``Should Be Equal`` compares records, in this instance the ``FirstName`` and ``LastName`` fields of the ``Contact`` record.


Suite Setup/Teardown
--------------------

Most real-world tests require setup before the test begins (such as opening a browser, or creating test data), and cleanup after the test finishes (such as closing the browser, or deleting test data). Robot has support for both suite-level setup and teardown (such as opening the browser before the first test, *and* closing the browser after the last test) and test-level setup and teardown (such as opening and closing the browser at the start *and* the end of the test).

If you run the ``create_contact.robot`` test case several times, you add a new ``Contact`` record to your scratch org each time it runs. If you have a test that depends on a specific number of ``Contact`` records, the test can fail the second time you run it. This can be prevented by creating a teardown that deletes any ``Contact`` records created when the test is run.

Let's modify the ``create_contact.robot`` test case with a ``Suite Teardown`` that deletes the ``Contact`` records created by any tests in the suite.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot
   Suite Teardown  Delete session records

   *** Test Cases ***
   Create a Contact using the API

      # Create a new Contact
      ${contact id}=   Salesforce Insert  Contact
      ...  FirstName=Eleanor
      ...  LastName=Rigby

      # Get the new Contact and examine it
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

Rather than require a user to hard-code test data for Robot tests, CumulusCI makes it simpler to generate the data you need with the ``get fake data`` keyword, which comes from the Faker library already installed with CumulusCI. ``Get fake data`` does much more than just return random strings; it generates strings in an appropriate format. You can ask it for a name, address, date, phone number, credit card number, and so on, and get back data in the proper format for acceptance testing.

Let's modify the ``create_contact.robot`` test case to generate a fake name with the ``get fake data`` keyword. Since the new ``Contact`` name is random in this updated example, you can't hard-code an assertion on the name of the created contact. Instead, for illustrative purposes, this test logs the ``Contact`` name. 

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot
   Suite Teardown  Delete session records

   *** Test Cases ***
   Create a Contact with a generated name
      [Teardown]       Delete session records
      
      # Generate a name to use for Contact
      ${first name}=   Get fake data  first_name
      ${last name}=    Get fake data  last_name

      # Create a new Contact
      ${contact id}=   Salesforce Insert  Contact
      ...  FirstName=${first name}
      ...  LastName=${last name}

      # Get the new Contact and add name to the log
      &{contact}=      Salesforce Get  Contact  ${contact id}
      Log  Contact name: ${contact}[Name]

To run this test from the command line:

.. code-block:: console

   $ cci task run robot --suites robot/<ProjectName>/tests/create_contact.robot



Create Custom Keywords
----------------------

Because Robot uses a domain-specific language, you can create your own custom keywords specific to your project's needs, and that can be used in multiple tests inside your project.

Let's create a new Robot test that includes a custom keyword called ``Create a test contact``, which creates a ``Contact`` record. Save this code in a file named ``custom_keyword.robot`` in the ``robot/<ProjectName>/tests`` folder of your project's repository.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot
   Suite Teardown  Delete session records

   *** Test Cases ***
   Example of using a custom keyword in a setup step
      [Setup]      Create a test contact

      # Get the new Contact and add name to the log
      &{contact}=      Salesforce Get  Contact  ${contact id}
      Log  Contact name: ${contact}[Name]

   *** Keywords ***
   Create a test contact
      [Documentation]  Create a temporary Contact and return it
      [Return]         ${contact}

      # Generate a name to use for Contact
      ${first name}=   Get fake data  first_name
      ${last name}=    Get fake data  last_name

      # Create a new Contact
      ${contact id}=   Salesforce Insert  Contact
      ...  FirstName=${first name}
      ...  LastName=${last name}

      # Fetch the Contact to be returned
      &{contact} = Salesforce Get  Contact ${contact_id}

Each test case and keyword can have its own settings. However, instead of a ``Settings`` section inside of a test case or keyword, test case or keyword settings are specified with the setting name in square brackets. In the previous example, ``[Setup]`` is a setting for the ``Example of using a custom keyword in a setup step`` test case, and ``[Documentation]`` and ``[Return]`` are settings for the ``Create a test contact`` keyword.

To run this test from the command line:

.. code-block:: console

   $ cci task run robot --suites robot/<ProjectName>/tests/custom_keyword.robot



Use a Resource File
-------------------

Now that you know how to create a custom keyword that is reusable within a test file, you can build a library of custom keywords to be shared project-wide with a resource file.

A resource file is similar to a normal test suite file, except it cannot contain test cases. Typically a resource file is used to define reusable keywords, and as a way to import a common set of libraries.

Let's create a resource file that stores the ``Create a test contact`` custom keyword, which is currently in the ``custom_keyword.robot`` test case defined in `Create Custom Keywords`_. Save this code in a file named ``<ProjectName>.robot`` in the ``robot/<ProjectName>/resources`` folder of your project's repository. Projects often organize their keywords into multiple files, and then use a ``.robot`` file named after the project (``NPSP.robot``, ``SAL.robot``, and so on) to import them. This file can also define keywords directly if the project doesn't have multiple keyword files.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot

   *** Keywords ***
   Create a test contact
      [Documentation]  Create a temporary Contact and return the ID
      [Return]         ${contact id}

      # Generate a name to use for Contact
      ${first name}=   Get fake data  first_name
      ${last name}=    Get fake data  last_name

      # Create a new Contact
      ${contact id}=   Salesforce Insert  Contact
      ...  FirstName=${first name}
      ...  LastName=${last name}

.. note::
    Along with moving the ``Keywords`` section in the ``custom_keyword.robot`` test case to this file, you must also import ``Salesforce.robot``, where the Faker library is defined.

Next, let's modify the ``custom_keyword.robot`` test case. Remove the ``Keywords`` section, and then under ``Settings`` add as many ``Resource`` statements as needed to import keywords from their specific ``.robot`` resource files.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot
   Resource        <ProjectName>/resources/<ProjectName>.robot

   Suite Teardown  Delete session records

   *** Test Cases ***
   Example of using a custom keyword in a setup step
      [Setup]      Create a test contact

      # Get the new Contact and add name to the log
      &{contact}=      Salesforce Get  Contact  ${contact id}
      Log  Contact name: ${contact}[Name]

.. note::
    Variables defined in resource files are accessible to all tests in a suite that imports the resource file.



Simple Browser Test
-------------------

Now that you know how to create objects using the API, you can use those objects in a browser test.

Let's create a Robot test that uses ``Suite Setup`` to call the ``Open test browser`` keyword. Save this code in a file named ``ui.robot`` in the ``robot/<ProjectName>/tests`` folder of your project's repository.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot

   Suite Setup     Open test browser
   Suite Teardown  Delete records and close browser

   *** Test Cases ***
   Take screenshot of landing page
      Capture page screenshot

When the browser opens, the test case takes a screenshot, which can be a useful tool when debugging tests (though it should only be used when necessary since screenshots can take up a lot of disk space). ``Suite Teardown`` then calls the ``Delete records and close browser`` keyword to complete the test. These simple yet foundational steps are essential to effective browser testing with Robot.

.. note::
    Because this test case calls ``Open test browser``, a window appears on your screen while the test runs.

To run this test from the command line:

.. code-block:: console

   $ cci task run robot --suites robot/<ProjectName>/tests/ui.robot

In addition to the normal output files (``log.html``, ``report.html``, ``output.xml``) this test also creates a screenshot in the ``results`` folder. If you open the ``log.html`` file, you can scroll down to see whether each step of the test case passed or failed. Toggle the ``+`` tab of the ``Take screenshot of landing page`` test header to examine the results of the test. Then toggle the ``+`` tab of the ``Capture page screenshot`` keyword to examine the screenshot taken of the landing page.

The Selenium library comes with a keyword for opening the browser. However, CumulusCi comes with its own keyword, `Open Test Browser <https://cumulusci.readthedocs.io/en/stable/Keywords.html#Salesforce.robot.Open%20Test%20Browser>`_, which not only opens the browser but takes care of the details of logging into the org. This keyword uses a variable named ``${BROWSER}``, which can be set from the command line or in the ``cumulusci.yml`` file to specify which browser to use.

Variables can be set in the ``cumulusci.yml`` file, or specified with the ``vars`` option under ``robot`` in the ``tasks`` section. For example, ``${BROWSER}`` defaults to ``chrome`` in Robot, but it can be set to ``firefox``.

.. code-block:: robot
      
   tasks:
      robot:
         options:
         vars:
            - BROWSER:firefox

To set the browser to ``firefox`` from the command line *for a single test run*:
   
.. code-block:: console

   $ cci task run robot --vars BROWSER:firefox


Supported Browsers
^^^^^^^^^^^^^^^^^^

The ``robot`` task supports both Chrome and Firefox browsers, and the "headless" variations of these browsers, ``headlesschrome`` and ``headlessfirefox``. With the headless version, browser tests run without opening a browser window on the display. The tests still use a browser, but you can't see it while the test runs. This variation is most useful when you run a test on a CI server like MetaCI, where there isn't a physical display connected to the server. 

The headless versions of the browsers are specified by prepending "headless" to the browser name. For example, the command line option to specify the headless version of chrome is ``--var BROWSER:headlesschrome``.

.. tip::
    When you run a test in headless mode, you can still capture screenshots of the browser window. The ``Capture Page Screenshot`` keyword becomes an indispensable tool when debugging tests that failed in headless mode.



Combine API Keywords and Browser Tests
--------------------------------------

In Robot, API and browser keywords can be used together, which gives the user options to build more elaborate acceptance tests. 

Let's build upon the original ``create_contact.robot`` test to integrate all the previous configurations covered in this document. Replace the entirety of the ``create_contact.robot`` test case in the ``robot/<ProjectName>/tests`` folder of your project's repository with this code.

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
      [Documentation]  Create a temporary Contact and return the ID
      [Return]         ${contact id}

      # Generate a name to use for Contact
      ${first name}=   Get fake data  first_name
      ${last name}=    Get fake data  last_name

      # Create a new Contact
      ${contact id}=   Salesforce Insert  Contact
      ...  FirstName=${first name}
      ...  LastName=${last name}

The ``create_contact.robot`` test case not only creates a contact, it also opens up the browser to see that the ``Contact`` appears in a list of ``Contacts``, takes a screenshot of the list, then deletes all new records created during the test run, and closes the browser.

To run this test from the command line:

.. code-block:: console

   $ cci task run robot --suites robot/<ProjectName>/tests/create_contact.robot



Run an Entire Suite of Tests
----------------------------

While a single ``.robot`` file is considered to be a test suite, Robot also considers folders to be suites. You can pass a folder to Robot, and Robot runs all tests stored in that folder. So if you've saved the ``create_contact.robot``, ``custom_keyword.robot`` and ``ui.robot`` test cases in your ``tests`` folder, you can run all of the tests in the command line.

.. code-block:: console

   $ cci task run robot --suites robot/<ProjectName>/tests

In the output you can see that all of the tests in the ``tests`` folder have been run.

.. tip:: 
    Test suite folders can also contain nested folders of tests, which makes it easy to organize tests into functional groups. For example, you can store all API tests in a ``tests/api`` folder, and store all UI tests in a ``tests/ui`` folder.

Because running everything in the ``tests`` folder is such common practice, it is the default behavior for the ``robot`` task.

To run an entire suite of tests with the ``robot`` task:

.. code-block:: console

   $ cci task run robot

