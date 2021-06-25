===============
Robot Framework
===============

Robot Framework (or simply "robot") is a keyword-driven acceptance testing framework used by CumulusCI. *Keyword-driven* means that test cases are made up of high-level keywords that allow acceptance tests to be written in an intuitive, human-readable language ("Open browser", "Click link", "Insert text") rather than in a programming language. *Acceptance testing* refers to the process of testing an application from the user's perspective as the final proof that the product meets its requirements.

Here's an example of a basic Robot test for creating a new Contact object.

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

.. We're still missing something in this intro. The updated info on tasks fits better two sections down in "Robot & CumulusCI". Meantime, there's no solid segue from introducing this example and moving onto "Why Robot". Discuss with Bryan O. about whether we should include example here. (It knocks the rhythm off the intro, but his point about first example popping up on line 100 is 100% valid.)

This document provides details about CumulusCI's integration with `Robot Framework <http://robotframework.org>`_ for automating tests using CumulusCI, Salesforce APIs, and Selenium. 


Why Robot?
----------

What makes Robot Framework an ideal acceptance testing framework for Salesforce?

* Human readable test cases: Robot uses *domain-specific language*, or DSL, for testing in a browser. A DSL takes a complex set of instructions and presents them in a more simplistic language. In the instance of Robot, instead of writing elaborate code for your test cases, you use basic, digestible keywords that don't require code syntax or functions.
* Test cases use keywords: Robot helps circumvent the actual writing of code (or, more accurately, writing as much code as previously required) by instead relying on reuseable keywords.
* Libraries provide keywords: Salesforce has a comprehensive standard library of Robot keywords created specifically to anticipate the needs of testers.

Because of these features, Robot offers a better experience with acceptance testing than the previous Salesforce testing hierarchy of Apex, JEST and Integration (API & Browser). Here's why:

* Apex is a programming language developed by Salesforce. Although it offers flexibility with building apps from scratch, it was not designed with the goal of making readable acceptance tests.
* JEST is a testing framework written in JavaScript, but it doesn't offer a lot of flexibility in its test cases, instead being used primarily for browser automation, which automates tests to run across any number of browsers to more efficiently find bugs, and to ensure a consistent user experience.
* Integration testing performs complex scenarios that involve multiple components to find possible bugs in between interactions with those components. Traditional integration tests are great from a technical perspective, but they aren't as expressive or as relatable to high-level, user-centric tests as Robot. 



Robot & CumulusCI
-----------------
 
CumulusCI's integration with Robot builds automated acceptance test scenarios useful to Salesforce projects, such as:
 
* Browser testing with Selenium
* API-only tests interacting with the Salesforce REST, Bulk, and Tooling APIs
* Complex org automation via CumulusCI
* Combinations of all of the above
 
The ability to create rich, single-file acceptance tests that interact with CumulusCI's project-specific automation, Salesforce's APIs, and the Salesforce UI in a browser is the most exciting feature of the integration with Robot. Robot also makes it easy to automate even complex regression scenarios and tests for edge-case bugs just by writing Robot test suites, and with no need to change project automation in the ``cumulusci.yml`` file.


Custom Tasks
^^^^^^^^^^^^

CumulusCI integrates Robot via custom tasks. The most common task is named ``robot``, but there are others that also make use of ``robotframework``. Like with any task, you can get documentation and a list of arguments with the ``cci task info`` command. For example, ``cci task info robot_libdoc`` will display documentation for the ``robot_libdoc`` task.

Robot tasks include:

``robot``: Runs one or more robot tests.
``robot_libdoc``: Runs the robotframework `libdoc <http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#library-documentation-tool-libdoc>`_ command.
``robot_testdoc``: Runs the robotframework `testdoc <http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#test-data-documentation-tool-testdoc>`_ command.
more info: 
``robot_lint``: Runs the static analysis tool `rflint <https://github.com/boakley/robotframework-lint/>`_, which is useful for validating Robot tests against a set of rules related to code quality.



``Salesforce.robot`` Libraries
------------------------------

The ``cumulusci/robotframework/Salesforce.robot`` file was designed to be the primary method of importing all keywords and variables provided by CumulusCI, so it's best practice for the file to be the first item imported in a test file. The ``Salesforce.robot`` file automatically imports the `CumulusCI Library`_, the `Salesforce Library`_, and these most commonly used Robot libraries.
 
* `Collections <http://robotframework.org/robotframework/latest/libraries/Collections.html>`_
* `OperatingSystem <http://robotframework.org/robotframework/latest/libraries/OperatingSystem.html>`_
* `String <http://robotframework.org/robotframework/latest/libraries/String.html>`_
* `XML <http://robotframework.org/robotframework/latest/libraries/XML.html>`_
 
In addition to these Robot libraries, CumulusCI comes bundled with these third-party keyword libraries, which must be explicitly imported by any test suite that needs them.
 
* `SeleniumLibrary <http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html>`_ for browser testing via Selenium. ``SeleniumLibrary`` is automatically imported when you import ``Salesforce.robot``.
* `RequestsLibrary <https://marketsquare.github.io/robotframework-requests/doc/RequestsLibrary.html>`_  for testing REST APIs. To use ``RequestsLibrary``, explicitly import it under the ``Settings`` section of your Robot test.
* `All other Robot libraries <https://robotframework.org/#libraries>`_. (Select the ``Standard`` tab.)



.. comment
   THIS IMPORTED VARIABLES SECTION SOUNDS LIKE IT COULD BE A PART OF ADVANCED ROBOT
..   
   Imported Variables
   ^^^^^^^^^^^^^^^^^^
..
   ...AND IF WE DO KEEP THIS IN, WE DEFINITELY NEED TO DISCUSS/BREAKDOWN THIS SECTION. IT'S ALL NEW TO ME.
..
   Here are the variable that are defined when Salesforce.robot is imported.
..
   All of the ones already mentioned in the existing robot.rst file (${BROWSER}, ${DEFAULT_BROWSER_SIZE}, ${IMPLICIT_WAIT},  ${SELENIUM_SPEED}, ${TIMEOUT})
   ${CHROME_BINARY}
   You can use this to define where to find the chrome binary, though it’s rare that you need to use this.
   ${ORG}
   automatically set by CumulusCI to be the name of your org (eg: if you do ‘cci task run robot --org dev’, ${ORG} will be set to “dev”
   ${faker}
   can be used to call faker methods (eg: ${faker.first_name()}). 
   This can be used to define test data in a *** Variables *** section.
   For a description of how to use this variable, see How to create fake test data with faker on confluence.
   We don’t need to go into a lot of detail on this, but a short paragraph might be useful. The way this works is that ${faker} represents an object of the Faker library. Any methods documented for that library can be called using robot frameworks extended variable syntax.
   It might be worth noting that this faker library is the same one used by snowfakery, which is another part of CumulusCI.


CumulusCI Library
^^^^^^^^^^^^^^^^^
 
The CumulusCI Library for Robot provides access to CumulusCI's functionality from inside a Robot test. The library is used to get credentials to a Salesforce org, and to run more complex automation to set up the test environment in the org.

.. MIGHT NEED A FEW MORE DETAILS HERE


.. PAGEOBJECTS LIBRARY TO BE LINKED HERE???


Robot Directory Structure
-------------------------
 
The ``cci project init`` command creates a folder named ``robot`` at the root of your repository. Within that folder is a subfolder for your project Robot files. If your project depends on keywords from other projects, those keywords are stored in the ``robot`` folder under their own project name.
 
.. code-block:: console
 
   MyProject/
   ├── robot
   │   └── MyProject
   │       ├── doc
   │       ├── resources
   │       ├── results
   │       └── tests
 
Also inside the ``robot`` project's folder:
 
* ``doc``: The folder where generated documentation will be placed.
* ``resources``: The folder where you store your own keyword files. You can create `robot keyword files <http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#creating-user-keywords>`_ (``.resource`` or ``.robot``) as well as `keyword libraries <http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#creating-test-libraries>`_ (``.py``). 
   * For keyword files we recommend using the ``.resource`` suffix.
* ``results``: This folder isn't created by `cci project init`. Instead, it is automatically created the first time you run your tests. All generated logs and screenshots of these tests are stored in the ``results`` folder.
* ``tests``: The folder where you store your test suites. You are free to organize this folder however you please, including adding subfolders.
 


Robot Test: Create a New Contact
--------------------------------

Here's the basic Robot test for creating a new Contact object (((previously featured at the beginning of this documentation (-- if we keep the example there)))). To follow along, save this code in a file named ``create_contact.robot`` in the ``robot/<ProjectName>/tests`` folder of your project's repository. This file will be the initialization of the ``Create Contact`` test suite, which creates a new contact and then confirms that the contact has the correct first and last names.

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

.. TO DISCUSS: WHAT IS BEST PRACTICE? TO PRESUME USER IS WORKING FROM CURRENT DIRECTORY, OR PRESUME THAT THEY NEED TO RUN FROM TEST FOLDER BY DEFAULT?
To run this test from the command line, and save  run ``cci task run robot --suites create_contact.robot`` (OR cci task run robot --suites robot/myproject/tests/create_contact.robot?).


Syntax
^^^^^^

Here's a quick primer for the Robot syntax in the ``Create Contact`` test ``.robot`` file.

.. NOT SURE IF TABLE EVEN WORKS BECAUSE MY FORMATTING FOR VSC ON THIS WORK COMPUTER IS *THE WORST*. THAT SAID, I ALSO MADE A BULLET LIST OF THIS TABLE BELOW, WHICH I THINK MIGHT WORK BETTER ANYWAY.

+--------+------+-----------------------------------------------------------------------------------------+
| Symbol | Name               | Description & Usage                                                       |
+========+======+=========================================================================================+
| ***    | Section Heading   | By convention, three stars on both sides of a heading designate a section  |
|        |                   | heading. Popular sections headings include ``Settings``, ``Test Cases``,   |
|        |                   | ``Keywords``, ``Variables``, and ``Tasks``.                                |
+--------+------+-----------------------------------------------------------------------------------------+
| #      | Hash              | Designates comments.                                                       |
+--------+------+-----------------------------------------------------------------------------------------+
| ${}    | Variable          | Curly brackets with a name placed inside designates a variable.            |
|        |                   |                                                                            |
|        |                   | Inside ``{}``, variable names are case-insensitive. Spaces and underscores |
|        |                   | are treated as the same value, and also optional.                          |
|        |                   |                                                                            | 
|        |                   | The leading ``$`` character refers to a single object.                     |
+--------+------+-----------------------------------------------------------------------------------------+
| &{}    | Dictionary or Map | The leading ``&`` character refers to a dictionary or map for              |
|        |                   |   key-value pairs, such as ``&{contact}``, whose keys are ``FirstName``    |
|        |                   |   and ``LastName``.                                |                       |
+--------+------+-----------------------------------------------------------------------------------------+
| =      | Equals            | Equals sign designates the value of a variable. It is allowed up to one    |
|        |                   | space before its placement but allowed more than two after, which is       |
|        |                   | helpful in formatting test cases into readable columns. It is entirely     |
|        |                   | optional.                                                                  |
+--------+------+-----------------------------------------------------------------------------------------+
| ...    | Ellipses          | Ellipses designate the continuation of a single-line command broken up     | 
|        |                   | over several lines for easier readability.                                 |
+--------+------+-----------------------------------------------------------------------------------------+
|        | Space             | Two or more spaces separate arguments from the keyword(s), and arguments   |
|        |                   | from each other. They can also align data for readability.                 |
+--------+------+-----------------------------------------------------------------------------------------+

.. BULLET LIST VERSION

* Section Heading (***): By convention, three stars on both sides of a heading designate a section heading. Popular section headings include ``Settings``, ``Test Cases``, ``Keywords``, ``Variables``, and ``Tasks``.
* Comments (``#``): Hashes designate comments.
* Variables (``{}``): Curly brackets with a name placed inside designates a variable.
   * Inside ``{}``, variable names are case-insensitive. Spaces and underscores are treated as the same value, and also optional.
   * The leading ``$`` character refers to a single object, such as ``${contact id}``. 
   * The leading ``&`` character refers to a dictionary or map for key-value pairs, such as ``&{contact}``, whose keys are ``FirstName`` and ``LastName``.
* Equals (``=``): Equals sign designates the value of a variable. It is allowed up to one space before its placement but allowed more than two after, which is helpful in formatting test cases into readable columns. It is entirely optional. 
* Ellipses (``...``): Ellipses designate the continuation of a single-line command broken up over several lines for easier readability.
* Spaces (`` ``): Two or more spaces separate arguments from the keyword(s), and arguments from each other. They can also align data for readability.

For more details on Robot syntax, visit the official `Robot syntax documentation (http://robotframework.org/robotframework/2.9.2/RobotFrameworkUserGuide.html#test-data-syntax)`_.



Settings
^^^^^^^^

The Settings section of the ``.robot`` file sets up the entire test suite. By including the resource ``cumulusci/robotframework/Salesforce.robot``, which comes with CumulusCI, we inherit useful configuration and keywords for Salesforce testing automatically.

.. THINGS THAT GO IN SETTINGS: SETUPS/TEARDOWNS, DOCUMENTATION, TAGS. (SORRY, STILL NEEDS TO BE WRITTEN. THIS HAS BECOME QUITE THE REFERENCE DOC.)


Test Cases
^^^^^^^^^^

The ``Test Cases`` section of the ``.robot`` file is where test cases are stored. To write a test case, its name is the first line of the code block, and placed in the far left margin of the test code block. All indented text under the test case name is the body of the test case. You can have multiple test cases under the ``Test Case`` section, but each test case must start in the left margin.

The keywords in the test cases are separated by two or more spaces from arguments. In this example, thanks to the ``Resource`` called in the ``Settings`` sections, we use keywords already stored within CumulusCI’s Salesforce library.

* ``Salesforce Insert`` is a keyword that creates a new Contact object to insert inside Contacts, and is being given arguments for the Salesforce field names ``FirstName`` and ``LastName``.
* ``Salesforce Get`` is a keyword that retrieves an object based on its ID, in this example the Contact object. 
* ``Should Be Equal`` is a built-in keyword for comparing objects, in this example the ``FirstName`` and ``LastName`` fields of the Contact object.



Suite Setup/Teardown
--------------------

.. NEED TO REWRITE THIS SECTION TO INCLUDE SETUP
..
When an object is created via the API, that object continues to live on in the org even after the test dies. That's why it's best practice to delete objects that were created at the end of a test run. This example shows how to do that using ``Suite Teardown``.
..
FIX THIS
.. ``Salesforce Insert`` is designed to keep track of the IDs of the objects created, ``Delete session records`` deletes those objects.
This is the previous ``Create Contact`` test case with ``Suite Teardown`` placed under the ``Settings`` section. The ``records`` in the ``delete session records`` keyword refer to any data records created by the ``Salesforce Insert`` keyword. This makes it possible to create and later clean up temporary data used for a test.

.. comment
   WHEN SOMETHING RUNS IN A SETUP/TEARDOWN, IT RUNS WHETHER OR NOT THE TEST PASSES OR FAILS
   SETUP AND TEARDOWN DESIGNED TO ACCEPT A SINGLE KEYWORD AS AN ARGUMENT
   SO TWO CHOICES: CREATE A CUSTOM KEYWORD, OR USE ``RUN KEYWORDS`` TO RUN EXISTING

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




Generate Fake Data with Faker
-----------------------------

Rather than require a user to hard-code test data for Robot tests, CumulusCI makes it simpler to generate the data you need with the ``get fake data`` keyword, which comes from the Faker library already installed with CumulusCI. ``Get fake data`` does much more than just return random strings; it generates strings in an appropriate format. We can ask it for a name, address, date, phone number, credit card number, and so on, and the data it returns will be in the proper format for acceptance testing.

Since the new ``Contact`` name is going to be random in this updated example, we can’t hard-code an assertion on the name of the created contact. Instead, for illustrative purposes, this test simply logs the contact name. 

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


.. STILL NEEDS TO BE WRITTEN:
.. IN THIS TEST LOG MEANS THAT Robot creates a file called log.html in the Results folder. (It's in its own folder to make it easier to find and delete.)  Inside this doc are the results of the keyword tests. LOG TO CONSOLE not only saves the log but logs the data to console.



Create Custom Keywords
----------------------

Because Robot uses domain-specific language, you can create your own custom keywords specific to your project's needs. This example shows how to move the creation of a test ``Contact`` into a keyword, which can then be used as a setup in multiple tests. 

Test cases and keywords has the concept of settings specified by square brackets. This is how Robot knows you're not referring to keyword but rather a test case setting. So test cases can have their own individual setups, teardowns, documentation, returns.

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



Use a Resource File
-------------------

Now that you know how to create a custom keyword that is reusable within a test file, you can build up a body of custom keywords to be shared project-wide by creating a resource file.

A resource file is similar to a normal test suite file, except there are no tests, only references to your project's personal library of custom keywords.

First, create a new file in ``robot/<ProjectName>/resources/<ProjectName>.robot``. Along with moving the ``Keywords`` section you used in the previous example to this file, you must also import ``Salesforce.robot`` because that is where the Faker library is defined.

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

Next, remove the ``Keywords`` section from the ``Create Contact`` test case. Under the ``Settings`` section add an import statement referring to your resource file.

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

This example test uses ``Suite Setup`` to call the ``Open test browser`` keyword. When the browser opens, the test case takes a screenshot, which is important for debugging failures. Suite Teardown then calls the ``Delete records and close browser`` keyword to complete the test. These simple yet foundational steps are essential to effective browser testing with Robot.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot

   Suite Setup     Open test browser
   Suite Teardown  Delete records and close browser

   *** Test Cases ***
   Take screenshot of landing page
      Capture page screenshot

The keywords in this Robot test are stored inside CumulusCI’s Salesforce library. ``Open test browser`` comes from the ``Salesforce.robot`` file, and it does so much more than open the browser. For example, it logs the user into their org, and it uses the browser defined by the ${BROWSER} variable rather than requiring a test what browser is to be used.

.. note::

   Variables can be set in cumulusci.yml, or specified with the ``vars`` option under the robot task. For example, ${BROWSER} defaults to "chrome" but it can be set to "firefox". 
   
   To set the browser to Firefox in the ``cumulusci.yml`` file:
 
      .. code-block:: robot
      
      tasks:
         robot:
            options:
            vars:
               - BROWSER:firefox

   To set the browser to Firefox from the command line *for a single test run*, call ``cci task run robot --vars BROWSER:firefox``. 



Combine API Keywords and Browser Tests
--------------------------------------

In Robot, API and browser keywords can be used together, which gives the user options for building more elaborate acceptance tests. In this example, we build upon the original ``Create Contact`` test by creating a contact, opening up the browser to see that the contact appears in a list of contacts, taking a screenshot of the list, then deleting all new records created during the test run, and closing the browser.

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


Run Keywords
------------

.. INTEGRATE THIS INTO BROWSER TEST???

Suite setups and teardowns are designed to call a single keyword. However, the `Run keywords <http://robotframework.org/robotframework/latest/libraries/BuiltIn.html#Run%20Keywords>`_ keyword can run other keywords, which makes it a breeze to call multiple keywords in a single setup or teardown, or anywhere else in the Robot test. For example, the ``Create Contact`` test is simplified further.

.. code-block:: robotframework

   *** Settings ***
   Suite Setup     Run keywords
   ...             Open test browser
   ...             AND  create a test contact

``AND`` must be capitalized in order for ``Run keywords`` to call each keyword. Also, notice how the ``...`` notation can be used to make the code more readable.


.. FINAL EXAMPLE -- RUN ALL TESTS IN ROBOT FOLDER 
   ADD TAGS TO DIFFERENT FILES W/ API VS UI DESIGNATIONS, LOG WILL SHOW PASS/FAIL