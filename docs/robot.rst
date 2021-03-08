=============================================
Automate Browser Testing with Robot Framework
=============================================
 
This document provides details about CumulusCI's integration with `Robot Framework <http://robotframework.org>`_ for automating tests using CumulusCI, Salesforce APIs, and Selenium.
 
 
 
Why Robot Framework?
====================
 
Robot Framework provides an abstraction layer for writing automated test scenarios in Python and via text keywords in ``.robot`` files. Since Robot Framework is written in Python (like CumulusCI), and has a robust SeleniumLibrary for automated browser testing, it works well with CumulusCI projects.
 
CumulusCI's integration with Robot Framework builds automated test scenarios useful to Salesforce projects, such as:
 
* Browser testing with Selenium
* API-only tests interacting with the Salesforce REST, Bulk, and Tooling APIs
* Complex org automation via CumulusCI
* Combinations of all of the above
 
The ability to create rich, single-file integration tests that interact with CumulusCI's project-specific automation, Salesforce's APIs, and the Salesforce UI in a browser is the most exciting feature of the integration with Robot Framework. Robot Framework also makes it easy to automate even complex regression scenarios and tests for edge-case bugs, just by writing Robot Framework test suites, and with no need to change project automation in the ``cumulusci.yml`` file.
 
 
 
Included Libraries
==================
 
In addition to the libraries that come with Robot Framework itself, CumulusCI comes bundled with additional third-party keyword libraries.
 
* `SeleniumLibrary <http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html>`_ for browser testing
* `RequestsLibrary <https://marketsquare.github.io/robotframework-requests/doc/RequestsLibrary.html>`_  for testing REST APIs
 
SeleniumLibrary is automatically imported when you import ``Salesforce.robot``. To use ``RequestsLibrary``, explicitly import it in the settings section of your Robot test.
 
 
 
Example Robot Test
==================
 
When placed under ``robot/ExampleProject/tests/create_contact.robot`` in your project's repository, this file automates the test creation of a Contact through the Salesforce UI in a browser and via the API. As an added convenience, it automatically deletes the created Contacts in the Suite Teardown step.
 
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
--------
 
The Settings section of the ``.robot`` file sets up the entire test suite. By including the Resource ``cumulusci/robotframework/Salesforce.robot``, which comes with CumulusCI, we inherit useful configuration and keywords for Salesforce testing automatically.
 
The Suite Setup and Suite Teardown run at the start and end of the entire test suite. In the previous example Robot test, the ``Open Test Browser`` keyword from the ``Salesforce.robot`` file opens a test browser. The ``Delete Records and Close Browser`` keyword automatically deletes all records created in the org during the session and close the test browser.
 
 
 
Test Cases
----------
 
The test cases test the same operation done through different paths: the Salesforce REST API and the Salesforce UI in a browser.
 
 
Via API
^^^^^^^
 
The ``Get fake data`` keyword generates a first and last name. The ``Salesforce Insert`` keyword from the Salesforce Library (included via ``Salesforce.robot``) then inserts a Contact using the same technique for generating test data. Next, ``Salesforce Get`` keyword retrieves the Contact's information as a dictionary.
 
Finally, the test calls the ``Validate Contact`` keyword explained in the Keywords section.
 
 
Via UI
^^^^^^
 
The ``Get fake data`` keyword generates a first and last name, and then the test browser creates a Contact via the Salesforce UI. Using keywords from the Salesforce Library, the test browser navigates to the Contact home page and clicks the ``New`` button to open a modal form. The test browser then uses ``Populate Form`` to fill in the First Name and Last Name fields (selected by field label), ``Click Modal Button`` to click the ``Save`` button, and ``Wait Until Modal Is Closed`` to wait for the modal to close.
 
When the modal closes, you arrive at the record view for the new Contact. The ``Get Current Record Id`` keyword parses the Contact's ID from the URL in the browser, and the ``Store Session Record`` keyword registers the Contact in the session records list. The session records list stores the type and ID of all records created in the session, which is used by the ``Delete Records and Close Browser`` keyword on Suite Teardown to delete every record created during the test. In the ``Via API`` test, there's no need to register the record because the ``Salesforce Insert`` keyword does it automatically. In the ``Via UI`` test, the Contact is created in the browser and, thus, its ID must be stored manually for it to be deleted.
 
 
 
 
Keywords
--------
 
The ``Keywords`` section lets you define keywords useful in the context of the current test suite, and encapsulates logic to reuse in multiple tests. In this case, the ``Validate Contact`` keyword is defined. ``Validate Contact`` accepts the Contact id, first, and last names as argument, and validates the Contact via the UI in a browser as well as via the ``Salesforce Get`` keyword in API. By abstracting out this keyword, you avoid duplication of logic in the test file and ensure that you're validating the same thing in both test scenarios.
 
 
 
Running the Test Suite
----------------------
 
This simple test file can be run with the ``robot`` task in CumulusCI.
 
.. code-block:: console
 
   $ cci task run robot --suites robot/MyProject/tests/create_contact.robot --vars BROWSER:firefox
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
 
.. note:: The WARN line shows functionality from the Salesforce Library that handles retry scenarios common to testing against Salesforce's Lightning UI. In this case, it automatically retried the wait for the modal window to close after creating a Contact in the browser.
 
If you put all of your tests inside the ``robot/<project_name>/tests`` folder, you don't have to use the ``suite`` option. By default, the ``robot`` task runs all tests in the ``tests`` folder and its subfolders.
 
To run all tests using the default browser, run ``cci task run robot``.
 
 
``Salesforce.robot``
====================
 
Keywords are not only defined in test suite files but also in libraries and resource files. Libraries are written in Python, and resource files are written in the Robot syntax. Resource files are almost identical to a test file, except that they have no tests and can be imported into other test files. Resource files contain keywords and can define variables and import other libraries.
 
The ``cumulusci/robotframework/Salesforce.robot`` file was designed to be the primary method of importing all keywords and variables provided by CumulusCI, so it's best practice for the file to be the first item imported in a test file. The ``Salesforce.robot`` file imports the `CumulusCI Library`_, the `Salesforce Library`_, and these most commonly used robot libraries.
 
* `Collections <http://robotframework.org/robotframework/latest/libraries/Collections.html>`_
* `OperatingSystem <http://robotframework.org/robotframework/latest/libraries/OperatingSystem.html>`_
* `String <http://robotframework.org/robotframework/latest/libraries/String.html>`_
* `XML <http://robotframework.org/robotframework/latest/libraries/XML.html>`_
 
Variables defined in resource files are accessible to all tests in a suite that imports the resource file. Variables can be set in the ``cumulusci.yml`` file, or specified with the ``vars`` option under the robot task. Variables need to be referenced without the dollar sign and curly braces. 
 
For example, set the browser to Firefox and the default timeout to 20 seconds in the ``cumulusci.yml`` file:
 
.. code-block:: yaml
 
  tasks:
    robot:
      options:
        vars:
          - BROWSER:firefox
          - TIMEOUT:20 seconds
 
These variables can be set from the command line to override the config file for a single test run.
 
.. code-block:: console
 
    $ cci task run robot --vars browser:firefox,timeout:20
 
.. note:: Variable names are case-insensitive. You can use lowercase letter in the command line for convenience.
 
 
 
Supported Variables
-------------------
 
These variables defined in the ``Salesforce.robot`` file are used by the ``Open Test Browser`` keyword.
 
.. list-table::
   :widths:  1 3
 
   * - ``${BROWSER}``
     - Defines the browser to be used for testing. Supported values are ``chrome``, ``firefox``,`` headlesschrome``, and ``headlessfirefox``.
       Default: ``chrome``
 
   * - ``${DEFAULT_BROWSER_SIZE}``
     - Sets the preferred size of the browser, which is specified in the form of width times height, and the values are passed to the `Set window size <http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html#Set%20Window%20Size>`_ keyword.
       Default: ``1280x1024``
 
   * - ``${IMPLICIT_WAIT}``
     - Automatically passed to the `Set Selenium Implicit Wait <http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html#Set%20Selenium%20Implicit%20Wait>`_ keyword.
       Default: ``7 seconds``
 
   * - ``${SELENIUM_SPEED}``
     - Defines a delay added after every Selenium command, and is automatically passed to the `Set Selenium Speed <http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html#Set%20Selenium%20Speed>`_ keyword.
       Default: ``0 seconds``
 
   * - ``${TIMEOUT}``
     - Sets the default amount of time Selenium commands will wait before timing out, and is automatically passed to the `Set Selenium Timeout <http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html#Set%20Selenium%20Timeout>`_ keyword.
       Default: ``30 seconds``
 
 
 
CumulusCI Library
=================
 
The CumulusCI Library for Robot Framework provides access to CumulusCI's functionality from inside a Robot test. The library is used to get credentials to a Salesforce org, and to run more complex automation to set up the test environment in the org.
 
 
 
Logging Into An Org
-------------------
 
The ``Login Url`` keyword returns a url with an updated OAuth access token to automatically log into the CumulusCI org from CumulusCI's project keychain.
 
 
 
Run Task
--------
 
The ``Run Task`` keyword runs any CumulusCI tasks configured for the project. Tasks run can be any of CumulusCI's standard tasks as well as project-specific custom tasks from the project's ``cumulusci.yml`` file.
 
``Run Task`` accepts a single argument, the task name. The task also accepts task options in the format ``<option_name>=<value>``.
 
 
 
Run Task Class
--------------
 
The ``Run Task Class`` keyword uses a CumulusCI's Python task class to automate part of a test scenario without mapping a custom task at the project level.
 
``Run Task Class`` accepts a single argument, the ``class_path``, as it would be entered into the ``cumulusci.yml`` file, such as ``cumulusci.tasks.salesforce.Deploy``. The task also accepts task options in the format ``<option_name>=<value>``
 
 
 
Set Test Elapsed Time
---------------------
 
The ``Set Test Elapsed Time`` keyword retrieves a computed rather than measured elapsed time for performance tests.
 
For example, when performance testing a Salesforce batch process, you have the option to store the Salesforce-measured elapsed time of the batch process instead of the time measured in the CumulusCI client process.
 
The ``Set Test Elapsed Time`` keyword takes a single optional argument, either a number of seconds or a `Robot time string <https://robotframework.org/robotframework/latest/libraries/DateTime.html#Time%20formats>`_.
 
This keyword automatically adds the ``cci_metric_elapsed_time`` tag to the test case.
 
Performance test times are output in the CCI logs, and are retrieved in MetaCI instead of the "total elapsed time" measured by Robot Framework.
 
 
 
Start and End Perf Time
-----------------------
 
The ``Start Performance Timer`` keyword starts a timer. The ``Stop Performance Timer`` keyword stops the timer and stores the result with ``Set Test Elapsed Time``.
 
 
 
Set Test Metric
---------------
 
The ``Set Test Metric`` keyword retrieves any metric for performance monitoring, such as number of queries, rows processed, CPU usage, and more.
 
 
 
Elapsed Time for Last Record
----------------------------
 
The ``Elapsed Time For Last Record`` keyword queries Salesforce for its recorded log of a job.
 
For example, to query an Apex bulk job:
 
.. code-block:: robot
 
    ${time_in_seconds} =    Elapsed Time For Last Record
    ...             obj_name=AsyncApexJob
    ...             where=ApexClass.Name='BlahBlah'
    ...             start_field=CreatedDate
    ...             end_field=CompletedDate
    ...             order_by=CompletedDate
 
 
 
All Available Keywords
----------------------
 
For a comprehensive list of the keywords available in the CumulusCI and Salesforce keyword libraries, see `CumulusCI and Salesforce Keyword Documentation NEEDS FULL LINK <../docs/robot/Keywords.html>`_.
 
 
 
Salesforce Library
==================
 
The Salesforce Library provides a set of useful keywords for interacting with Salesforce's Lightning UI and Salesforce's APIs to test Salesforce applications.
 
 
 
UI Keywords
-----------
 
The goal of UI keywords in the Salesforce Library is to abstract out common interactions with Salesforce from interactions with your application's UI. The Salesforce Library itself has an extensive suite of Robot tests that run regularly to alert you to any changes in the base Salesforce UI. By centralizing these interactions and regularly testing them, the Salesforce Library provides a more stable framework on which to build your product tests.
 
 
Waiting for Lightning UI
^^^^^^^^^^^^^^^^^^^^^^^^
 
A common challenge when writing end-to-end UI tests is waiting for asynchronous actions to complete before proceeding to run the next interaction. The Salesforce Library is aware of the Lightning UI and can handle waiting automatically. After each click, the Salesforce Library waits for any pending requests to the server to complete. (Manually waiting using "sleep", or waiting for a particular element to appear, can still be necessary after specific interactions, and when interacting with pages that don't use the Lightning UI.)
 
 
 
API Keywords
------------
 
In addition to browser interactions, the Salesforce Library also provides keywords for interacting with the Salesforce REST API.
 
* ``Salesforce Collection Insert``: Creates a collection of objects based on a template.
* ``Salesforce Collection Update``: Updates a collection of objects.
* ``Salesforce Delete``: Deletes a record using its type and ID.
* ``Salesforce Get``: Gets a dictionary of a record from its ID.
* ``Salesforce Insert``: Inserts a record using its type and field values. Returns the ID.
* ``Salesforce Query``: Runs a simple query using the ``object type`` and ``<field_name=value>`` syntax.  Returns a list of matching record dictionaries.
* ``Salesforce Update``: Updates a record using its type, ID, and ``<field_name=value>`` syntax.
* ``SOQL Query``: Runs a SOQL query and returns a REST API result dictionary.
 
 
 
PageObjects Library
===================
 
The ``PageObjects`` library provides support for page objects, Robot Framework-style. Even though Robot is a keyword-driven framework, it's also possible to dynamically load in keywords unique to a page or an object on the page.
 
With the ``PageObjects`` library, you can define classes that represent page objects. Each class provides keywords that are unique to a page or a component. These classes can be imported on demand only for tests that use these pages or components.
 
 
 
The ``pageobject`` Decorator
----------------------------
 
Page objects are normal Python classes that use the ``pageobject`` decorator provided by CumulusCI. Unlike traditional Robot Framework keyword libraries, you can define multiple sets of keywords in a single file.
 
To create a page object class, start by inheriting from one of the provided base classes. No matter which class you inherit from, your page object class gets these predefined properties.
 
* ``self.object_name``: The name of the object related to the class. This is defined via the ``object_name`` parameter to the ``pageobject`` decorator. Do not add the namespace prefix in the decorator. This attribute will automatically add the prefix from the ``cumulusci.yml`` file when necessary.
* ``self.builtin``: A reference to the Robot Framework ``BuiltIn`` library that can be used to directly call built-in keywords. Any built-in keyword can be called by converting the name to all lowercase, and replacing all spaces with underscores (such as ``self.builtin.log`` and ``self.builtin.get_variable_value``).
* ``self.cumulusci``: A reference to the CumulusCI keyword library. Call any keyword in this library by converting the name to all lowercase, and replacing all spaces with underscores (such as ``self.cumulusci.get_org_info``).
* ``self.salesforce``: A reference to the Salesforce keyword library. Call any keyword in this library by converting the name to all lowercase, and replacing all spaces with underscores (such as ``self.salesforce.wait_until_loading_is_complete``).
* ``self.selenium``: A reference to SeleniumLibrary. Call any keyword in this library by converting the name to all lowercase, and replacing all spaces with underscores (such as ``self.selenim.wait_until_page_contains_element``).
 
 
 
Page Object Base Classes
------------------------
 
Presently, CumulusCI provides the following base classes, which should be used for all classes that use the ``pageobject`` decorator:
 
* ``cumulusci.robotframework.pageobjects.BasePage``: A generic base class used by the other base classes. Use the ``BasePage`` class for creating custom page objects when none of the other base classes make sense.
    * The ``BasePage`` adds the ``Log current page object`` keyword to every page object. This keyword is most useful when debugging tests. It will add to the log information about the currently loaded page object.
* ``cumulusci.robotframework.pageobjects.DetailPage``: A class for a page object that represents a detail page.
* ``cumulusci.robotframework.pageobjects.HomePage``: A class for a page object that represents a home page.
* ``cumulusci.robotframework.pageobjects.ListingPage``: A class for a page object that represents a listing page.
* ``cumulusci.robotframework.pageobject.NewModal``: A class for a page object that represents the "new object" modal.
* ``cumulusci.robotframework.pageobject.ObjectManagerPage``: A class for interacting with the object manager.
 
 
 
Example Page Object
-------------------
 
This example shows the definition of a page object for the listing page of custom object ``MyObject__c`` wherein a new custom keyword, ``Click on the row with name``, is added.
 
.. code-block:: python
 
   from cumulusci.robotframework.pageobjects import pageobject, ListingPage
 
   @pageobject(page_type="Listing", object_name="MyObject__c")
   class MyObjectListingPage(ListingPage):
 
       def click_on_the_row_with_name(self, name):
           self.selenium.click_link('xpath://a[@title="{}"]'.format(name))
           self.salesforce.wait_until_loading_is_complete()
 
The ``pageobject`` decorator takes two arguments: ``page_type`` and ``object_name``. These two arguments are used to identify the page object (`Go to page  Listing  Contact`_). The values can be any arbitrary string, but ordinarily should represent standard page types (such as "Detail", "Home", "Listing", or "New") and standard object names.
 
 
Importing the Library Into a Test
---------------------------------
 
The ``PageObjects`` library is not only a keyword library, but also the mechanism to import files that contain page object classes. You can import these files by providing the paths to one or more Python files that implement page objects. You can also import ``PageObjects`` without passing any files to it to take advantage of general purpose page objects.
 
For example, consider a case where you create two files that each have one or more page object definitions: ``PageObjects.py`` and ``MorePageObjects.py``, both located in the ``robot/MyProject/resources`` folder. You can import these page objects from these files into a test suite.
 
.. code-block:: robotframework
 
   *** Settings ***
   Library         cumulusci.robotframework.PageObjects
   ...  robot/MyProject/resources/PageObjects.py
   ...  robot/MyProject/resources/MorePageObjects.py
 
 
 
Using Page Objects
------------------
 
To use the keywords in a page object:
 
As mentioned in the previous section, first import the ``PageObjects`` library and any custom page object files you wish to use.
 
Next, either explicitly load the keywords for a page object, or reference a page object with one of the generic `page object keywords`_ provided by the ``PageObjects`` library.
 
To explicitly load the keywords for a page object, use the ``Load Page Object`` keyword provided by the ``PageObjects`` library. If successful, the ``PageObjects`` library will automatically import the keywords. 
 
For example, call the ``Go To Page`` keyword followed by a page object reference. If the keyword (or page object reference?) navigates you to the proper page, its keywords will automatically be loaded.
 
 
 
Page Object Keywords
--------------------
 
The ``PageObjects`` library provides these keywords.
 
* Current Page Should Be
* Get Page Object
* Go To Page Object
* Load Page Object
* Log Page Object Keywords
* Wait For Modal
* Wait For Page Object
 
 
Current Page Should Be
^^^^^^^^^^^^^^^^^^^^^^
 
Example: ``Current Page Should Be Listing Contact``
 
This keyword attempts to validate that the given page object represents the current page. Each page object may use its own method for making the determination, but the built-in page objects all compare the page location to an expected pattern (such as ``.../lightning/o/...``). If the assertion passes, the keywords for that page object automatically load.
 
This keyword is useful if you get to a page via a button or some other form of navigation because it lets you assert that you are on the page you think you should be on, and load the keywords for that page, with a single statement.
 
 
Get Page Object
^^^^^^^^^^^^^^^
 
Example: ``Get page object  Listing  Contact``
 
This keyword is most often used to get the reference to a keyword from another keyword. It is similar in function to robot's built-in `Get Library Instance <http://robotframework.org/robotframework/latest/libraries/BuiltIn.html#Get%20Library%20Instance>`_ keyword. It is rarely used in a test.
 
 
Go To Page
^^^^^^^^^^
 
Example: ``Go to page  Listing  Contact``
 
This keyword attempts to go to the listing page for the Contact object, and then load the keywords for that page.
 
 
Log Page Object Keywords
^^^^^^^^^^^^^^^^^^^^^^^^
 
Example: ``Log Page Object Keywords``
 
This keyword is primarily used as a debugging tool. When called, it will log each of the keywords for the current page object.
 
 
Load Page Object
^^^^^^^^^^^^^^^^
 
Example: ``Load page object  Listing  Contact``
 
This keyword loads the page object for the given ``page_type`` and ``object_name``. It is useful when you want to use keywords from a page object without first navigating to that page (for example, when you are already on the page and don't want to navigate away).
 
 
Wait for Modal
^^^^^^^^^^^^^^^
 
Example: ``Wait for modal  New  Contact``
 
This keyword can be used to wait for a modal, such as the one that pops up when creating a new object. The keyword returns once a modal appears, and has a title of ``New <object_name>`` (such as "New Contact").
 
 
Wait for Page Object
^^^^^^^^^^^^^^^^^^^^
 
Example: ``Wait for page object  Popup  ActivityManager``
 
Page objects don't have to represent entire pages. You can use the ``Wait for page object`` keyword to wait for a page object representing a single element on a page, such as a popup window.
 
 
 
Generic Page Objects
--------------------
 
You don't need to create a page object in order to take advantage of page object keywords. If you use one of the page object keywords for a page that does not have its own page object, the ``PageObjects`` library attempts to find a generic page.
 
For example, if you use ``Current page should be  Home  Event`` and there is no page object by that name, a generic ``Home`` page object will be loaded, and its object name will be set to ``Event``.
 
Or let's say your project has created a custom object named ``Island``. You don't have a home page, but the object does have a standard listing page. Without creating any page objects, this test works by using generic implementations of the ``Home`` and ``Listing`` page objects:
 
.. code-block:: robotframework
 
   *** Test Cases ***
   Example test which uses generic page objects
       # Go to the custom object home page, which should
       # redirect to the listing page
       Go To Page  Home  Islands
 
       # Verify that the redirect happened
       Current Page Should Be  Listing  Islands
 
CumulusCI provides these generic page objects.
 
 
``Detail``
^^^^^^^^^^
 
Example: ``Go to page  Detail  Contact  ${contact id}``
 
Detail pages refer to pages with a URL that matches the pattern ``<host>/lightning/r/<object name>/<object id>/view``.
 
 
``Home``
^^^^^^^^
 
Example: ``Go to page  Home  Contact``
 
Home pages refer to pages with a URL that matches the pattern "<host>/lightning/o/<object name>/home"
 
 
``Listing``
^^^^^^^^^^^
 
Example: ``Go to  page  Listing  Contact``
 
Listing pages refer to pages with a URL that matches the pattern "<host>b/lightning/o/<object name>/list"
 
 
``New``
^^^^^^^
 
Example: ``Wait for modal  New  Contact``
 
The New page object refers to the modal that pops up when creating a new object.
 
Of course, the real power comes when you create your own page object class that implements keywords that can be used with your custom objects.
 
 
 
CumulusCI Robot Tasks
=====================
 
CumulusCI includes several tasks for working with Robot Framework tests and keyword libraries.
 
* ``robot``: Runs Robot test suites.  By default, recursively runs all tests located under the folder ``robot/<project name>/tests/``. Test suites can be overridden via the ``suites`` keyword and variables inside robot files can be overridden using the ``vars`` option with the syntax ``VAR:value`` (such as ``BROWSER:firefox``).
* ``robot_testdoc``: Generates HTML documentation of your whole robot test suite and writes to ``robot/<project name>/doc/<project_name>.html``.
* ``robot_lint``: Performs static analysis of robot files (files with
  .robot and .resource), flagging issues that may reduce the quality of the code.
* ``robot_libdoc``: Generates library documentation if you choose to create a library of robot keywords for your project.
 
 
Configure the ``robot_libdoc`` Task
-----------------------------------
 
If you define a robot resource file named ``MyProject.resource`` and place it in the ``resources`` folder, you can add this configuration to the ``cumulusci.yml`` file to enable the ``robot_libdoc`` task to generate documentation.
 
.. code-block:: yaml
 
   tasks:
      robot_libdoc:
          description: Generates HTML documentation for the MyProject Robot Framework Keywords
          options:
              path: robot/MyProject/resources/MyProject.resource
              output: robot/MyProject/doc/MyProject_Library.html
 
 
To generate documentation for more than one keyword file or
library, give a comma-separated list of files for the ``path``
option, or define ``path`` as a list under ``tasks__robot_libdoc`` in the ``cumulusci.yml`` file.
 
For example, generate documentation for ``MyLibrary.py``
and ``MyLibrary.resource``.
 
.. code-block:: yaml
 
   tasks:
      robot_libdoc:
          description: Generates HTML documentation for the MyProject Robot Framework Keywords
          options:
              path:
                - robot/MyProject/resources/MyProject.resource
                - robot/MyProject/resources/MyProject.py
              output: robot/MyProject/doc/MyProject_Library.html
 
You can also use basic filesystem wildcards.
 
For example, to document all Robot files in ``robot/MyProject/resources``, configure the ``path`` option under ``tasks__robot_libdoc`` in the ``cumulusci.yml`` file.
 
.. code-block:: yaml
 
   tasks:
      robot_libdoc:
          description: Generates HTML documentation for the MyProject Robot Framework Keywords
          options:
              path: robot/MyProject/resources/*.resource
              output: robot/MyProject/doc/MyProject_Library.html
 
 
 
Robot Directory Structure
=========================
 
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
 
.. note:: For keyword files we recommend using the ``.resource`` suffix.
 
* ``results``: This folder isn't created by `cci project init`. Instead, it is automatically created the first time you run your tests. All generated logs and screenshots of these tests are stored in the ``results`` folder.
* ``tests``: The folder where you store your test suites. You are free to organize this folder however you please, including adding subfolders.
 
 
 
Create Project Tests
====================
 
All project tests live in ``.robot`` files stored under the ``robot/<project_name>/tests/`` directory in the project. You can choose how you want to structure the ``.robot`` files into directories by moving the files around. Directories are treated by Robot Framework as a parent test suite, so a directory named "standard_objects" would become the "Standard Objects" test suite.
 
To learn more about best practices when creating project tests, see `How to Write Good Test Cases <https://github.com/robotframework/HowToWriteGoodTestCases/blob/master/HowToWriteGoodTestCases.rst>`_.
 
 
 
Use Keywords and Tests from a Different Project
===============================================
 
Much like you can :ref:`use tasks and flows from a different project<sources>`<TODO>, you can also use keywords and tests from other projects. The keywords are brought into your repository the same way as with tasks and flows, via the ``sources`` configuration option in the ``cumulusci.yml`` file. However, keywords and tests require extra configuration before they can be used.
 
.. note::
    This feature isn't for general purpose sharing of keywords between multiple projects. It was designed specifically for the case where a product is being built on top of another project and needs access to product-specific keywords.
 
 
Use Keywords
------------
 
In order to use the resources from another project, you must first configure the ``robot`` task to use one of the sources that have been defined for the project. To do this, add a ``sources`` option under the ``robot`` task, and add to it the name of an imported source.
 
For exmple, if your project is built on top of NPSP, and you want to use keywords from the NPSP project, first add the NPSP repository as a source in the project's ``cumulusci.yml`` file:
 
.. code-block:: yaml
 
    sources:
        npsp:
            github: https://github.com/SalesforceFoundation/NPSP
            release: latest_beta
 
Then add ``npsp`` under the ``sources`` option for the robot task. This is because the project as a whole can use tasks or flows from multiple projects, but ``robot`` only needs keywords from a single project.
 
.. code-block:: yaml
 
    tasks:
       robot:
         options:
            sources:
              - npsp
 
When the ``robot`` task runs, it adds the directory that contains the code for the other repository to ``PYTHONPATH``, which Robot uses when resolving references to libraries and keyword files.
 
Once this configuration has been saved, you can import the resources as if you were in the NPSP repository. 
 
For example, in a project which has been configured to use NPSP as a source, the ``NPSP.robot`` file can be imported into a test suite.
 
.. code-block:: robot
 
    *** Settings ***
    Resource   robot/Cumulus/resources/NPSP.robot
 
.. note::
   Even with proper configuration, some keywords or keyword libraries might not be usable. Be careful to avoid using files that have the exact same name in multiple repositories.
 
 
Run Tests
---------
 
Running a test from another project requires prefixing the path to the test with the source name. The path needs to be relative to the root of the other repo.
 
For example, starting from the previous example, to run the ``create_organization.robot`` test suite from NPSP:
 
.. code-block:: console
 
    $ cci task run robot --suites npsp:robot/Cumulus/tests/browser/contacts_accounts/create_organization.robot
 
 
Further Reading
===============
 
.. toctree::
    :maxdepth: 1
 
    robot_tutorial.rst
    robot_debugger.rst
 
 

