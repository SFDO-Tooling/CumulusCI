===============
Robot Framework
===============

Robot Framework (or simply "robot") is a keyword-driven acceptance testing framework used by CumulusCI. *Keyword-driven* means that test cases are made up of high-level keywords that allow acceptance tests to be written in an intuitive, human-readable language ("Open browser", "Click link", "Insert text") rather than in a programming language. *Acceptance testing* refers to the process of testing an application from the user's perspective as the final proof that the product meets its requirements. 

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
^^^^^^^^^^^^^^^^^
 
CumulusCI's integration with Robot builds automated acceptance test scenarios useful to Salesforce projects, such as:
 
* Browser testing with Selenium
* API-only tests interacting with the Salesforce REST, Bulk, and Tooling APIs
* Complex org automation via CumulusCI
* Combinations of all of the above
 
The ability to create rich, single-file acceptance tests that interact with CumulusCI's project-specific automation, Salesforce's APIs, and the Salesforce UI in a browser is the most exciting feature of the integration with Robot. Robot also makes it easy to automate even complex regression scenarios and tests for edge-case bugs just by writing Robot test suites, and with no need to change project automation in the ``cumulusci.yml`` file.



A More Efficient Robot
----------------------

Because automated acceptance testing is sometimes a secondary concern for development teams, this Robot documentation is written with that in mind. Ahead are neatly explained examples of Robot tests that leverage the features of CumulusCI, each one written as a foundation test to be run during development, not after.

The goal here is to demystify the testing process for everyone who works with CumulusCI, to give a head start on designing essential Robot tests, and to inspire you to build upon the test cases given here to meet the needs of your project. 



Robot Test: Create a New Contact
--------------------------------

Here's a basic Robot test for creating a new Contact object. To follow along, save this code in a file named ``create_contact.robot`` in the ``robot/<ProjectName>/tests`` folder of your project's repository. This file will be the initialization of the ``Create Contact`` test suite, which creates a new contact and then confirms that the contact has the correct first and last names.

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


Syntax
^^^^^^

Hashes (``#``) designate comments in a ``.robot`` file.

Variables are designated by ``{}`` with the variable name placed inside the brackets.

${name} is a string
@{account} is a map, dictionary, or array

In this example, ``contact id`` is the variable name. Variable names are space- and case-insensitive.

``&{contact}`` _________________.

Ellipses (``...``) designate the continuation of a single-line command broken up over several lines for easier reading comprehension.

Spacing is also a handy feature in Robot tests.

.. = need to be discussed as well

.. note::

   Notice how each argument is also separated by two or more spaces for better uniformity. (MORE ON THIS.)


Settings
^^^^^^^^

The Settings section of the ``.robot`` file sets up the entire test suite. By including the resource ``cumulusci/robotframework/Salesforce.robot``, which comes with CumulusCI, we inherit useful configuration and keywords for Salesforce testing automatically.


Test Cases
^^^^^^^^^^

.. Go over with Bryan


Keywords
^^^^^^^^

Keywords are separated by two or more spaces from arguments. In this example, thanks to the ``Resource`` called in the ``Settings`` sections, we use keywords already stored within CumulusCI’s Salesforce library.

* ``Salesforce Insert`` creates a new Contact object to insert inside Contacts, and determines the arguments for ``FirstName`` and ``LastName``.
* ``Salesforce Get`` retrieves the Contact object to be examined, and tests whether or not the object details match the given ``FirstName`` and ``LastName`` arguments. 
* ``Should Be Equal`` comes from Robot’s standard library. It compares the test arguments.



Suite Teardown
--------------

When an object is created via the API, that object continues to live on in the org even after the test dies. That's why it's best practice to delete objects that were created at the end of a test run. This example shows how to do that using ``Suite Teardown``.

This is the previous ``Create Contact`` test case with ``Suite Teardown`` placed under the ``Settings`` section. The ``records`` in the ``delete session records`` call/command/keyword(???) refer to any data records created by the ``Salesforce Insert`` keyword. This makes it possible to create and later clean up temporary data used for a test.

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


.. This might be a good time to show the difference between log and log to console


Create Custom Keywords
----------------------

Because Robot uses domain-specific language, you can create your own custom keywords specific to your project's needs. This example shows how to move the creation of a test ``Contact`` into a keyword, which can then be used as a setup in multiple tests. 

.. This also shows how to document keywords through the [Documentation] test setting. (ADD MORE DETAILS.)

.. We might want to have two simple test cases here, to illustrate that the same keyword can be shared. 

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


.. This might be a good place to dive into the different characters used for variables ($, &, and a few others)




Use a Resource File
-------------------

Now that you know how to create a custom keyword that is reusable within a test file, you can build up a body of custom keywords to be shared project-wide by creating a resource file.

A resource file is similar to a normal test suite file, except there are no tests, only references to your project's personal library of custom keywords.

First, create a new file in robot/<ProjectName>/resources/<ProjectName>.robot. Along with moving the ``Keywords`` section you used in the previous example to this file, you must also import ``Salesforce.robot`` because that is where the Faker library is defined.

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





Simple Browser Test
-------------------

Now that you know how to create objects using the API, let's explore how to use those objects in a browser test.

This example test opens the browser and takes a screenshot, which is important for debugging failures. It is the bare minimum for a browser test, but these foundational steps are essential to effective browser testing with Robot.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot

   *** Test Cases ***
   Open the browser to our org
      Open test browser
      Capture page screenshot
      Close browser

``Open test browser`` comes from the ``Salesforce.robot`` file, and it does so much more than open the browser. It logs the user into their org. It uses the browser defined by the ${BROWSER} variable rather than requiring a test what browser is to be used.

.. note::

   Variables can be set in cumulusci.yml, or on the command line. For example, ${BROWSER} defaults to "chrome" but it can be set to "firefox". To run the test using Firefox, use ``cci task run robot -o vars BROWSER:firefox ...``. 



Suite Setup
-----------

While the previous example shows how to open and close a browser, it doesn’t show the preferred way to do so. Typically one would open the browser in a Suite Setup, and close it in a Suite Teardown. In a previous example we showed how to delete test assets created during the test run with ``Delete session records``. This time we will use Suite Setup to call the ``Open test browser`` keyword and Suite Teardown to call ``Delete records and close browser``.

.. code-block:: robotframework

   *** Settings ***
   Resource        cumulusci/robotframework/Salesforce.robot

   Suite Setup     Open test browser
   Suite Teardown  Delete records and close browser

   *** Test Cases ***
   Take screenshot of landing page
      Capture page screenshot

The keywords in this Robot test are stored inside CumulusCI’s Salesforce library.



Combine API Keywords and Browser Tests
--------------------------------------

In Robot, API and browser keywords can be used together, which gives the user options for building more elaborate acceptance tests. In this example, we build upon the original ``Create Contact`` test by creating a contact, opening up the browser to see that the contact appears in a list of contacts, taking a screenshot of the list, then deleting all new records created during the test run, and closing the browser.

.. reminder: 
   The fake names generated in this test are random. If the user runs this test twice, the screenshot shows different contact names each time.

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

Suite setups and teardowns are designed to call a single keyword. However, the `Run keywords <http://robotframework.org/robotframework/latest/libraries/BuiltIn.html#Run%20Keywords>`_ keyword can run other keywords, which makes it a breeze to call multiple keywords in a single setup or teardown, or anywhere else in the Robot test. For example, the ``Create Contact`` test is simplified further.

.. code-block:: robotframework

   *** Settings ***
   Suite Setup     Run keywords
   ...             Open test browser
   ...             AND  create a test contact

``AND`` must be capitalized in order for ``Run keywords`` to call each keyword. Also, notice how the ``...`` notation can be used to make the code more readable.
