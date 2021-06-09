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

