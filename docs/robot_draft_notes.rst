POSSIBLE EXAMPLE: OPEN APP LAUNCHER


Should we worry about functions vs keywords? So why keywords: HUMAN READABILITY




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




Example of the “Run Keywords” keyword

At some point in the discussion of setups and teardowns it might be good to mention how they are designed to call a single keyword, but there is a keyword (Run keywords (http://robotframework.org/robotframework/latest/libraries/BuiltIn.html#Run%20Keywords)) that itself can run other keywords. This makes it extremely easy to call multiple keywords in a single setup or teardown (or anywhere else). 

This example doesn’t necessarily have to follow the previous example, it could be used anywhere after first talking about setups and teardowns. It’s important to emphasize that there must be two or more spaces after “AND”, and that “AND” must be capitalized. 

This also illustrates how using the “...” notation can be used to make the code more readable.


*** Settings ***
Suite Setup     Run keywords
...             Open test browser
...             AND  create a test contact




A More Efficient Robot
----------------------

Because automated acceptance testing is sometimes a secondary concern for development teams, this Robot documentation is written with that in mind. Ahead are neatly explained examples of Robot tests that leverage the features of CumulusCI, each one written as a foundation test to be run during development, not after.

The goal here is to demystify the testing process for everyone who works with CumulusCI, to give a head start on designing essential Robot tests, and to inspire you to build upon the test cases given here to meet the needs of your project. 



   WHEN SOMETHING RUNS IN A SETUP/TEARDOWN, IT RUNS WHETHER OR NOT THE TEST PASSES OR FAILS
   SETUP AND TEARDOWN DESIGNED TO ACCEPT A SINGLE KEYWORD AS AN ARGUMENT
   SO TWO CHOICES: CREATE A CUSTOM KEYWORD, OR USE ``RUN KEYWORDS`` TO RUN EXISTING


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


Advance Project Structure

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





* Section Heading (***): By convention, three stars on both sides of a heading designate a section heading. Popular section headings include ``Settings``, ``Test Cases``, ``Keywords``, ``Variables``, and ``Tasks``.
* Comments (``#``): Hashes designate comments.
* Variables (``{}``): Curly brackets with a name placed inside designates a variable.
   * Inside ``{}``, variable names are case-insensitive. Spaces and underscores are treated as the same value, and also optional.
   * The leading ``$`` character refers to a single object, such as ``${contact id}``. 
   * The leading ``&`` character refers to a dictionary or map for key-value pairs, such as ``&{contact}``, whose keys are ``FirstName`` and ``LastName``.
* Equals (``=``): Equals sign designates the value of a variable. It is allowed up to one space before its placement but allowed more than two after, which is helpful in formatting test cases into readable columns. It is entirely optional. 
* Ellipses (``...``): Ellipses designate the continuation of a single-line command broken up over several lines for easier readability.
* Spaces (`` ``): Two or more spaces separate arguments from the keyword(s), and arguments from each other. They can also align data for readability.


.. DISCUSS BEFORE DELETION (THIS WAS PART OF OUTLINE) 
Because of these features, Robot offers a better experience with acceptance testing than the previous Salesforce testing hierarchy of Apex, JEST and Integration (API & Browser). Here's why:
* Apex is a programming language developed by Salesforce. Although it offers flexibility with building apps from scratch, it was not designed with the goal of making readable acceptance tests.
* JEST is a testing framework written in JavaScript, but it doesn't offer a lot of flexibility in its test cases, instead being used primarily for browser automation, which automates tests to run across any number of browsers to more efficiently find bugs, and to ensure a consistent user experience.
* Integration testing performs complex scenarios that involve multiple components to find possible bugs in between interactions with those components. Traditional integration tests are great from a technical perspective, but they aren't as expressive or as relatable to high-level, user-centric tests as Robot. 




Imported Variables
^^^^^^^^^^^^^^^^^^
.. ...AND IF WE DO KEEP THIS IN, WE DEFINITELY NEED TO DISCUSS/BREAKDOWN THIS SECTION. IT'S ALL NEW TO ME.

Here are the variable that are defined when Salesforce.robot is imported.

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


LOG TO CONSOLE