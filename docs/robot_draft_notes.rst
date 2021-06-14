POSSIBLE EXAMPLE: OPEN APP LAUNCHER


Should we worry about functions vs keywords? So why keywords: HUMAN READABILITY



Robot & CumulusCI
-----------------

Robot Framework provides an abstraction layer for writing automated test scenarios in Python and via text keywords in ``.robot`` files. Since Robot Framework is written in Python (like CumulusCI), and has a robust SeleniumLibrary for automated browser testing, it works well with CumulusCI projects.
 
CumulusCI's integration with Robot Framework builds automated test scenarios useful to Salesforce projects, such as:
 
* Browser testing with Selenium
* API-only tests interacting with the Salesforce REST, Bulk, and Tooling APIs
* Complex org automation via CumulusCI
* Combinations of all of the above
 
The ability to create rich, single-file integration tests that interact with CumulusCI's project-specific automation, Salesforce's APIs, and the Salesforce UI in a browser is the most exciting feature of the integration with Robot Framework. Robot Framework also makes it easy to automate even complex regression scenarios and tests for edge-case bugs, just by writing Robot Framework test suites, and with no need to change project automation in the ``cumulusci.yml`` file.



CumulusCI
---------

&&& Scratch org is a sandbox environment as *temporary* work space for changes in your org.

&&& Continuous integration provide framework to create usable, and therefore testable, Salesforce orgs for a project

&&& Includes Robot Framework

&&& Provides library of specific keywords that Robot recognizes and utilizes for testing a Salesforce application.
   In addition to the libraries that come with Robot Framework itself, CumulusCI comes bundled with additional third-party keyword libraries.
   
   * `SeleniumLibrary <http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html>`_ for browser testing
   * `RequestsLibrary <https://marketsquare.github.io/robotframework-requests/doc/RequestsLibrary.html>`_  for testing REST APIs
   
   SeleniumLibrary is automatically imported when you import ``Salesforce.robot``. To use ``RequestsLibrary``, explicitly import it in the ``Settings`` section of your Robot test.




Example: API Test Automation
============================

&&& Scenario: Automate the creation of an Account record using randomized data and verify that it created successfully
&&& Test: Store in a file named create_account.robot in the folder robot/YOUR_PROJECT_NAME/tests


.. code-block:: robotframework

   *** Settings ***

   Documentation        Tests the creation of a basic Account via the API

   # Load CumulusCI's collection of keywords and relevant libraries
   Resource             cumulusci/robotframework/Salesforce.robot

   *** Test Cases ***

   Single Account via API

      # Generate a fake company name and store as the variable ${name}
      ${name} =        Get fake data      company
   
      # Insert an Account and set the Name field to the fake company name
      ${account_id} =  Salesforce Insert  Account
      ...              Name=${name}

      # Query for the Account by its ID, store as an array named @{account}
      @{account}    =  Salesforce Get     Account  ${account_id}

      Should Be Equal  @{account}[Name]   ${name}


Running the Test
----------------

&&& cci task run robot --org dev -o suites robot/YourProjectName/tests/create_account
&&& open log.htm


Components
----------

&&& File name: names the test suite
   create_account.robot → Create Account test suite

&&& Settings section:
   Load libraries of keywords needed to write the test
   Specify documentation for the test suite

&&& Test Cases



Syntax
------

&&& Keywords separated by two or more spaces from arguments
   Keywords in API Example:
      Get fake data: comes from the Faker library
      Salesforce Insert: comes from CumulusCI’s Salesforce library
      Salesforce Get: comes from CumulusCI’s Salesforce library
      Should Be Equal: comes from robot’s standard library

&&& Lines continued with ... and indentation

&&& Variables
   ${name} is a string
   @{account} is a map, dictionary, or array



Example: Use Suite Teardown to Delete Records
=============================================

Challenge: Each test creates data. Ideally we want to clean up the org after the test.

.. code-block:: robotframework

   *** Settings ***

   Documentation        Tests the creation of a basic Account via the API

   # Load CumulusCI's collection of keywords and relevant libraries
   Resource             cumulusci/robotframework/Salesforce.robot

   Suite Teardown       Delete Records

Run Test and Check Output
-------------------------

&&& cci task run robot --org dev -o suites robot/YourProjectName/tests/create_account

&&& open log.html
   Expand Suite Teardown and you should see the Account Id listed as a deleted object from the Delete Records keyword


Example: Add a Second Test
==========================

Challenge: Create a test that includes a parent account

&&& Create a new library file robot/YourProjectName/resources/YourProjectName.robot
&&& Define a Create Account keyword that returns the Account as a dictionary
&&& Load the library as a Resource entry in the test
&&& Add new test case that uses the keyword



Example: Automated Browser Testing
==================================

&&& Setup:
   Installing Chrome and chromedriver

&&& Steps:
   cci task run robot --org dev
   open log.html







=================================================

12 JUNE 2021 UPDATE

Robot Tutorial examples

Jason and I talked a bit about what we think would be the best first examples, and here’s the direction we thing we could go. This is a reasonable sequence, though it might make more sense to talk about creating keywords before getting too deep in the weeds with faker. 

What a test looks like

The goal is just to introduce the very basics of a robot test. Keep variable use to a minimum, explain how to import cci keywords, explain what a test case looks like and show an example of a cci keyword, and how to clean up data generated during the test. Unlike an earlier example I provided, this does not test any business logic behind the creation of an object, since that’s something that should be done in an apex test and we don’t want to encourage people to do that sort of testing from robot.

Note: I left out the [teardown] step so that it can be addressed in a separate example

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



Removing test artifacts

When we create an object via the API, that object will continue to live on in the org even after the test dies. We have a way to clean up objects which were created during a test run. This example shows how to do that in a suite teardown, we could also do it in a test teardown and describe the difference between the two.


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



Using faker to generate fake data

The goal here is to show that cci provides a way to avoid hard-coding test data. This uses get fake data to generate a name. The Get fake data keyword does much more than just return random strings, it generates strings in an appropriate format. We can ask it for a date, a phone number, a credit card number, and many other things, and the data it returns will be in the proper format. Faker can probably be covered in more depth later

Since the name is going to be random,  we can’t hard-code an assertion on the name of the created contact. Instead, for illustrative purposes this just logs the contact name. This might be a good time to show the difference between log and log to console


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

Creating custom keywords

The current introduction mentions DSL - domain specific languages. The way to create these domain specific languages is through custom keywords. This example shows how we can move the creation of a test account into a keyword which we can then use as a setup in multiple tests. This example also shows how we can document our keywords through the [Documentation] test setting.

We might want to have two simple test cases here, to illustrate that the same keyword can be shared. 

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



This might be a good place to dive into the different characters used for variables ($, &, and a few others)

Using a resource file

Now that we have shown how to create a keyword that is reusable within a test file, we can show how to build up a body of custom keywords that can be shared project-wide

The first step is to create a new file in robot/<project>/resources/<project>.robot (any name will do, this is the convention our teams use). We’ll move the keywords section to this file, but this file also has to import Salesforce.robot since that is where the faker stuff is defined

In other words (and perhaps this is an important point to make): a resource file is just like a normal test suite file, except there are no tests.  


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



The next step is to remove the keywords section from the test file and add in an import statement


*** Settings ***
Resource        cumulusci/robotframework/Salesforce.robot
Resource        yourprojectname/resources/yourprojectname.robot

Suite Teardown  Delete session records

*** Test Cases ***
Example of using a custom keyword in a setup step
    [Setup]      Create a test contact

    # Get the new Contact and add their name to the log
    &{contact}=      Salesforce Get  Contact  ${contact id}
    Log  Contact name: ${contact}[Name]


First browser test

Now that we know how to create objects using the API, we can dive into how to use those objects in a browser test. As a first example we just want to show how to open the browser and take a screenshot, since screenshots are important for debugging failures.

