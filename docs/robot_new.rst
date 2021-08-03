=======================================
Acceptance Testing with Robot Framework
=======================================

CumulusCI can help automate another important aspect of building packages: acceptance testing. Acceptance testing is the process of testing an application from the user's perspective as the final proof that the product meets its requirements.While there are plenty of testing tools, we're partial to Robot Framework, an acceptance testing framework that you can use with and within CumulusCI to create and run automated acceptance tests for your Salesforce projects.

`Robot Framework <https://robotframework.org/>`_ (or just Robot) is a keyword-driven acceptance testing framework. `*Keyword-driven* <https://robocorp.com/docs/languages-and-frameworks/robot-framework/keywords>`_ means that users can write test cases in an intuitive, human-readable language made up of high-level, reusable keywords (``Open test browser``, ``Delete records and close browser``) rather than in a programming language. 

For example, in this basic Robot test case that creates a new ``Contact`` record, and then examines the record to confirm that the fields listed are correct, you can see how straightforward the keyword syntax is. Even someone brand new to test automation can look at this test and grasp the function of the ``Salesforce Insert``, ``Salesforce Get``, and ``Should be equal`` keywords.

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



The Robot Framework Advantage
-----------------------------

Acceptance testing touches on multiple aspects of an application such as the data model, custom APIs, performance, and the user experience in the browser. Existing tools like Apex and Jest are good for writing unit tests and low-level integration tests. However, it can be difficult to understand the intent of a test, and the features being tested, when the test itself involves multiple lines of code detailing where to fetch data from, and how, and other such implementation details.

Robot addresses these challenges with a few strategies, helping you write high-level acceptance tests for every aspect of an application, often in a single test suite.

* Human-readable, domain-specific test cases: Robot lets you create a language tailored to the domain of testing Salesforce applications (a domain-specific language, or DSL). The DSL consists of reusable keywords that present a complex set of instructions in a human-readable language. The result? Test cases that all project stakeholders can easily understand, such as a product manager, scrum master, documentation teams, and so on—not just the test authors. In the previous example, ``Salesforce Insert``, ``Salesforce Get`` and ``Should be equal`` are all keywords.
* Keyword libraries: Robot organizes keywords into libraries, which provide a simple, effective method to organize and share keywords between tests and projects. CumulusCI comes with a comprehensive standard library of Robot keywords created specifically to anticipate the needs of Salesforce testers. In the previous example, when you define ``Salesforce.robot`` as a resource, it automatically pulls in dozens of Salesforce-specific keywords.
* Streamlined test cases: Keywords allow implementation details to be handled by the test but not explicitly itemized in the test. In the previous example, a new ``Contact`` record is created with the ``Salesforce Insert`` keyword, but we don't see all the steps required to make an API call to create the record, such as getting an access token, creating an API payload, making the API call, and parsing the results.


Custom Tasks
^^^^^^^^^^^^

CumulusCI integrates with Robot via custom tasks, such as:

* ``robot``: Runs one or more Robot tests. This is the most common task.
* ``robot_libdoc``: Runs the `libdoc <http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#library-documentation-tool-libdoc>`_ command, which creates an HTML file defining all the keywords in a library or resource file.
* ``robot_testdoc``: Runs the `testdoc <http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#test-data-documentation-tool-testdoc>`_ command, which creates an HTML file documenting all the tests in a test suite.
* ``robot_lint``: Runs the static analysis tool `rflint <https://github.com/boakley/robotframework-lint/>`_, which can validate Robot tests against a set of rules related to code quality.

Like with any CumulusCi task, you can get documentation and a list of arguments with the ``cci task info`` command. For example, ``cci task info robot`` displays documentation for the ``robot`` task.


Custom Keywords
^^^^^^^^^^^^^^^

CumulusCI provides a set of keywords unique to both Salesforce and CumulusCI for acceptance testing. These keywords can run other tasks, interact with Salesforce applications, call Salesforce APIs, and so on. For a list of all custom keywords provided by CumulusCI, see `Keywords.html <https://cumulusci.readthedocs.io/en/stable/Keywords.html>`_.

.. tip::
    In addition to the keywords that come with CumulusCI, you have the ability to write project-specific keywords. These keywords can be written based on existing keywords, or implemented in Python.



Robot Directory Structure
^^^^^^^^^^^^^^^^^^^^^^^^^

When a project is `initialized <https://cumulusci.readthedocs.io/en/latest/get_started.html#project-initialization>`_ with ``cci project init``, this folder structure is created for Robot tests and resources.

.. code-block:: console

   ProjectName/
   ├── robot
   │   └── ProjectName
   │       ├── doc
   │       ├── resources
   │       ├── results
   │       └── tests

We're going to learn more about using these folders as we work through the examples and exercises in the rest of this documentation.



Write a Sample Robot Test Case
------------------------------

Now that you have a general lay of the land, you're ready to construct a sample test case to see how things come together. Let's revisit the test case that creates a new ``Contact`` record.

#. Run ``cci project init``, which creates a file named ``create_contact.robot``.
#. Save this code in a file named ``new_contact_record.robot`` in the ``robot/<ProjectName>/tests`` folder of your project's repository. 

You can tell this file is a test case because it has a ``.robot`` extension and contains a ``Test Cases`` section.

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

The test case makes two calls to a Salesforce API: one to create the ``Contact`` record, and another to confirm that the record has the correct first and last names.


################UPDATE THIS
The test makes calls to two keywords that communicate with Salesforce via an API.

* ``Salesforce Insert``, which creates the ``Contact`` record.
* ``Salesforce Get``, which 


Syntax
^^^^^^

Here's a quick primer for the Robot syntax in the ``new_contact_record.robot`` test case.

+---------+-------------------+----------------------------------------------------------------------------+
| Symbol  | Name              | Description and Usage                                                      |
+========+====================+============================================================================+
| ``***`` | Section Heading   | A line that begins with one or more asterisks is a section heading. By     |
|         |                   | convention, we use three asterisks on both sides of a heading to designate |
|         |                   | a section heading. Section headings include ``Settings``, ``Test Cases``,  ||         |                   | ``Keywords``, ``Variables``, ``Comments``, and ``Tasks``.                  |
+---------+-------------------+----------------------------------------------------------------------------+
| #       | Hash              | Designates code comments.                                                  |
+---------+-------------------+----------------------------------------------------------------------------+
| ${}     | Variable          | Curly braces surrounding a name designate a variable. The lead $ character |
|         |                   | refers to a single value..                                                 |
|         |                   |                                                                            |
|         |                   | Variable names are case-insensitive. Spaces and underscores are allowed    | 
|         |                   | and are treated the same.                                                  |
+---------+-------------------+----------------------------------------------------------------------------+
| &{}     | Dictionary or Map | Lead ``&`` character refers to a dictionary or map for key-value pairs,    |
|         |                   | such as ``&{contact}``, which in this test has defined values for the keys |
|         |                   | ``FirstName`` and ``LastName``.                                            |
+---------+-------------------+----------------------------------------------------------------------------+
| =       | Assignment        | Equals sign is optional yet convenient for showing that a variable is      | 
|         |                   | assigned a value. Before the equals sign, up to one space is allowed but   |
|         |                   | *not* required. After the equals sign, two spaces are required, but more   |
|         |                   | are allowed to format test cases into readable columns.                    |
+---------+-------------------+----------------------------------------------------------------------------+
| ...     | Ellipses          | Ellipses designate the continuation of a single-line row of code split     | 
|         |                   | over multiple lines for easier readability.                                |
+---------+-------------------+----------------------------------------------------------------------------+
|         | Space             | Two or more spaces separate arguments from the keywords, and arguments     |
|         |                   | from each other. Multiple spaces can be used to align data and to aid in   | |         |                   | readability.                                                               |
+---------+-------------------+----------------------------------------------------------------------------+

For more details on Robot syntax, visit the official `Robot syntax documentation <http://robotframework.org/robotframework/2.9.2/RobotFrameworkUserGuide.html#test-data-syntax>`_.


Settings
^^^^^^^^

The Settings section of the ``.robot`` file sets up the entire test suite. Configurations established under ``Settings`` affect all test cases, such as:

* ``Suite Setup`` and ``Suite Teardown``, which support processes before the test begins and cleanup after the test finishes.
* ``Documentation``, which describes the purpose of the test suite.
* ``Tags``, which lets a user associate individual test cases with a label.
* ``Resource``, which imports keywords from external files.

For example, these are the settings stored inside the ``new_contact_record.robot`` file.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot

The resource ``cumulusci/robotframework/Salesforce.robot`` comes with CumulusCI and automatically inherits useful configuration and keywords for Salesforce testing. The ``Salesforce.robot`` file is the primary method of importing all keywords and variables provided by CumulusCI, so it's best practice for the file to be the first item imported in a test file under ``Settings``. It also imports the `CumulusCI Library <https://cumulusci.readthedocs.io/en/stable/Keywords.html#file-cumulusci.robotframework.CumulusCI>`_, the `Salesforce Library <LINK TODO>`, the third-party `SeleniumLibrary <http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html>`_ for browser testing via Selenium, and these most commonly used Robot libraries.

* `Collections <http://robotframework.org/robotframework/latest/libraries/Collections.html>`_
* `OperatingSystem <http://robotframework.org/robotframework/latest/libraries/OperatingSystem.html>`_
* `String <http://robotframework.org/robotframework/latest/libraries/String.html>`_
* `XML <http://robotframework.org/robotframework/latest/libraries/XML.html>`_
 
CumulusCI also comes bundled with these third-party keyword libraries, which must be explicitly imported by any test suite that needs them.
 
* `RequestsLibrary <https://marketsquare.github.io/robotframework-requests/doc/RequestsLibrary.html>`_  for testing REST APIs. To use ``RequestsLibrary``, explicitly import it under the ``Settings`` section of your Robot test.
* All other libraries (listed in the Standard tab) of the `Robot libraries documentation <https://robotframework.org/#libraries>`_.


Test Cases
^^^^^^^^^^

The ``Test Cases`` section of the ``.robot`` file stores test cases. Each test case gets its own code block, with the test case name as the first line of code, with no indentation. The body of the test case is all the indented text underneath.

For example, these are the test cases stored inside the ``new_contact_record.robot`` file.

.. code-block:: robotframework

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

These keywords are used in the test cases.

* ``Salesforce Insert`` creates a new ``Contact`` record with the arguments it's given for the ``FirstName`` and ``LastName`` fields.
* ``Salesforce Get`` retrieves the requested record, a ``Contact`` record, based on its ID.
* ``Should Be Equal`` compares the arguments to the values of the ``FirstName`` and ``LastName`` fields of the newly created ``Contact`` record.

.. tip::
    Keywords in the test cases are separated from arguments by two or more spaces.


Test Case Output
^^^^^^^^^^^^^^^^

To run this test from the command line:

.. code-block:: console

   $ cci task run robot --suites robot/<ProjectName>/tests/new_contact_record.robot

.. note::
   Make sure to `set a default org <https://cumulusci.readthedocs.io/en/main/scratch_orgs.html#set-a-default-org>`_ first or supply the ``--org`` argument with the command. If you haven't created a scratch org yet, the ``robot`` task creates one for you. 

The output is similar to this.

.. code-block:: console

   $ cci task run robot --suites robot/CumulusCI-Test/new_contact_record.robot

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

Each time Robot runs it creates these output files in the ``results`` folder.
* ``output.xml``, the official source of test results. It's used to generate the ``log.html`` and ``report.html`` files, which each offer distinct views of the data. 
* ``log.html``, which contains a detailed view of test execution, such as statistics on every keyword that is run.
* ``report.html``, which contains a high-level overview of test execution results.

By default these files are written to the ``results`` folder, and will overwrite any existing files by the same name. 


Suite Setup and Teardown
------------------------

Most real-world tests require setup before the test begins (such as opening a browser or creating test data), and cleanup after the test finishes (such as closing the browser or deleting test data). Robot supports setup and teardown at both the suite level (such as opening the browser before the first test, *and* closing the browser after the last test) and the test level (such as opening and closing the browser at the start *and* the end of the test).

If you run the ``new_contact_record.robot`` test case several times, you add a new ``Contact`` record to your scratch org each time it runs. If you have a test that requires a specific number of ``Contact`` records, the test can fail the second time you run it. To maintain the required number, you can add a teardown that deletes any ``Contact`` records created by running the test.

Let's modify the ``new_contact_record.robot`` test case with a ``Suite Teardown`` that deletes the ``Contact`` records created by any tests in the suite.

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
    The ``Salesforce Insert`` keyword keeps track of the IDs of the records created. The ``Delete session records`` keyword deletes those records.

To run this test from the command line:

.. code-block:: console

   $ cci task run robot --suites robot/<ProjectName>/tests/new_contact_record.robot



Generate Fake Data with Faker
-----------------------------

The ``get fake data`` keyword comes with the Faker library that's installed with CumulusCI, and saves you from hard-coding test data for Robot tests. ``Get fake data`` does much more than just return random strings; it generates strings in an appropriate format. You can ask it for a name, address, date, phone number, credit card number, and so on, and get back properly formatted data.

For example, let's modify the ``new_contact_record.robot`` test case to generate a fake name. Because the new ``Contact`` name is randomly generated in this updated example, you can't hard-code an assertion on the name of the created ``Contact`` to verify the name. Instead, for illustrative purposes, this test logs the ``Contact`` name in the test's ``log.html`` file.

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

   $ cci task run robot --suites robot/<ProjectName>/tests/new_contact_record.robot



Create Custom Keywords
----------------------

We mentioned earlier that Robot makes use of a domain-specific language. By creating a collection of reusable custom keywords, we can create this DSL for testing Salesforce apps.

Let's now create a new Robot test that includes a custom keyword called ``Create a test Contact``, which creates a ``Contact`` record. Save this code in a file named ``custom_keyword.robot`` in the ``robot/<ProjectName>/tests`` folder of your project's repository.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot
   Suite Teardown  Delete session records

   *** Test Cases ***
   Example of using a custom keyword in a setup step
      [Setup]      Create a test Contact

      # Get the new Contact and add name to the log
      &{contact}=      Salesforce Get  Contact  ${contact id}
      Log  Contact name: ${contact}[Name]

   *** Keywords ***
   Create a test Contact
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

Each test case and keyword can have its own settings. However, instead of a ``Settings`` section inside of a test case or keyword, test case or keyword settings are specified with the setting name in square brackets. In the previous example, ``[Setup]`` is a setting for the ``Example of using a custom keyword in a setup step`` test case, and ``[Documentation]`` and ``[Return]`` are settings for the ``Create a test Contact`` keyword.

To run this test from the command line:

.. code-block:: console

   $ cci task run robot --suites robot/<ProjectName>/tests/custom_keyword.robot



Create a Resource File
----------------------

Now that you know how to create a custom keyword that is reusable within a test file, you can build a library of custom keywords to be shared project-wide with a resource file.

A resource file is similar to a normal test suite file, except it can't contain test cases. Typically, it defines reusable keywords and imports a common set of libraries..

Let's create a resource file that stores the ``Create a test Contact`` custom keyword, which is currently in the ``custom_keyword.robot`` test case defined in `Create Custom Keywords`_. Save this code in a file named ``<ProjectName>.robot`` in the ``robot/<ProjectName>/resources`` folder of your project's repository. Projects often organize their keywords into multiple files, and then use a ``.robot`` file named after the project (``NPSP.robot``, ``EDA.robot``, and so on) to import them. This file can also define keywords directly if the project doesn't have multiple keyword files.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot

   *** Keywords ***
   Create a test Contact
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
    Along with moving the ``Keywords`` section in the ``custom_keyword.robot`` test case to this file, you must also import ``Salesforce.robot`` as a ``Resource`` because that's where the Faker library is defined.

Next, let's modify the ``custom_keyword.robot`` test case. Remove the ``Keywords`` section, and then under ``Settings`` add as many ``Resource`` statements as needed to import keywords from their specific ``.robot`` resource files.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot
   Resource        <ProjectName>/resources/<ProjectName>.robot

   Suite Teardown  Delete session records

   *** Test Cases ***
   Example of using a custom keyword in a setup step
      [Setup]      Create a test Contact

      # Get the new Contact and add name to the log
      &{contact}=      Salesforce Get  Contact  ${contact id}
      Log  Contact name: ${contact}[Name]

.. note::
    Variables defined in resource files are accessible to all tests in a suite that imports the resource files.



Create a Simple Browser Test
----------------------------

Now that you know how to create records using the API, you can use those records in a browser test.

Let's create a Robot test that uses ``Suite Setup`` to call the ``Open test browser`` keyword. Save this code in a file named ``ui.robot`` in the ``robot/<ProjectName>/tests`` folder of your project's repository.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot

   Suite Setup     Open test browser
   Suite Teardown  Delete records and close browser

   *** Test Cases ***
   Take screenshot of landing page
      Capture page screenshot

When the browser opens, the test case takes a screenshot, which can be a useful tool when debugging tests (a tool used sparingly because screenshots can take up a lot of disk space). ``Suite Teardown`` then calls the ``Delete records and close browser`` keyword to complete the test.

.. note::
    Because this test case calls ``Open test browser``, a browser window appears while the test runs.

To run this test from the command line:

.. code-block:: console

   $ cci task run robot --suites robot/<ProjectName>/tests/ui.robot

In addition to the usual output files (``log.html``, ``report.html``, ``output.xml``), this test also creates a screenshot in the ``results`` folder. If you open ``log.html``, you can see whether each step of the test case passed or failed. Toggle the ``+`` tab of the ``Take screenshot of landing page`` test header to examine the results of the test. Then toggle the ``+`` tab of the ``Capture page screenshot`` keyword to examine the screenshot taken of the landing page.


Open the Browser
^^^^^^^^^^^^^^^^

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

The ``robot`` task supports both Chrome and Firefox browsers, and the headless variations of these browsers, ``headlesschrome`` and ``headlessfirefox``. With the headless version, browser tests run without opening a browser window. The tests still use a browser, but you can't see it while the test runs. This variation is most useful when you run a test on a continuous integration server like MetaCI, where there isn't a physical display connected to the server. 

To specify the headless version of a browser, prepend ``headless`` to the browser name. For example, the command line option to specify the headless version of Chrome is  ``--var BROWSER:headlesschrome``.

.. tip::
    When you run a test in headless mode, you can still capture screenshots of the browser window. The ``Capture Page Screenshot`` keyword is indispensable for debugging tests that failed in headless mode.



Combine API Keywords and Browser Tests
--------------------------------------

In Robot, API and browser keywords can be used together to build more elaborate acceptance tests.

Let's build on the original ``new_contact_record.robot`` test to integrate the previous configurations covered so far. Replace the entirety of the ``new_contact_record.robot`` test case in the ``robot/<ProjectName>/tests`` folder of your project's repository with this code.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot

   Suite Setup     Open test browser
   Suite Teardown  Delete records and close browser

   *** Test Cases ***
   Take screenshot of list of Contacts
      [Setup]  Create a test Contact

      Go to object home  Contact
      Capture page screenshot

   *** Keywords ***
   Create a test Contact
      [Documentation]  Create a temporary Contact and return the ID
      [Return]         ${contact id}

      # Generate a name to use for Contact
      ${first name}=   Get fake data  first_name
      ${last name}=    Get fake data  last_name

      # Create a new Contact
      ${contact id}=   Salesforce Insert  Contact
      ...  FirstName=${first name}
      ...  LastName=${last name}

The ``new_contact_record.robot`` test case not only creates a ``Contact``, it also opens the browser to see that the ``Contact`` appears in a list of ``Contacts``, takes a screenshot of the list, then deletes all new records created during the test run, and closes the browser.

To run this test from the command line:

.. code-block:: console

   $ cci task run robot --suites robot/<ProjectName>/tests/new_contact_record.robot



Run an Entire Suite of Tests
----------------------------

While a single ``.robot`` file is considered to be a test suite, Robot also considers folders to be suites. You can pass a folder to Robot to run all tests stored in that folder. So if you've saved the ``new_contact_record.robot``, ``custom_keyword.robot`` and ``ui.robot`` test cases in your ``tests`` folder, you can run all of the tests in the command line.

.. code-block:: console

   $ cci task run robot --suites robot/<ProjectName>/tests

In the output, you can see that all of the tests in the ``tests`` folder have been run.

.. tip:: 
    Test suite folders can also contain nested folders of tests, which makes it easy to organize tests into functional groups. For example, you can store all API tests in a ``tests/api`` folder, and store all UI tests in a ``tests/ui`` folder.

Because running everything in the ``tests`` folder is such common practice, it's the default behavior for the ``robot`` task.

To run an entire suite of tests with the ``robot`` task:

.. code-block:: console

   $ cci task run robot

