===============
Robot Framework
===============

This document provides details about CumulusCI's integration with `Robot Framework <http://robotframework.org>`_ for automating tests using CumulusCI, Salesforce APIs, and Selenium. 

Robot Framework (or simply "robot") is a keyword-driven acceptance testing framework used by CumulusCI. *Keyword-driven* means that test cases are made up of high-level keywords that allow acceptance tests to be written in an intuitive, human-readable language ("Open browser", "Click link", "Insert text") rather than in a programming language. *Acceptance testing* refers to the process of testing an application from the user's perspective as the final proof that the product meets its requirements.

For example, here's a basic Robot test for creating a new Contact object.

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

.. There's sometime still missing to cap this intro. Discuss with Bryan.


Why Robot?
----------

What makes Robot Framework an ideal acceptance testing framework for Salesforce?

* Human readable test cases: Robot uses *domain-specific language*, or DSL, for testing in a browser. A DSL takes a complex set of instructions and presents them in a human-readable language. In the instance of Robot, instead of writing elaborate code for your test cases, you use basic, digestible keywords that don't require code syntax or functions.
* Test cases use keywords: Robot helps circumvent the actual writing of code (or, more accurately, writing as much code as previously required) by instead relying on reuseable keywords.
* Libraries provide keywords: Salesforce has a comprehensive standard library of Robot keywords created specifically to anticipate the needs of testers.

Existing testing tools like Apex and JEST are good for writing unit tests and low-level integration tests. However, it can be difficult to separate the intent of the test, and the features being tested, from the implementation of the test when using those tools.

Here's how Robot was designed specifically to address problems associated with writing high-level acceptance tests using technology designed for unit and integration tests.

* Tests are written as a sequence of keywords that together form a domain-specific language tailored to testing Salesforce applications. In the previous test example, ``Salesforce Insert Contact``, ``Salesforce Get Contact`` and ``Should be equal`` are all keywords. 
* Keywords allow implementation details to be hidden from the test. In the previous test example, a new contact is created with the ``Salesforce Insert Contact`` keyword without the user seeing all the steps required to make an API call to create a contact.
* Robot organizes keywords into libraries, which provides a simple and effective method of organizing and sharing keywords between tests, and projects. In the previous example, defining ``Salesforce.robot`` as a resource automatically pulls in dozens of Salesforce-specific keywords.
* Robot tests can be easily read and understood by all stakeholders of a project (such as a product manager, scrum master, doc writer, and so on), not solely by the person who wrote the test.

.. DISCUSS BEFORE DELETION (THIS WAS PART OF OUTLINE) 
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

.. DISCUSS WITH BRIAN THE MENTION OF ``robotframework``

CumulusCI integrates Robot via custom tasks. The most common task is named ``robot``, but there are others that also make use of ``robotframework``. Like with any task, you can get documentation and a list of arguments with the ``cci task info`` command. For example, ``cci task info robot_libdoc`` will display documentation for the ``robot_libdoc`` task.

Robot tasks include:

* ``robot``: Runs one or more robot tests.
* ``robot_libdoc``: Runs the robotframework `libdoc <http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#library-documentation-tool-libdoc>`_ command.
* ``robot_testdoc``: Runs the robotframework `testdoc <http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#test-data-documentation-tool-testdoc>`_ command.
* ``robot_lint``: Runs the static analysis tool `rflint <https://github.com/boakley/robotframework-lint/>`_, which is useful for validating Robot tests against a set of rules related to code quality.



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

.. MIGHT NEED A FEW MORE DETAILS HERE. DISCUSS WITH BRYAN.

.. PAGEOBJECTS LIBRARY TO BE LINKED HERE???



Robot Directory Structure
-------------------------

When you initialize a project with ``cci project init``, several folders are created specifically for Robot tests and resources. This is the folder structure.

.. code-block:: console

   ProjectName/
   ├── robot
   │   └── ProjectName
   │       ├── doc
   │       ├── resources
   │       ├── results
   │       └── tests

Though the examples and exercies in this documentation will illustrate the use of most of these folders, see <link to ADVANCE ROBOT doc>_ for more details on each one.


.. CONFIRM BEFORE DELETION
.. The ``cci project init`` command creates a folder named ``robot`` at the root of your repository. Within that folder is a subfolder for your project Robot files. If your project depends on keywords from other projects, those keywords are stored in the ``robot`` folder under their own project name.
 
.. .. code-block:: console
   MyProject/
   ├── robot
   │   └── MyProject
   │       ├── doc
   │       ├── resources
   │       ├── results
   │       └── tests
 
.. Also inside the ``robot`` project's folder:
   * ``doc``: The folder where generated documentation will be placed.
   * ``resources``: The folder where you store your own keyword files. You can create `robot keyword files <http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#creating-user-keywords>`_ (``.resource`` or ``.robot``) as well as `keyword libraries <http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#creating-test-libraries>`_ (``.py``). 
      * For keyword files we recommend using the ``.resource`` suffix.
   * ``results``: This folder isn't created by `cci project init`. Instead, it is automatically created the first time you run your tests. All generated logs and screenshots of these tests are stored in the ``results`` folder.
   * ``tests``: The folder where you store your test suites. You are free to organize this folder however you please, including adding subfolders.
 


Robot Test Breakdown
--------------------

Again, here's the basic Robot test for creating a new Contact object featured at the beginning of this documentation. To follow along, save this code in a file named ``create_contact.robot`` in the ``robot/<ProjectName>/tests`` folder of your project's repository. This file is considered to be a test suite by virtue of having  the ``.robot`` extension with a ``Test Cases`` section. The test itself creates a new contact and then confirms that the contact has the correct first and last names.

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
To run this test from the command line, and save  run ``cci task run robot --suites create_contact.robot`` (OR ``cci task run robot --suites robot/myproject/tests/create_contact.robot``?).

To run this test from the command line, and save(???), run ``cci task run robot --suites create_contact.robot``.

.. GREEN BOX TEXT

.. code-block:: console
   $ cci task run robot --suites robot/CumulusCI-Test/create_contact.robot
   2021-06-25 15:50:35: Creating scratch org with command: sfdx force:org:create -f orgs/dev.json -n --durationdays 7 -a "CumulusCI-Test__dev" -w 120 adminEmail="bryan.oakley@gmail.com" 
   2021-06-25 15:51:13: Successfully created scratch org: 00D2D000000E5oTUAS, username: test-sukm2hyav7el@example.com
   2021-06-25 15:51:13: Generating scratch org user password with command: sfdx force:user:password:generate -u test-sukm2hyav7el@example.com
   2021-06-25 15:51:16: Getting org info from Salesforce CLI for test-sukm2hyav7el@example.com
   2021-06-25 15:51:19: Org info updated, writing to keychain
   2021-06-25 15:51:19: Beginning task: Robot
   2021-06-25 15:51:19: As user: test-sukm2hyav7el@example.com
   2021-06-25 15:51:19: In org: 00D2D000000E5oT
   2021-06-25 15:51:19: 
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



Syntax
^^^^^^

Here's a quick primer for the Robot syntax in the ``Create Contact`` test ``.robot`` file.

+--------+-------------------+----------------------------------------------------------------------------+
| Symbol | Name              | Description & Usage                                                        |
+========+===================+============================================================================+
| ***    | Section Heading   | By convention, three stars on both sides of a heading designate a section  |
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
|        |                   | The leading ``$`` character refers to a single object.                     |
+--------+-------------------+----------------------------------------------------------------------------+
| &{}    | Dictionary or Map | The leading ``&`` character refers to a dictionary or map for              |
|        |                   | key-value pairs, such as ``&{contact}``, whose keys are ``FirstName``      |
|        |                   | and ``LastName``.                                                          |
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

.. BULLET LIST VERSION -- CONFIRM BEFORE DELETION
..
* Section Heading (***): By convention, three stars on both sides of a heading designate a section heading. Popular section headings include ``Settings``, ``Test Cases``, ``Keywords``, ``Variables``, and ``Tasks``.
* Comments (``#``): Hashes designate comments.
* Variables (``{}``): Curly brackets with a name placed inside designates a variable.
   * Inside ``{}``, variable names are case-insensitive. Spaces and underscores are treated as the same value, and also optional.
   * The leading ``$`` character refers to a single object, such as ``${contact id}``. 
   * The leading ``&`` character refers to a dictionary or map for key-value pairs, such as ``&{contact}``, whose keys are ``FirstName`` and ``LastName``.
* Equals (``=``): Equals sign designates the value of a variable. It is allowed up to one space before its placement but allowed more than two after, which is helpful in formatting test cases into readable columns. It is entirely optional. 
* Ellipses (``...``): Ellipses designate the continuation of a single-line command broken up over several lines for easier readability.
* Spaces (`` ``): Two or more spaces separate arguments from the keyword(s), and arguments from each other. They can also align data for readability.

For more details on Robot syntax, visit the official `Robot syntax documentation <http://robotframework.org/robotframework/2.9.2/RobotFrameworkUserGuide.html#test-data-syntax>`_.


Settings
^^^^^^^^

The Settings section of the ``.robot`` file sets up the entire test suite. By including the resource ``cumulusci/robotframework/Salesforce.robot``, which comes with CumulusCI, we inherit useful configuration and keywords for Salesforce testing automatically.

.. THINGS THAT GO IN SETTINGS: SETUPS/TEARDOWNS, DOCUMENTATION, TAGS. (SORRY, STILL NEEDS TO BE WRITTEN. THIS HAS BECOME QUITE THE REFERENCE DOC.)


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

If you run the ``Create Contact`` test example several times, notice that each time it runs you add a new contact to your scratch org. If you have a test that depends on a specific number of contacts, the test could fail the second time you run it. To prevent this, you can create a teardown that will delete any contacts created during the test when the test is run.

In this example, the suite teardown deletes the contacts created by any tests in the suite.

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

Test cases and keywords have the concept of settings specified by square brackets, which means test cases can have their own individual setups, teardowns, documentation, and returns. This is how Robot knows you're not referring to the keyword but rather a specific test case setting.



Use a Resource File
-------------------

Now that you know how to create a custom keyword that is reusable within a test file, you can build up a body of custom keywords to be shared project-wide by creating a resource file.

A resource file is similar to a normal test suite file, except there are no tests, only references to your project's personal library of custom keywords.

First, create a new file in ``robot/<ProjectName>/resources/<ProjectName>.robot``. Along with moving the ``Keywords`` section you used in the previous example to this file, you must also import ``Salesforce.robot``, where the Faker library is defined.

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

This example test uses ``Suite Setup`` to call the ``Open test browser`` keyword. When the browser opens, the test case takes a screenshot, which can be a useful tool when trying to debug your tests (though it should only be used when necessary since screenshots can take up a lot of disk space). Suite Teardown then calls the ``Delete records and close browser`` keyword to complete the test. These simple yet foundational steps are essential to effective browser testing with Robot.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot

   Suite Setup     Open test browser
   Suite Teardown  Delete records and close browser

   *** Test Cases ***
   Take screenshot of landing page
      Capture page screenshot

.. TO DISCUSS WITH BRYAN
Including instructions to have the reader open up log.html and drill down into the test so that they can see how the screenshot is included in the log. You could also mention where the screenshots are stored (same directory as log.html). 

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


Supported Browsers
^^^^^^^^^^^^^^^^^^

CumulusCI provides out-of-the-box support for ``headlesschrome`` and ``headlessfirefox``, which run tests without actually opening a window on the screen. So in the previous example, even when the window isn't displayed, the ``Take screenshot of landing page`` test case still takes screenshots.



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


.. TO DISCUSS WITH BRYAN: FINAL EXAMPLE?? -- RUN ALL TESTS IN ROBOT FOLDER?
   ADD TAGS TO DIFFERENT FILES W/ API VS UI DESIGNATIONS, LOG WILL SHOW PASS/FAIL?
   (OR IS THIS LAST COMBO ABOVE ENOUGH?)