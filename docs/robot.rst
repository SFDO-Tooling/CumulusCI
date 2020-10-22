Automation Using Robot Framework
================================



Introduction to Robot Framework
-------------------------------
This section of documentation includes details about CumulusCI's integration with `Robot Framework <http://robotframework.org>`_ for automating tests using the CumulusCI, Salesforce API's, and Selenium.



Why Robot Framework?
^^^^^^^^^^^^^^^^^^^^
Robot Framework provides an abstraction layer for writing automated test scenarios in Python and via text keywords in .robot files.  Since Robot Framework is written in Python (like CumulusCI) and has a robust SeleniumLibrary for automated browser testing, it was an easy integration providing a lot of power.

CumulusCI's integration with Robot Framework allows building automated test scenarios useful to Salesforce projects:

* Browser testing with Selenium
* API only tests interacting with the Salesforce REST, Bulk, and Tooling API's
* Complex org automation via CumulusCI
* Combinations of all of the above

The ability to create rich, single file integration tests that interact with CumulusCI's project specific automation, Salesforce's APIs, and the Salesforce UI in a browser is the most exciting feature of the integration with Robot Framework.

The integration with Robot Framework adds a new dimension to CumulusCI.  Before, automating the recreation of a test environment for an edge case bug reported in a custom org would have required creating new tasks in cumulusci.yml which pollute the project's task list used by everyone on the project for an obscure scenario needed only for regression testing.  Now, you can create the test scenario in a .robot test file and run it through the standard **robot** task in CumulusCI.  Adding a new test scenario just adds a new file in the repository rather than a new task in CumulusCI.



Included Libraries
^^^^^^^^^^^^^^^^^^
CumulusCI comes bundled with the following additional third-party keyword libraries in addition to the libraries that come with robot framework itself:

* `SeleniumLibrary <http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html>`_ for browser testing
* `RequestsLibrary <https://marketsquare.github.io/robotframework-requests/doc/RequestsLibrary.html>`_  for testing REST APIs

SeleniumLibrary is automatically imported when you import Salesforce.robot. To use RequestsLibrary you need to explicitly import it in the settings section of your robot test.



Example Robot Test
^^^^^^^^^^^^^^^^^^
The following test file placed under **robot/ExampleProject/tests/create_contact.robot** in your project's repository automates the testing of creating a Contact through the Salesforce UI in a browser and via the API.  As an added convenience, it automatically deletes the created Contacts in the Suite Teardown step:

.. code-block:: robotframework

   *** Settings ***

   Resource        cumulusci/robotframework/Salesforce.robot
   Library         cumulusci.robotframework.PageObjects

   Suite Setup     Open Test Browser
   Suite Teardown  Delete Records and Close Browser


   *** Test Cases ***

   Via API
       ${first_name} =       Get fake data  first_name
       ${last_name} =        Get fake data  last_name
       ${contact_id} =       Salesforce Insert  Contact
       ...                     FirstName=${first_name}
       ...                     LastName=${last_name}

       &{contact} =          Salesforce Get  Contact  ${contact_id}
       Validate Contact      ${contact_id}  ${first_name}  ${last_name}

   Via UI
       ${first_name} =       Get fake data  first_name
       ${last_name} =        Get fake data  last_name

       Go to page            Home  Contact
       Click Object Button   New
       Wait for modal        New  Contact

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
       [Documentation]
       ...  Given a contact id, validate that the contact has the
       ...  expected first and last name both through the detail page in
       ...  the UI and via the API.

       # Validate via UI
       Go to page             Detail   Contact  ${contact_id}
       Page Should Contain    ${first_name} ${last_name}

       # Validate via API
       &{contact} =     Salesforce Get  Contact  ${contact_id}
       Should Be Equal  ${first_name}  ${contact}[FirstName]
       Should Be Equal  ${last_name}   ${contact}[LastName]



Settings
*************
The Settings section of the robot file sets up the entire test suite.  By including the Resource cumulusci/robotframework/Salesforce.robot which comes with CumulusCI, we inherit a lot of useful configuration and keywords for Salesforce testing automatically.

The Suite Setup and Suite Teardown are run at the start and end of the entire test suite.  In the example test, we're using the **Open Test Browser** keyword from the Salesforce.robot file to open a test browser.  We're also using the **Delete Records and Close Browser** keyword from Salesforce.robot to automatically delete all records created in the org during the session and close the test browser.



Test Cases
*************
The two test cases test the same operation done through two different paths: the Salesforce REST API and the Salesforce UI in a browser.



Via API
**********
This test case uses the **Get fake data** keyword to generate a first and last name.  It then uses the **Salesforce Insert** keyword from the Salesforce Library (included via Salesforce.robot) to insert a Contact using the same technique for generating test data. Next, it uses **Salesforce Get** to retrieve the Contact's information as a dictionary.

Finally, the test calls the **Validate Contact** keyword explained in the Keywords section below.



Via UI
*********
This test case also uses **Get fake data** for the first and last name, but instead uses the test browser to create a Contact via the Salesforce UI.  Using keywords from the Salesforce Library, it navigates to the Contact home page and clicks the **New** button to open a modal form.  It then uses **Populate Form** to fill in the First Name and Last Name fields (selected by field label) and uses **Click Modal Button** to click the **Save** button and **Wait Until Modal Is Closed** to wait for the modal to close.

At this point, we should be on the record view for the new Contact.  We use the **Get Current Record Id** keyword to parse the Contact's ID from the url in the browser and the **Store Session Record** keyword to register the Contact in the session records list.  The session records list stores the type and id of all records created in the session which is used by the **Delete Records and Close Browser** keyword on Suite Teardown to delete all the records created during the test.  In the **Via API** test, we didn't have to register the record since the **Salesforce Insert** keyword does that for us automatically.  In the **Via UI** test, we created the Contact in the browser and thus need to store its ID manually for it to be deleted.



Keywords
**************
The **Keywords** section allows you to define keywords useful in the context of the current test suite.  This allows you to encapsulate logic you want to reuse in multiple tests.  In this case, we've defined the **Validate Contact** keyword which accepts the contact id, first, and last names as argument and validates the Contact via the UI in a browser and via the API via **Salesforce Get**.  By abstracting out this keyword, we avoid duplication of logic in the test file and ensure that we're validating the same thing in both test scenarios.



Running the Test Suite
******************************
This simple test file can then be run via the **robot** task in CumulusCI:

.. code-block:: console

   $ cd ~/dev/MyProject
   $ cci task run robot -o suites robot/MyProject/tests/create_contact.robot -o vars BROWSER:firefox
   2019-04-26 09:47:24: Getting scratch org info from Salesforce DX
   2019-04-26 09:47:28: Beginning task: Robot
   2019-04-26 09:47:28:        As user: test-leiuvggcviyi@example.com
   2019-04-26 09:47:28:         In org: 00DS0000003ORti
   2019-04-26 09:47:28:
   ==============================================================================
   Create Contact
   ==============================================================================
   Via API                                                               | PASS |
   [ WARN ] Retrying call to method _wait_until_modal_is_closed
   ------------------------------------------------------------------------------
   Via UI                                                                | PASS |
   ------------------------------------------------------------------------------
   Create Contact                                                        | PASS |
   2 critical tests, 2 passed, 0 failed
   2 tests total, 2 passed, 0 failed
   ==============================================================================
   Output:  /Users/boakley/dev/MyProject/robot/MyProject/results/output.xml
   Log:     /Users/boakley/dev/MyProject/robot/MyProject/results/log.html
   Report:  /Users/boakley/dev/MyProject/robot/MyProject/results/report.html


.. note::

   In the example output, the WARN line shows functionality from the
   Salesforce Library which helps handle retry scenarios common to
   testing against Salesforce's Lightning UI.  In this case, it
   automatically retried the wait for the modal window to close after
   creating a contact in a browser.

If you put all of your tests inside that **robot/<project name>/tests** folder you don't have to use the **suite** option. By default the robot task will run all tests in the folder and all subfolders. For example, to run all tests and use the default browser you just have to issue the command `cci task run robot`.



Salesforce.robot
^^^^^^^^^^^^^^^^
Keywords can be defined in a test suite file, but they can also be defined in libraries and resource files. Libraries are written in python, and resource files are written in the robot syntax. Resource files are almost identical to a test file, except that they have no tests and can be imported into other test files. In addition to containing keywords, resource files can also define variables and they can import other libraries.

The file **cumulusci/robotframework/Salesforce.robot** was designed to be the way to import all of the keywords and variables provided by CumulusCI. It should be the first item imported in a test file. It will import the :ref:`salesforce-library-overview` and :ref:`cumulusci-library-overview`, as well as the most commonly used robot libraries
(`Collections <http://robotframework.org/robotframework/latest/libraries/Collections.html>`_,
`OperatingSystem <http://robotframework.org/robotframework/latest/libraries/OperatingSystem.html>`_,
`String <http://robotframework.org/robotframework/latest/libraries/String.html>`_, and
`XML <http://robotframework.org/robotframework/latest/libraries/XML.html>`_)

Variables defined in resource files are accessible to all tests in a suite which imports the resource file. They can be set in your cumulusci.yml file, or specified with the `vars` option to the robot task. When doing so, the variables need to be referenced without the dollar sign and curly braces. Variable names are case-insensitive.

For example, here is how to set the browser to firefox and the default timeout to 20 seconds in a cumulusci.yml file:

.. code-block:: yaml

  tasks:
    robot:
      options:
        vars:
          - BROWSER:firefox
          - TIMEOUT:20 seconds

The same variables can be set from the command line to override the config file for a single test run. This example shows that you can use the lowercase name for convenience:

.. code-block:: console

    $ cci task run robot -o vars browser:firefox,timeout:20


Supported Variables
************************
The following variables defined in **Salesforce.robot** are all used by the ``Open Test Browser`` keyword:

.. list-table::
   :widths:  1 3

   * - ``${BROWSER}``
     - Defines the browser to be used for testing. Supported values are
       ``chrome``, ``firefox``,`` headlesschrome``, and ``headlessfirefox``.
       Default: ``chrome``

   * - ``${DEFAULT_BROWSER_SIZE}``
     - This sets the preferred size of the browser. It is specified in the form of widthxheight, and
       the values are passed to the `Set window size
       <http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html#Set%20Window%20Size>`_ keyword.
       Default: ``1280x1024``

   * - ``${IMPLICIT_WAIT}``
     - This is automatically passed to the `Set Selenium Implicit Wait
       <http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html#Set%20Selenium%20Implicit%20Wait>`_ keyword.
       Default: ``7 seconds``

   * - ``${SELENIUM_SPEED}``
     - This defines a delay added after every selenium command. It is
       automatically passed to the `Set Selenium Speed
       <http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html#Set%20Selenium%20Speed>`_ keyword.
       Default: ``0 seconds``

   * - ``${TIMEOUT}``
     - This sets the default amount of time selenium commands will wait before timing out. It is
       automatically passed to the `Set Selenium Timeout
       <http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html#Set%20Selenium%20Timeout>`_ keyword.
       Default: ``30 seconds``


.. _cumulusci-library-overview:



CumulusCI Library
^^^^^^^^^^^^^^^^^
The CumulusCI Library for Robot Framework provides access to CumulusCI's functionality from inside a robot test.  It is mostly used to get credentials to a Salesforce org and to run more complex automation to set up the test environment in the org.



Logging Into An Org
************************
The **Login Url*** keyword returns a url with an updated OAuth access token to automatically log into the CumulusCI org from CumulusCI's project keychain.



Run Task
************
The **Run Task** keyword is used to run named CumulusCI tasks configured for the project.  These can be any of CumulusCI's built in tasks as well as project specific custom tasks from the project's cumulusci.yml file.

**Run Task** accepts a single argument, the task name.  It optionally accepts task options in the format **option_name=value**.



Run Task Class
*******************
The **Run Task Class** keyword is for use cases where you want to use one of CumulusCI's Python task classes to automate part of a test scenario but don't want to have to map a custom named task at the project level.

**Run Task Class** accepts a single argument, the **class_path** like would be entered into cumulusci.yml such as **cumulusci.tasks.salesforce.Deploy**.  Like **Run Task**, you can also optionally pass task options in the format **option_name=value**.



Full Documentation
**********************
Use the following links to download generated documentation for both
the CumulusCI and Salesforce keywords

* :download:`CumulusCI and Salesforce Keyword Documentation <../docs/robot/Keywords.html>`

.. _salesforce-library-overview:

Salesforce Library
==================

The Salesforce Library provides a set of useful keywords for interacting with Salesforce's Lightning UI and Salesforce's APIs to test Salesforce applications.

UI Keywords
-----------

The goal of the UI keywords in the Salesforce Library is to abstract out common interactions with Salesforce from interactions with your application's UI.  The Salesforce Library itself has an extensive suite of robot tests which are regularly run to alert us to any changes in the base Salesforce UI.  By centralizing these interactions and regularly testing them, the Salesforce Library provides a more stable framework on which to build your product tests.

There are too many keywords relating to UI interactions to cover here.  Please reference the full Salesforce Library documentation below.

Waiting for Lightning UI
^^^^^^^^^^^^^^^^^^^^^^^^

A common challenge when writing end-to-end UI tests is the need to wait for asynchronous actions to complete before proceeding to run the next interaction. The Salesforce Library is aware of the Lightning UI and can handle this waiting automatically. After each click, it will wait for any pending requests to the server to complete. (Manually waiting using a "sleep" or waiting for a particular element to appear may still be necessary after other kinds of interactions and when interacting with pages that don't use the Lightning UI.)

API Keywords
------------

In addition to browser interactions, the Salesforce Library also provides the following keywords for interacting with the Salesforce REST API:

* **Salesforce Collection Insert**: used for bulk creation of objects
  based on a template
* **Salesforce Collection Update**: used for the bulk updating of
  objects
* **Salesforce Delete**: Deletes a record using its type and ID
* **Salesforce Get**: Gets a dictionary of a record from its ID
* **Salesforce Insert**: Inserts a record using its type and field values.  Returns the ID.
* **Salesforce Query**: Runs a simple query using the object type and field=value syntax.  Returns a list of matching record dictionaries.
* **Salesforce Update**: Updates a record using its type, ID, and field=value syntax
* **SOQL Query**: Runs a SOQL query and returns a REST API result dictionary

PageObjects Library
===================

The **PageObjects** library provides support for page objects,
Robot Framework-style. Even though robot is a keyword-driven framework,
we've implemented a way to dynamically load in keywords that are
unique to a page or an object on the page.

With this library, you can define classes which represent page
objects. Each class provides keywords that are unique to a page or a
component. These classes can be imported on demand only for tests
which use these pages or components.


The ``pageobject`` Decorator
----------------------------

Page objects are normal Python classes which use the :code:`pageobject`
decorator provided by CumulusCI. Unlike traditional Robot Framework
keyword libraries, you may define multiple sets of keywords in a
single file.

When you create a page object class, you start by inheriting from one
of the provided base classes. No matter which class your inherit from,
your class gets the following predefined properties:

- **self.object_name** is the name of the object related to the
  class. This is defined via the `object_name` parameter to the
  ``pageobject`` decorator. You should not add the namespace
  prefix in the decorator. This attribute will automatically add the
  prefix from cumulusci.yml when necessary.

- **self.builtin** is a reference to the robot framework
  ``BuiltIn`` library, and can be used to directly call built-in
  keywords. Any built-in keyword can be called by converting the name
  to all lowercase, and replacing all spaces with underscores (eg:
  ``self.builtin.log``, ``self.builtin.get_variable_value``, etc).

- **self.cumulusci** is a reference to the CumulusCI keyword
  library. You can call any keyword in this library by converting the
  name to all lowercase, and replacing all spaces with underscores (eg:
  ``self.cumulusci.get_org_info``, etc).

- **self.salesforce** is a reference to the Salesforce keyword
  library. You can call any keyword in this library by converting the
  name to all lowercase, and replacing all spaces with underscores (eg:
  ``self.salesforce.wait_until_loading_is_complete``, etc).

- **self.selenium** is a reference to SeleniumLibrary. You can call
  any keyword in this library by converting the name to all lowercase,
  and replacing all spaces with underscores (eg:
  ``self.selenim.wait_until_page_contains_element``, etc)


.. _page-object-base-classes:

Page Object Base Classes
------------------------

Presently, cumulusci provides the following base classes,
which should be used for all classes that use the ``pageobject`` decorator:

- ``cumulusci.robotframework.pageobjects.BasePage`` - a generic base
  class used by the other base classes. It can be used when creating
  custom page objects when none of the other base classes make sense.
- ``cumulusci.robotframework.pageobjects.DetailPage`` - a class
  for a page object which represents a detail page
- ``cumulusci.robotframework.pageobjects.HomePage`` - a class for a
  page object which represents a home page
- ``cumulusci.robotframework.pageobjects.ListingPage`` - a class for a
  page object which represents a listing page
- ``cumulusci.robotframework.pageobject.NewModal`` - a class for a
  page object which represents the "new object" modal
- ``cumulusci.robotframework.pageobject.ObjectManagerPage`` - a class
  for interacting with the object manager.

The ``BasePage`` class adds the following keyword to every page object:

- ``Log current page object`` - this keyword is mostly useful
  while debugging tests. It will add to the log information about the
  currently loaded page object.

Example Page Object
-------------------

The following example shows the definition of a page
object for the listing page of a custom object named MyObject__c. It adds a new
keyword named :code:`Click on the row with name`:

.. code-block:: python

   from cumulusci.robotframework.pageobjects import pageobject, ListingPage

   @pageobject(page_type="Listing", object_name="MyObject__c")
   class MyObjectListingPage(ListingPage):

       def click_on_the_row_with_name(self, name):
           self.selenium.click_link('xpath://a[@title="{}"]'.format(name))
           self.salesforce.wait_until_loading_is_complete()

The :code:`pageobject` decorator takes two arguments: :code:`page_type` and
:code:`object_name`. These two arguments are used to identify the page
object (eg: :code:`Go To Page  Listing  Contact`). The values can be
any arbitrary string, but ordinarily should represent standard page
types ("Detail", "Home", "Listing", "New"), and standard object names.


Importing the library into a test
---------------------------------

The **PageObjects** library is somewhat unique in that it is not only a
keyword library, but also the mechanism by which you can import files
which contain page object classes. This is done by providing the paths
to one or more Python files which implement page objects. You may also
import **PageObjects** without passing any files to it in order to take
advantage of some general purpose page objects.

For example, consider the case where you've created two files that
each have one or more page object definitions. For example, lets say
in **robot/MyProject/resources** you have the files **PageObjects.py** and
**MorePageObjects.py**. You can import these page objects into a test
suite like so:

.. code-block:: robotframework

   *** Settings ***
   Library         cumulusci.robotframework.PageObjects
   ...  robot/MyProject/resources/PageObjects.py
   ...  robot/MyProject/resources/MorePageObjects.py


Using Page Objects
------------------

There are two things that must be done in order to use the keywords in
a page object. The first has already been covered, and that is to
import the **PageObjects** library and any custom page object files you
wish to use.

The second thing you must do is either explicitly load the keywords
for a page object, or reference a page object with one of the generic
keywords provided by the **PageObjects** library.

To explicitly load the keywords for a page object you can use the
:code:`load page object` keyword provided by the **PageObjects**
library. Other keywords provided by that library will automatically
import the keywords if they are successful. For example, you can call
:code:`Go To Page` followed by a page object reference, and if that page is
able to be navigated to, its keywords will automatically be loaded.

Page Object Keywords
--------------------

The **PageObjects** library provides the following keywords:

* Current Page Should Be
* Get Page Object
* Go To Page Object
* Load Page Object
* Log Page Object Keywords
* Wait For Modal
* Wait For Page Object

Current Page Should Be
^^^^^^^^^^^^^^^^^^^^^^

Example: :code:`Current Page Should Be  Listing  Contact`

This keyword will attempt to validate that the given page object
represents the current page. Each page object may use its own method
for making the determination, but the built-in page objects all
compare the page location to an expected pattern
(eg: ``.../lightning/o/...``). If the assertion passes, the keywords for
that page object will autoamtically be loaded.

This keyword is useful if you get to a page via a button or some other
form of navigation, in that it allows you to both assert that you are
on the page you think you should be on, and load the keywords for that
page, all with a single statement.

Get Page Object
^^^^^^^^^^^^^^^

Example: :code:`Get page object  Listing  Contact`

This keyword is rarely used in a test. It is mostly useful
to get the reference to a other keyword from another keyword. It is
similar in function to robot's built-in `Get library instance
<http://robotframework.org/robotframework/latest/libraries/BuiltIn.html#Get%20Library%20Instance>`_
keyword.


Go To Page
^^^^^^^^^^

Example: :code:`Go to page  Listing  Contact`

This will attempt to go to the listing page for the Contact object,
and then load the keywords for that page.

Log Page Object Keywords
^^^^^^^^^^^^^^^^^^^^^^^^

Example: :code:`Log Page Object Keywords`

This keyword is primarily a debugging tool. When called it will log
each of the keywords for the current page object.

Load Page Object
^^^^^^^^^^^^^^^^

Example: :code:`Load page object  Listing  Contact`

This will load the page object for the given **page_type** and
**object_name_**. It is useful when you want to use the keywords from a
page object without first navigating to that page (i.e. when you are
already on the page and don't want to navigate away).

Wait For Modal
^^^^^^^^^^^^^^^

Example: :code:`Wait for modal  New  Contact`

This keyword can be used to wait for a modal, such as the one
that pops up when creating a new object. The keyword will return once
a modal appears, and has a title of "New _object_" (eg: "New
Contact").

Wait For Page Object
^^^^^^^^^^^^^^^^^^^^

Example: :code:`Wait for page object  Popup  ActivityManager`

Page objects don't necessarily have to represent entire pages. You can
use Wait for page object to wait for a page object representing a
single element on a page such as a popup window.



Generic Page Objects
--------------------

You do not need to create a page object in order to take advantage of
the new page object keywords. If you use one of the page object
keywords for a page that does not have its own page object, the
**PageObjects** library will try to find a generic page.

For example, if you use :code:`Current page should be  Home  Event` and
there is no page object by that name, a generic :code:`Home` page object
will be loaded, and its object name will be set to :code:`Event`.

Let's say your project has created a custom object named
**Island**. You don't have a home page, but the object does have a
standard listing page. Without creating any page objects, this test
should work by using generic implementations of the Home and Listing
page objects:

.. code-block:: robotframework

   *** Test Cases ***
   Example test which uses generic page objects
       # Go to the custom object home page, which should
       # redirect to the listing page
       Go To Page  Home  Islands

       # Verify that the redirect happened
       Current Page Should Be  Listing  Islands

CumulusCI provides the following generic page objects:

- **Detail** (eg: :code:`Go to page  Detail  Contact  ${contact id}`)
  Detail pages refer to pages with a URL that matches the
  pattern "<host>/lightning/r/<object name>/<object id>/view"
- **Home** (eg: :code:`Go to page  Home  Contact`)
  Home pages refer to pages with a URL that matches the pattern
  "<host>/lightning/o/<object name>/home"
- **Listing** (eg: :code:`Go to  page  Listing  Contact`)
  Listing pages refer to pages with a URL that matches the pattern
  "<host>b/lightning/o/<object name>/list"
- **New** (eg: :code:`Wait for modal  New  Contact`)
  The New page object refers to the modal that pops up
  when creating a new object.

Of course, the real power comes when you create your own page object
class which implements keywords which can be used with your custom
objects.



Keyword Documentation
^^^^^^^^^^^^^^^^^^^^^
Use the following links to download generated documentation for both
the CumulusCI and Salesforce keywords

* :download:`CumulusCI Keyword Documentation <../docs/robot/Keywords.html>`



CumulusCI Robot Tasks
^^^^^^^^^^^^^^^^^^^^^
CumulusCI includes several tasks for working with Robot Framework tests and keyword libraries:

* **robot**: Runs robot test suites.  By default, recursively runs all tests located under the folder **robot/<project name>/tests/**.  Test suites can be overridden via the **suites** keyword and variables inside robot files can be overridden using the **vars** option with the syntax VAR:value (ex: BROWSER:firefox).
* **robot_testdoc**: Generates html documentation of your whole robot test suite and writes to **robot/<project name>/doc/<project_name>.html**.
* **robot_lint**: Performs static analysis of robot files (files with
  .robot and .resource), flagging issues that may reduce the quality of the code.
* **robot_libdoc**:  This task can be wired up to generate library
  documentation if you choose to create a library of robot keywords
  for your project.



Configure the ``libdoc`` Task
***********************************
If you have defined a robot resource file named MyProject.resource and
placed it in the **resources** folder, you can add the following
configuration to your cumulusci.yml file in order to enable the
**robot_libdoc** task to generate documentation:

.. code-block:: yaml

   tasks:
      robot_libdoc:
          description: Generates HTML documentation for the MyProject Robot Framework Keywords
          options:
              path: robot/MyProject/resources/MyProject.resource
              output: robot/MyProject/doc/MyProject_Library.html


You can generate documentation for more than one keyword file or
library by giving a comma-separated list of files for the **path**
option, or by defining path as a list in cumulusci.yml.  In the
following example, documentation will be generated for MyLibrary.py
and MyLibrary.resource:

.. code-block:: yaml

   tasks:
      robot_libdoc:
          description: Generates HTML documentation for the MyProject Robot Framework Keywords
          options:
              path:
                - robot/MyProject/resources/MyProject.resource
                - robot/MyProject/resources/MyProject.py
              output: robot/MyProject/doc/MyProject_Library.html

You can also use basic filesystem wildcards. For example,
to document all robot files in robot/MyProject/resources you could
configure your yaml file like this:

.. code-block:: yaml

   tasks:
      robot_libdoc:
          description: Generates HTML documentation for the MyProject Robot Framework Keywords
          options:
              path: robot/MyProject/resources/*.resource
              output: robot/MyProject/doc/MyProject_Library.html



Robot Directory Structure
^^^^^^^^^^^^^^^^^^^^^^^^^
When you use `cci project init`, it creates a folder named **robot** at the root of your repository. Immediately under that is a folder for your project robot files. If your project depends on keywords from other projects, they would also be in the **robot** folder under their own project name.

.. code-block:: console

   MyProject/
   ├── robot
   │   └── MyProject
   │       ├── doc
   │       ├── resources
   │       ├── results
   │       └── tests

With the project folder inside the **robot** folder are the following additional folders:

* **doc**: the location where generated documentation will be placed.
* **resources**: this folder is where you can put your own keyword files. You can create `robot keyword files <http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#creating-user-keywords>`_ (.resource or .robot) as well as `keyword libraries <http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#creating-test-libraries>`_ (.py). For keyword files we recommend using the **.resource** suffix.
* **results**: this folder isn't created by `cci project init`. Instead, it will automatically be created the first time you run your tests. It will contain all of the generated logs and screenshots.
* **tests**: this is where you should put your test suites. You are free to organize this however you wish, including adding subfolders.



Creating Project Tests
^^^^^^^^^^^^^^^^^^^^^^
Like in the example above, all project tests live in .robot files stored under the **robot/<project name>/tests/** directory in the project.  You can choose how you want to structure the .robot files into directories by just moving the files around.  Directories are treated by robot as a parent test suite so a directory named "standard_objects" would become the "Standard Objects" test suite.

`This document is recommended reading <https://github.com/robotframework/HowToWriteGoodTestCases/blob/master/HowToWriteGoodTestCases.rst>`_.





Robot Framework Tutorial
------------------------
This tutorial will step you through writing your first test, then
enhancing that test with a custom keyword implemented as a page
object. It is not a comprehensive tutorial on using Robot
Framework. For Robot Framework documentation see the
`Robot Framework User Guide <http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html>`_

It is assumed you've worked through the CumulusCI :doc:`tutorial` at least up to the
point where you've called ``cci project init``. It is also assumed
that you've read the :doc:`robotframework` section of this document, which gives
an overview of CumulusCI / Robot Framework integration.



Part 1: Folder Structure
^^^^^^^^^^^^^^^^^^^^^^^^
We recommend that all robot tests, keywords, data, and log and report files live under
a folder named **robot**, at the root of your repository. If you worked
through the CumulusCI :doc:`tutorial`, the following folders will
have been created under **MyProject/robot/MyProject**:

- **doc** - a place to put documentation for your tests
- **resources** - a place to put robot libraries and keyword files that
  are unique to your project
- **results** - a place for robot to write its log and report files
- **tests** - a place for all of your tests.



Part 2: Creating a custom object
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
For this tutorial we're going to use a custom object named
``MyObject`` (e.g. ``MyObject__c``). In addition, we need a custom tab that is associated
with that object.

If you want to run the tests and keywords in this tutorial verbatim,
you will need to go to Setup and create the following:

1. A custom object with the name ``MyObject``.
2. A custom tab associated with this object.



Part 3: Creating and running your first robot test
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The first thing we want to do is create a test that verifies
we can get to the listing page of the custom object. This will
let us know that everything is configured properly.

Open up your favorite editor and create a file named ``MyObject.robot``
in the folder ``robot/MyProject/tests``. Copy and paste the
following into this file, and then save it.

.. code-block:: robotframework

    *** Settings ***
    Resource  cumulusci/robotframework/Salesforce.robot
    Library   cumulusci.robotframework.PageObjects

    Suite Setup     Open test browser
    Suite Teardown  Delete records and close browser

    *** Test Cases ***
    Test the MyObject listing page
        Go to page  Listing  MyObject__c
        Current page should be  Listing  MyObject__c

.. note::

   The above code uses ``Go to page`` and ``Current page should be``
   which accept a page type (``Listing``) and object name
   (``MyObject__c``). Even though we have yet to create that page object,
   the keywords will work by using a generic implementation. Later,
   once we've created the page object, the test will start using our
   implementation.

To run just this test, run the following command at the prompt:

.. code-block:: console

    $ cci task run robot -o suites robot/MyProject/tests/MyObject.robot --org dev

If everything is set up correctly, you should see the output that
looks similar to this:

.. code-block:: console

    $ cci task run robot -o suites robot/MyProject/tests/MyObject.robot --org dev
    2019-05-21 17:29:25: Getting scratch org info from Salesforce DX
    2019-05-21 17:29:29: Beginning task: Robot
    2019-05-21 17:29:29:        As user: test-wftmq9afc3ud@example.com
    2019-05-21 17:29:29:         In org: 00Df0000003cuDx
    2019-05-21 17:29:29:
    ==============================================================================
    MyObject
    ==============================================================================
    Test the MyObject listing page                                        | PASS |
    ------------------------------------------------------------------------------
    MyObject                                                              | PASS |
    1 critical test, 1 passed, 0 failed
    1 test total, 1 passed, 0 failed
    ==============================================================================
    Output:  /Users/boakley/dev/MyProject/robot/MyProject/results/output.xml
    Log:     /Users/boakley/dev/MyProject/robot/MyProject/results/log.html
    Report:  /Users/boakley/dev/MyProject/robot/MyProject/results/report.html



Part 4: Creating a page object
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Most projects are going to need to write custom keywords that are
unique to that project. For example, NPSP has a keyword for filling in
a batch gift entry form, EDA has a keyword with some custom logic for
validating and affiliated contact, and so on.

The best way to create and organize these keywords is to place them in
page object libraries. These libraries contain normal Python classes
and methods which have been decorated with the ``pageobjects``
decorator provided by CumulusCI. By using page objects, you can write
keywords that are unique to a given page, making them easier to find
and easier to manage.



Defining the Class
********************
CumulusCI provides the base classes that are a good starting point for
your page object (see :ref:`page-object-base-classes`). In this case
we're writing a keyword that works on the listing page, so we want our
class to inherit from the ``ListingPage`` class.

.. note::

    Our class also needs to use the ``pageobject`` decorator, so we must
    import that along with the ``ListingPage`` class.

To get started, create a new file named **MyObjectPages.py** in the
folder ``robot/MyProject/resources``. At the top of the new keyword
file, add the following import statement:

.. code-block:: python

    from cumulusci.robotframework.pageobjects import pageobject, ListingPage

Next we can create the class definition by adding the following two
lines:

.. code-block:: python

    @pageobject(page_type="Listing", object_name="MyObject__c")
    class MyObjectListingPage(ListingPage):

The first line registers this class as a page object for a listing page
for the object ``MyObject__c``. The second line begins the class
definition.



Creating the Keyword
*********************
At this point, all we need to do to create the keyword is to create a
method on this object. The method name should be all lowercase, with
underscores instead of spaces. When called from a robot test, the case
is ignored and all spaces are converted to underscores.

In this case we want to create a method named
``click_on_the_row_with_name``. All we want it to do is to find a
link with the given name, click on the link, and then wait for the new
page to load. To make the code more bulletproof, it will use a keyword
from SeleniumLibrary to wait until the page contains the link before
clicking on it. While probably not strictly necessary on this page,
waiting for elements before interacting with them is a good habit to
get into.

Add the following under the class definition:

.. code-block:: python

    def click_on_the_row_with_name(self, name):
        xpath='xpath://a[@title="{}"]'.format(name)
        self.selenium.wait_until_page_contains_element(xpath)
        self.selenium.click_link(xpath)
        self.salesforce.wait_until_loading_is_complete()

Notice that the above code is able to use the built-in properties
``self.selenium`` and ``self.salesforce`` to directly call keywords in
the ``SeleniumLibrary`` and ``Salesforce`` keyword libraries.


Putting it All Together
****************************
After adding all of the above code, our file should now look like
this:

.. code-block:: python

    from cumulusci.robotframework.pageobjects import pageobject, ListingPage


    @pageobject(page_type="Listing", object_name="MyObject__c")
    class MyObjectListingPage(ListingPage):
        def click_on_the_row_with_name(self, name):
            xpath='xpath://a[@title="{}"]'.format(name)
            self.selenium.wait_until_page_contains_element(xpath)
            self.selenium.click_link(xpath)
            self.salesforce.wait_until_loading_is_complete()

We now need to import this page object into our tests. In the first
iteration of the test, we imported
``cumulusci.robotframework.PageObjects``, which provided our test with
keywords such as ``Go to page`` and ``Current page should be``. In
addition to being the source of these keywords, it is also the way to
import page object files into a test case.

To import a file with one or more page objects you need to supply the
path to the page object file as an argument when importing
``PageObjects``. The easiest way is to use robot's continuation
characters ``...`` on a separate line.

Modify the import statements at the top of ``MyObject.robot`` to look
like the following:

.. code-block:: robotframework

    *** Settings ***
    Resource  cumulusci/robotframework/Salesforce.robot
    Library   cumulusci.robotframework.PageObjects
    ...  robot/MyProject/resources/MyObjectPages.py

This will import the page object definitions into the test case, but
the keywords won't be available until the page object is loaded. Page
objects are loaded automatically when you call ``Go to page``, or you
can explicitly load them with ``Load page object``. In both cases, the
first argument is the page type (eg: `Listing`, `Home`, etc) and the
second argument is the object name (eg: ``MyObject__c``).

Our test is already using ``Go to page``, so our keyword should
already be available to us once we've gone to that page.



Part 5: Adding Test Data
^^^^^^^^^^^^^^^^^^^^^^^^
We want to be able to test that when we click on one of our custom
objects on the listing page that it will take us to the detail page
for that object. To do that, our test needs some test data. While that
can be very complicated in a real-world scenario, for simple tests we
can use the Salesforce API to create test data when the suite first
starts up.

To create the data when the suite starts, we can add a ``Suite Setup``
in the settings section of the test. This takes as an argument the
name of a keyword. In our case we're going to create a custom keyword
right in the test to add some test data for us.

It is not necessary to do it in a setup. It could be a step in an
individual test case, for example. However, putting it in the ``Suite
Setup`` guarantees it will run before any tests in the same file are
run.

Open up ``MyObject.robot`` and add the following just before ``***
Test Cases ***``:

.. code-block:: robotframework

    *** Keywords ***
    Create test data
        [Documentation]
        ...  Creates a MyObject record named "Leeroy Jenkins"
        ...  if one doesn't exist

        # Check to see if the record is already in the database,
        # and return if it already exists
        ${status}  ${result}=  Run keyword and ignore error  Salesforce get  MyObject__c  Name=Leeroy Jenkins
        Return from keyword if  '${status}'=='PASS'

        # The record didn't exist, so create it
        Log  creating MyObject object with name 'Leeroy Jenkins'  DEBUG
        Salesforce Insert  MyObject__c  Name=Leeroy Jenkins

We also need to modify our ``Suite Setup`` to call this keyword in
addition to calling the ``Open Test Browser`` keyword. Since ``Suite
Setup`` only accepts a single keyword, we can use the built-in keyword
``Run keywords`` to run more than one keyword in the setup.

Change the suite setup to look like the following, again using robot's
continuation characters to spread the code across multipe rows for
readability.

.. note::

    It is critical that you use all caps for ``AND``, as
    that's the way robot knows where one keyword ends and the next
    begins.

.. code-block:: robotframework

    Suite Setup     Run keywords
    ...  Create test data
    ...  AND  Open test browser

Notice that our ``Suite Teardown`` calls ``Delete records and
close browser``. The _records_ in that keyword refers to any data
records created by ``Salesforce Insert``. This makes it possible to
both create and later clean up temporary data used for a test.

It is important to note that the suite teardown isn't guaranteed to run
if you forcibly kill a running robot test. For that reason, we added a
step in ``Create test data`` to check for an existing record
before adding it. If a previous test was interrupted and the record
already exists, there's no reason to create a new record.



Part 6: Using the New Keyword
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
We are now ready to modify our test to use our new keyword, since we
now have some test data in our database, and the keyword definition in
our page object file.

Once again, edit ``MyObject.robot`` to add the following two
statements at the end of our test:

.. code-block:: robotframework

    Click on the row with name  Leeroy Jenkins
    Current page should be  Detail  MyObject__c

The complete test should now look like this:

.. code-block:: robotframework

    *** Settings ***
    Resource  cumulusci/robotframework/Salesforce.robot
    Library   cumulusci.robotframework.PageObjects
    ...  robot/MyProject/resources/MyObjectPages.py

    Suite Setup     Run keywords
    ...  Create test data
    ...  AND  Open test browser
    Suite Teardown  Delete records and close browser

    *** Keywords ***
    Create test data
        [Documentation]  Creates a MyObject record named "Leeroy Jenkins" if one doesn't exist

        # Check to see if the record is already in the database,
        # and do nothing if it already exists
        ${status}  ${result}=  Run keyword and ignore error  Salesforce get  MyObject__c  Name=Leeroy Jenkins
        Return from keyword if  '${status}'=='PASS'

        # The record didn't exist, so create it
        Log  creating MyObject object with name 'Leeroy Jenkins'  DEBUG
        Salesforce Insert  MyObject__c  Name=Leeroy Jenkins

    *** Test Cases ***
    Test the MyObject listing page
        Go to page  Listing  MyObject__c
        Current page should be  Listing  MyObject__c

        Click on the row with name  Leeroy Jenkins
        Current page should be  Detail  MyObject__c

With everything in place, we should be able to run the test using the
same command as before:

.. code-block:: console

    $ cci task run robot -o suites robot/MyProject/tests/MyObject.robot --org dev
    2019-05-21 22:02:27: Getting scratch org info from Salesforce DX
    2019-05-21 22:02:31: Beginning task: Robot
    2019-05-21 22:02:31:        As user: test-wftmq9afc3ud@example.com
    2019-05-21 22:02:31:         In org: 00Df0000003cuDx
    2019-05-21 22:02:31:
    ==============================================================================
    MyObject
    ==============================================================================
    Test the MyObject listing page                                        | PASS |
    ------------------------------------------------------------------------------
    MyObject                                                              | PASS |
    1 critical test, 1 passed, 0 failed
    1 test total, 1 passed, 0 failed
    ==============================================================================
    Output:  /Users/boakley/dev/MyProject/robot/MyProject/results/output.xml
    Log:     /Users/boakley/dev/MyProject/robot/MyProject/results/log.html
    Report:  /Users/boakley/dev/MyProject/robot/MyProject/results/report.html





Robot Framework Debugger
------------------------
CumulusCI includes a rudimentary debugger which can be enabled by
setting the ``debug`` option of the **robot** task to ``True``. When
the debugger is enabled you can use the ``Breakpoint`` keyword from
the **Salesforce** keyword library to pause execution.

Once the ``Breakpoint`` keyword is encountered you will be given a
prompt from which you can interactively issue commands.

For the following examples we'll be using this simple test:

.. code-block:: robotframework

    *** Settings ***
    Resource  cumulusci/robotframework/Salesforce.robot

    Suite Setup     Open test browser
    Suite Teardown  Close all browsers

    *** Test Cases ***
    Example test case
        log  this is step one
        Breakpoint
        log  this is step two
        log  this is step three



Enabling the Debugger
^^^^^^^^^^^^^^^^^^^^^
To enable the debugger you must set the ``debug`` option to ``True``
for the robot task. **You should never do this in your cumulusci.yml
file.** Doing so could cause tests to block when run on a CI server such
as MetaCI.

Instead, you should set it from the command line when running tests
locally.

For example, assuming you have the example test in a file named
**example.robot**, you can enable the debugger by running the robot
task like this:

.. code-block:: console

    $ cci task run robot -o debug True -o suites example.robot



Setting Breakpoints
^^^^^^^^^^^^^^^^^^^
The Salesforce keyword library includes a keyword named
`Breakpoint`. Normally it does nothing. However, once the debugger is
enabled it will cause the test to pause. You will then be presented
with a prompt where you can interactively enter commands.

.. code-block:: console

    $ cci task run robot -o debug True -o suites example.robot
    cci task run robot -o debug True -o suites example.robot
    2019-10-01 15:29:01: Getting scratch org info from Salesforce DX
    2019-10-01 15:29:05: Beginning task: Robot
    2019-10-01 15:29:05:        As user: test-dp7to8ww6fec@example.com
    2019-10-01 15:29:05:         In org: 00D0R000000ERx6
    2019-10-01 15:29:05:
    ==============================================================================
    Example
    ==============================================================================
    Example test case                                                     .

    :::
    ::: Welcome to rdb, the Robot Framework debugger
    :::

    Type help or ? to list commands.

    > Example.Example test case
    -> <Keyword: cumulusci.robotframework.Salesforce.Breakpoint>
    rdb>

Note: the ``Breakpoint`` keyword has no effect on a test if the ``debug`` option
is not set to ``True``. While we don't encourage you to leave this
keyword in your test cases, it's safe to do so as long as you only
ever set the ``debug`` option when running tests locally.



Getting Help
^^^^^^^^^^^^
Whenever you see the debugger prompt ``rdb>``, you can request help
by typing **help** or **?** and pressing return. You will be given a
list of available commands. To get help with a specific command you
can type **help** followed by the command you want help on.

.. code-block:: console

    rdb> help

    Documented commands (type help <topic>):
    ========================================
    continue  locate_elements  quit            shell  vars
    help      pdb              reset_elements  step   where

    rdb> help vars
    Print the value of all known variables
    rdb>



Examining Variables
^^^^^^^^^^^^^^^^^^^
There are two ways you can examine the current value of a robot
variable. The simplest method is to enter the name of a variable at
the prompt and press return. The debugger will show you the value of
that single variable:

.. code-block:: console

    rdb> ${BROWSER}
    chrome

To see a list of all variables and their values, enter the command
**vars**.

.. code-block:: console

    rdb> vars
    ┌────────────────────────────────────┬──────────────────────────────────────────────────┐
    │ Variable                           │ Value                                            │
    ├────────────────────────────────────┼──────────────────────────────────────────────────┤
    │ ${/}                               │ /                                                │
    ├────────────────────────────────────┼──────────────────────────────────────────────────┤
    │ ${:}                               │ :                                                │
    ├────────────────────────────────────┼──────────────────────────────────────────────────┤
    │ ${BROWSER}                         │ chrome                                           │
    ├────────────────────────────────────┼──────────────────────────────────────────────────┤
    ... <more output> ...



Executing Robot Keywords
^^^^^^^^^^^^^^^^^^^^^^^^

You can execute robot keywords at the prompt by entering the command
**shell** (or the shortcut **!**) followed by the keyword and
arguments just as you would in a test. The following example runs the
SeleniumLibrary keyword
`Get Location <http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html#Get%20Location>`_:

.. code-block:: console

    rdb> shell get location
    status: PASS
    result: https://ability-enterprise-4887-dev-ed.lightning.force.com/lightning/setup/SetupOneHome/home

Notice that the **shell** command will run the keyword and then report
the status of the keyword and display the return value.

Note: just like in a test, you must separate arguments from keywords
by two or more spaces.



Setting Robot Variables
^^^^^^^^^^^^^^^^^^^^^^^

To capture the output of a keyword into a variable, you do it the same
way you would do it in a test: use a variable name, two or more
spaces, then the keyword:

.. code-block:: console

    rdb> ! ${loc}  get location
    status: PASS
    ${loc} was set to https://ability-enterprise-4887-dev-ed.lightning.force.com/lightning/setup/SetupOneHome/home
    rdb> ${loc}
    https://ability-enterprise-4887-dev-ed.lightning.force.com/lightning/setup/SetupOneHome/home

In addition to setting variables from the results of keywords, you can
also set variables with the **shell** command using the built-in keywords
`Set Test Variable <http://robotframework.org/robotframework/latest/libraries/BuiltIn.html#Set%20Test%20Variable>`_,
`Set Suite Variable <http://robotframework.org/robotframework/latest/libraries/BuiltIn.html#Set%20Suite%20Variable>`_, or
`Set Global Variable <http://robotframework.org/robotframework/latest/libraries/BuiltIn.html#Set%20Global%20Variable>`_.

.. code-block:: console

    rdb> ! set test variable  ${message}  hello, world
    status: PASS
    result: None
    rdb> ${message}
    hello, world



Locating Elements on the Web Page
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One of the most powerful features of the debugger is the ability to
locate elements on the screen. This makes it easy to experiment with
xpaths or other types of locators.

In the following example, we want to find all items on the page that
contain the title "Learn More":

.. code-block:: console

    rdb> locate_elements  //button[@title='Learn More']
    Found 1 matches

The elements will be highlighted with a yellow border:

.. image:: images/locate_elements_screenshot.png


To remove the highlighting you can use the debugger command
**reset_elements**



Step Through the Test
^^^^^^^^^^^^^^^^^^^^^
The debugger allows you to step through a test one keyword at a
time. From the rdb prompt, enter the command **step** to continue to
the next step in the test.

.. code-block:: console

    rdb> step
    .

    > Example.Example test case
    -> <Keyword: BuiltIn.Log  this is step two>

The last two lines help to give context. It is showing that you are
currently right before the keyword ``BuiltIn.Log  this is step 2``. To
get a full stack you can issue the command **where**

.. code-block:: console

    rdb> where
    0: -> Example
    1:   -> Example.Example test case
    2:     -> BuiltIn.Log



Continuing or Quitting the Test
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
To let the test continue to the end, or to the next ``Breakpoint``
keyword, issue the command **continue**. To stop execution gracefully
(ie: allow all test and suite teardowns to run), issue the command
**quit**.
