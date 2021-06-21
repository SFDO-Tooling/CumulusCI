=============================================
Automate Browser Testing with Robot Framework
=============================================

This document provides details about CumulusCI's integration with `Robot Framework <http://robotframework.org>`_ for automating tests using CumulusCI, Salesforce APIs, and Selenium.

Why Robot Framework?
====================

Robot Framework provides an abstraction layer for writing automated test scenarios in Python and via text keywords in ``.robot`` files.  Since Robot Framework is written in Python (like CumulusCI) and has a robust SeleniumLibrary for automated browser testing, it works well with CumulusCI projects.

CumulusCI's integration with Robot Framework allows building automated test scenarios useful to Salesforce projects:

* Browser testing with Selenium.
* API-only tests interacting with the Salesforce REST, Bulk, and Tooling APIs.
* Complex org automation via CumulusCI.
* Combinations of all of the above.

The ability to create rich, single-file integration tests that interact with CumulusCI's project-specific automation, Salesforce's APIs, and the Salesforce UI in a browser is the most exciting feature of the integration with Robot Framework. Robot Framework makes it easy to automate even complex regression scenarios and tests for edge-case bugs, just by writing Robot Framework test suites and with no need to change project automation in ``cumulusci.yml``.


Included Libraries
==================

CumulusCI comes bundled with additional third-party keyword libraries, in addition to the libraries that come with Robot Framework itself:

* `SeleniumLibrary <http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html>`_ for browser testing
* `RequestsLibrary <https://marketsquare.github.io/robotframework-requests/doc/RequestsLibrary.html>`_  for testing REST APIs

SeleniumLibrary is automatically imported when you import ``Salesforce.robot``. To use ``RequestsLibrary`` you need to explicitly import it in the settings section of your Robot test.


Example Robot Test
==================

The following test file placed under ``robot/ExampleProject/tests/create_contact.robot`` in your project's repository automates the testing of creating a Contact through the Salesforce UI in a browser and via the API.  As an added convenience, it automatically deletes the created Contacts in the Suite Teardown step:

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

The Settings section of the ``.robot`` file sets up the entire test suite.  By including the Resource ``cumulusci/robotframework/Salesforce.robot``, which comes with CumulusCI, we inherit a lot of useful configuration and keywords for Salesforce testing automatically.

The Suite Setup and Suite Teardown are run at the start and end of the entire test suite.  In the example test, we're using the ``Open Test Browser`` keyword from the ``Salesforce.robot`` file to open a test browser.  We're also using the ``Delete Records and Close Browser`` keyword from ``Salesforce.robot`` to automatically delete all records created in the org during the session and close the test browser.

Test Cases
----------

The two test cases test the same operation done through two different paths: the Salesforce REST API and the Salesforce UI in a browser.

Via API
^^^^^^^

This test case uses the ``Get fake data`` keyword to generate a first and last name.  It then uses the ``Salesforce Insert`` keyword from the Salesforce Library (included via ``Salesforce.robot``) to insert a Contact using the same technique for generating test data. Next, it uses ``Salesforce Get`` to retrieve the Contact's information as a dictionary.

Finally, the test calls the ``Validate Contact`` keyword explained in the Keywords section below.

Via UI
^^^^^^

This test case also uses ``Get fake data`` for the first and last name, but instead uses the test browser to create a Contact via the Salesforce UI.  Using keywords from the Salesforce Library, it navigates to the Contact home page and clicks the ``New`` button to open a modal form.  It then uses ``Populate Form`` to fill in the First Name and Last Name fields (selected by field label) and uses ``Click Modal Button`` to click the ``Save`` button and ``Wait Until Modal Is Closed`` to wait for the modal to close.

At this point, we should be on the record view for the new Contact.  We use the ``Get Current Record Id`` keyword to parse the Contact's ID from the URL in the browser and the ``Store Session Record`` keyword to register the Contact in the session records list.  The session records list stores the type and Id of all records created in the session, which is used by the ``Delete Records and Close Browser`` keyword on Suite Teardown to delete all the records created during the test.  In the ``Via API`` test, we didn't have to register the record since the ``Salesforce Insert`` keyword does that for us automatically.  In the ``Via UI`` test, we created the Contact in the browser and thus need to store its ID manually for it to be deleted.

Keywords
--------

The ``Keywords`` section allows you to define keywords useful in the context of the current test suite.  This allows you to encapsulate logic you want to reuse in multiple tests.  In this case, we've defined the ``Validate Contact`` keyword which accepts the Contact id, first, and last names as argument and validates the Contact via the UI in a browser and via the API via ``Salesforce Get``.  By abstracting out this keyword, we avoid duplication of logic in the test file and ensure that we're validating the same thing in both test scenarios.

Running the Test Suite
----------------------

This simple test file can be run via the ``robot`` task in CumulusCI:

.. code-block:: console

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

If you put all of your tests inside that ``robot/<project name>/tests`` folder you don't have to use the ``suite`` option. By default the ``robot`` task will run all tests in the folder and all subfolders. For example, to run all tests and use the default browser you just have to issue the command ``cci task run robot``.


``Salesforce.robot``
====================

Keywords can be defined in a test suite file, but they can also be defined in libraries and resource files. Libraries are written in Python, and resource files are written in the Robot syntax. Resource files are almost identical to a test file, except that they have no tests and can be imported into other test files. In addition to containing keywords, resource files can also define variables and can import other libraries.

The file ``cumulusci/robotframework/Salesforce.robot`` was designed to be the way to import all of the keywords and variables provided by CumulusCI. It should be the first item imported in a test file. It will import the :ref:`salesforce-library-overview` and :ref:`cumulusci-library-overview`, as well as the most commonly used robot libraries
(`Collections <http://robotframework.org/robotframework/latest/libraries/Collections.html>`_,
`OperatingSystem <http://robotframework.org/robotframework/latest/libraries/OperatingSystem.html>`_,
`String <http://robotframework.org/robotframework/latest/libraries/String.html>`_, and
`XML <http://robotframework.org/robotframework/latest/libraries/XML.html>`_)

Variables defined in resource files are accessible to all tests in a suite which imports the resource file. They can be set in your cumulusci.yml file, or specified with the ``vars`` option to the robot task. When doing so, the variables need to be referenced without the dollar sign and curly braces. Variable names are case-insensitive.

For example, here is how to set the browser to Firefox and the default timeout to 20 seconds in a ``cumulusci.yml`` file:

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
-------------------

The following variables defined in ``Salesforce.robot`` are all used by the ``Open Test Browser`` keyword:

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
     - This defines a delay added after every Selenium command. It is
       automatically passed to the `Set Selenium Speed
       <http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html#Set%20Selenium%20Speed>`_ keyword.
       Default: ``0 seconds``

   * - ``${TIMEOUT}``
     - This sets the default amount of time Selenium commands will wait before timing out. It is
       automatically passed to the `Set Selenium Timeout
       <http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html#Set%20Selenium%20Timeout>`_ keyword.
       Default: ``30 seconds``


.. _cumulusci-library-overview:

CumulusCI Library
=================

The CumulusCI Library for Robot Framework provides access to CumulusCI's functionality from inside a Robot test.  It is mostly used to get credentials to a Salesforce org and to run more complex automation to set up the test environment in the org.

Logging Into An Org
-------------------

The ``Login Url``* keyword returns a url with an updated OAuth access token to automatically log into the CumulusCI org from CumulusCI's project keychain.

Run Task
--------

The ``Run Task`` keyword is used to run named CumulusCI tasks configured for the project.  These can be any of CumulusCI's built in tasks as well as project specific custom tasks from the project's cumulusci.yml file.

``Run Task`` accepts a single argument, the task name.  It optionally accepts task options in the format ``option_name=value``.

Run Task Class
--------------

The ``Run Task Class`` keyword is for use cases where you want to use one of CumulusCI's Python task classes to automate part of a test scenario but don't want to have to map a custom named task at the project level.

``Run Task Class`` accepts a single argument, the ``class_path``, as it would be entered into ``cumulusci.yml``, such as ``cumulusci.tasks.salesforce.Deploy``.  Like ``Run Task``, you can also optionally pass task options in the format ``option_name=value``.

Set Test Elapsed Time
---------------------
This ``Set Test Elapsed Time`` keyword captures a computed rather than measured elapsed time for performance-tests.

For example, if you were performance testing a Salesforce batch process, you might want to store the Salesforce-measured elapsed time of the batch process instead of the time measured in the CCI client process.

The keyword takes a single optional argument which is either a number of seconds or a Robot time string
(https://robotframework.org/robotframework/latest/libraries/DateTime.html#Time%20formats).

Using this keyword will automatically add the tag cci_metric_elapsed_time to the test case.

Performance test times are output in the CCI logs and are captured in MetaCI instead of the
"total elapsed time" measured by Robot Framework.

Start and End Perf Time
-----------------------
As a convenience, there are keywords to handle the common case where you want to start
a timer and then store the result with ``Set Test Elapsed Time``. These are ``Start Performance Timer``
and ``Stop Performance Timer``.

Set Test Metric
---------------
This keyword captures any metric for performance monitoring.

For example: number of queries, rows processed, CPU usage, etc.

Elapsed Time For Last Record
----------------------------
The ``Elapsed Time For Last Record`` queries Salesforce for a value that
is Salesforce's recorded log of a job. For example, to query an Apex bulk
job:

.. code-block:: robot

    ${time_in_seconds} =    Elapsed Time For Last Record
    ...             obj_name=AsyncApexJob
    ...             where=ApexClass.Name='BlahBlah'
    ...             start_field=CreatedDate
    ...             end_field=CompletedDate
    ...             order_by=CompletedDate

Full Documentation
------------------

Full documentation of the keywords in the CumulusCI and Salesforce
keyword libraries can be found here:

* :download:`CumulusCI and Salesforce Keyword Documentation <../docs/robot/Keywords.html>`


.. _salesforce-library-overview:

Salesforce Library
==================

The Salesforce Library provides a set of useful keywords for interacting with Salesforce's Lightning UI and Salesforce's APIs to test Salesforce applications. In addition to keywords, the library defines some custom locator strategies to aid in locating elements on a page.

UI Keywords
-----------

The goal of the UI keywords in the Salesforce Library is to abstract out common interactions with Salesforce from interactions with your application's UI.  The Salesforce Library itself has an extensive suite of Robot tests which are regularly run to alert us to any changes in the base Salesforce UI.  By centralizing these interactions and regularly testing them, the Salesforce Library provides a more stable framework on which to build your product tests.

There are too many keywords relating to UI interactions to cover here.  Please reference the full Salesforce Library documentation below.

Waiting for Lightning UI
^^^^^^^^^^^^^^^^^^^^^^^^

A common challenge when writing end-to-end UI tests is the need to wait for asynchronous actions to complete before proceeding to run the next interaction. The Salesforce Library is aware of the Lightning UI and can handle this waiting automatically. After each click, it will wait for any pending requests to the server to complete. (Manually waiting using a "sleep" or waiting for a particular element to appear may still be necessary after other kinds of interactions and when interacting with pages that don't use the Lightning UI.)

API Keywords
------------

In addition to browser interactions, the Salesforce Library also provides the following keywords for interacting with the Salesforce REST API:

* ``Salesforce Collection Insert``: used for bulk creation of objects
  based on a template.
* ``Salesforce Collection Update``: used for the bulk updating of
  objects.
* ``Salesforce Delete``: Deletes a record using its type and ID.
* ``Salesforce Get``: Gets a dictionary of a record from its ID.
* ``Salesforce Insert``: Inserts a record using its type and field values.  Returns the ID.
* ``Salesforce Query``: Runs a simple query using the object type and field=value syntax.  Returns a list of matching record dictionaries.
* ``Salesforce Update``: Updates a record using its type, ID, and field=value syntax.
* ``SOQL Query``: Runs a SOQL query and returns a REST API result dictionary.

Locator Strategies
------------------

SeleniumLibrary provides many locator strategies for finding elements on a page. For example, you can specify an element via an xpath, an id, a css selector, or several others. These are documented in the SeleniumLibrary documentation under a section titled `Locating elements <http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html#Locating%20elements>`_.

In addition to the predefined locator strategies, the Salesforce library defines the following locator strategies, all of which use keywords in the Salesforce library to find web elements. For detailed explanations of the locator strategies, see the documentation for each keyword.

.. list-table::
   :widths:  1 3

   * - ``label``
     - This uses the Salesforce library keyword ``Locaate Element by Label`` to find web elements.
       It is most useful to find form fields based on lightning web components and which have a ``label`` associated with the component. For example, ``label:First Name`` might return a ``<lightning-input>`` component that wraps a block of code which contains a ``<label>`` element with the given text. This strategy is used by the Salesforce library keyword ``Input form data``.
   * - ``text``
     - This uses the Salesforce library keyword ``Locate Element by Text`` to find web elements that contain a given string. For example, ``text:Profile`` is shorthand for the xpath locator ``xpath://*[text()='Profile']``
   * - ``title``
     - This uses the Salesforce library keyword ``Locate Element by Title`` to find web elements that have a title attribute with the given string. For example, ``title:Appointment`` is shorthand for the xpath ``xpath://*[@title='Appointment']``

PageObjects Library
===================

The ``PageObjects`` library provides support for page objects,
Robot Framework-style. Even though Robot is a keyword-driven framework,
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
of the provided base classes. No matter which class you inherit from,
your class gets the following predefined properties:

- ``self.object_name`` is the name of the object related to the
  class. This is defined via the ``object_name`` parameter to the
  ``pageobject`` decorator. You should not add the namespace
  prefix in the decorator. This attribute will automatically add the
  prefix from ``cumulusci.yml`` when necessary.

- ``self.builtin`` is a reference to the robot framework
  ``BuiltIn`` library, and can be used to directly call built-in
  keywords. Any built-in keyword can be called by converting the name
  to all lowercase, and replacing all spaces with underscores (eg:
  ``self.builtin.log``, ``self.builtin.get_variable_value``, etc).

- ``self.cumulusci`` is a reference to the CumulusCI keyword
  library. You can call any keyword in this library by converting the
  name to all lowercase, and replacing all spaces with underscores (eg:
  ``self.cumulusci.get_org_info``, etc).

- ``self.salesforce`` is a reference to the Salesforce keyword
  library. You can call any keyword in this library by converting the
  name to all lowercase, and replacing all spaces with underscores (eg:
  ``self.salesforce.wait_until_loading_is_complete``, etc).

- ``self.selenium`` is a reference to SeleniumLibrary. You can call
  any keyword in this library by converting the name to all lowercase,
  and replacing all spaces with underscores (eg:
  ``self.selenim.wait_until_page_contains_element``, etc)


.. _page-object-base-classes:

Page Object Base Classes
------------------------

Presently, CumulusCI provides the following base classes,
which should be used for all classes that use the ``pageobject`` decorator:

- ``cumulusci.robotframework.pageobjects.BasePage`` - a generic base
  class used by the other base classes. It can be used when creating
  custom page objects when none of the other base classes make sense.
- ``cumulusci.robotframework.pageobjects.DetailPage`` - a class
  for a page object which represents a detail page.
- ``cumulusci.robotframework.pageobjects.HomePage`` - a class for a
  page object which represents a home page.
- ``cumulusci.robotframework.pageobjects.ListingPage`` - a class for a
  page object which represents a listing page.
- ``cumulusci.robotframework.pageobject.NewModal`` - a class for a
  page object which represents the "new object" modal.
- ``cumulusci.robotframework.pageobject.ObjectManagerPage`` - a class
  for interacting with the object manager.

The ``BasePage`` class adds the following keyword to every page object:

- ``Log current page object`` - this keyword is mostly useful
  while debugging tests. It will add to the log information about the
  currently loaded page object.

Example Page Object
-------------------

The following example shows the definition of a page
object for the listing page of a custom object named ``MyObject__c``. It adds a new
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

The ``PageObjects`` library is somewhat unique in that it is not only a
keyword library, but also the mechanism by which you can import files
which contain page object classes. This is done by providing the paths
to one or more Python files which implement page objects. You may also
import ``PageObjects`` without passing any files to it in order to take
advantage of some general purpose page objects.

For example, consider the case where you've created two files that
each have one or more page object definitions. For example, lets say
in ``robot/MyProject/resources`` you have the files ``PageObjects.py`` and
``MorePageObjects.py``. You can import these page objects into a test
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
import the ``PageObjects`` library and any custom page object files you
wish to use.

The second thing you must do is either explicitly load the keywords
for a page object, or reference a page object with one of the generic
keywords provided by the ``PageObjects`` library.

To explicitly load the keywords for a page object you can use the
:code:`load page object` keyword provided by the ``PageObjects``
library. Other keywords provided by that library will automatically
import the keywords if they are successful. For example, you can call
:code:`Go To Page` followed by a page object reference, and if that page is
able to be navigated to, its keywords will automatically be loaded.

Page Object Keywords
--------------------

The ``PageObjects`` library provides the following keywords:

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
that page object will automatically be loaded.

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

This will load the page object for the given ``page_type`` and
``object_name_``. It is useful when you want to use the keywords from a
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
``PageObjects`` library will try to find a generic page.

For example, if you use :code:`Current page should be  Home  Event` and
there is no page object by that name, a generic :code:`Home` page object
will be loaded, and its object name will be set to :code:`Event`.

Let's say your project has created a custom object named
``Island``. You don't have a home page, but the object does have a
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

- ``Detail`` (eg: :code:`Go to page  Detail  Contact  ${contact id}`)
  Detail pages refer to pages with a URL that matches the
  pattern "<host>/lightning/r/<object name>/<object id>/view"
- ``Home`` (eg: :code:`Go to page  Home  Contact`)
  Home pages refer to pages with a URL that matches the pattern
  "<host>/lightning/o/<object name>/home"
- ``Listing`` (eg: :code:`Go to  page  Listing  Contact`)
  Listing pages refer to pages with a URL that matches the pattern
  "<host>b/lightning/o/<object name>/list"
- ``New`` (eg: :code:`Wait for modal  New  Contact`)
  The New page object refers to the modal that pops up
  when creating a new object.

Of course, the real power comes when you create your own page object
class which implements keywords which can be used with your custom
objects.


Keyword Documentation
=====================

Use the following links to download generated documentation for both
the CumulusCI and Salesforce keywords

* :download:`CumulusCI and Salesforce Keyword Documentation <../docs/robot/Keywords.html>`

CumulusCI Robot Tasks
=====================

CumulusCI includes several tasks for working with Robot Framework tests and keyword libraries:

* ``robot``: Runs Robot test suites.  By default, recursively runs all tests located under the folder ``robot/<project name>/tests/``.  Test suites can be overridden via the ``suites`` keyword and variables inside robot files can be overridden using the ``vars`` option with the syntax ``VAR:value`` (ex: ``BROWSER:firefox``).
* ``robot_testdoc``: Generates html documentation of your whole robot test suite and writes to ``robot/<project name>/doc/<project_name>.html``.
* ``robot_lint``: Performs static analysis of robot files (files with
  .robot and .resource), flagging issues that may reduce the quality of the code.
* ``robot_libdoc``:  This task can be wired up to generate library
  documentation if you choose to create a library of robot keywords
  for your project.

Configuring the ``robot`` task
--------------------------

The Robot Framework command-line test runner supports more than 50
`command line options
<http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#command-line-options-for-test-execution>`_.
To make the ``robot`` task simpler to use, we've only exposed a few of the
command-line options at the task level. For example, the ``robot`` task
options ``include``, ``exclude``, and ``skip`` directly map to the Robot CLI
options ``--include``, ``--exclude``, and ``--skip``. These options
are specified the same way as task options elsewhere in the CumulusCI framework,
using either command-line options as shown above or by including them in the ``options``
section of a task configuration in ``cumulusci.yml``::

    tasks:
        robot:
            options:
                include: <value>

Other Robot CLI
options, such as ``tagstatlink``, ``expandkeywords``, and
many others, have no direct task option counterpart.

There may be times when you want to use some of the Robot CLI
options which haven't been exposed as task options. We support that through
an additional ``options`` section nested inside the typical task options in
``cumulusci.yml``.

For example, one of the most common uses of this inner ``options`` section is to
use the Robot CLI option ``--outputdir`` to specify where Robot should
write its report and log files. To configure this option
for the task, you must remove the leading dashes from the option name
and then place that option
and value in a nested ``options`` section.

.. code-block:: robotframework

    tasks:
        robot:
            options:
                options:
                    outputdir: robot/my_project/results

Any Robot CLI option which takes a value can be specified
this way. For example, to use the Robot CLI option ``--name`` along with
``--outputdir``, your ``cumulusci.yml`` file should look like
this:

.. code-block:: robotframework

    tasks:
        robot:
            options:
                options:
                    outputdir: robot/my_project/results
                    name: Salesforce Robot Tests


Configuring the ``libdoc`` task
---------------------------

If you have defined a Robot resource file named MyProject.resource and
placed it in the ``resources`` folder, you can add the following
configuration to your cumulusci.yml file in order to enable the
``robot_libdoc`` task to generate documentation:

.. code-block:: yaml

   tasks:
      robot_libdoc:
          description: Generates HTML documentation for the MyProject Robot Framework Keywords
          options:
              path: robot/MyProject/resources/MyProject.resource
              output: robot/MyProject/doc/MyProject_Library.html


You can generate documentation for more than one keyword file or
library by giving a comma-separated list of files for the ``path``
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
to document all Robot files in ``robot/MyProject/resources`` you could
configure your YAML file like this:

.. code-block:: yaml

   tasks:
      robot_libdoc:
          description: Generates HTML documentation for the MyProject Robot Framework Keywords
          options:
              path: robot/MyProject/resources/*.resource
              output: robot/MyProject/doc/MyProject_Library.html



Robot Directory Structure
=========================

When you use ``cci project init``, it creates a folder named ``robot`` at the root of your repository. Immediately under that is a folder for your project Robot files. If your project depends on keywords from other projects, they would also be in the ``robot`` folder under their own project name.

.. code-block:: console

   MyProject/
   ├── robot
   │   └── MyProject
   │       ├── doc
   │       ├── resources
   │       ├── results
   │       └── tests

With the project folder inside the ``robot`` folder are the following additional folders:

* ``doc``: the location where generated documentation will be placed.
* ``resources``: this folder is where you can put your own keyword files. You can create `robot keyword files <http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#creating-user-keywords>`_ (.resource or .robot) as well as `keyword libraries <http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#creating-test-libraries>`_ (.py). For keyword files we recommend using the ``.resource`` suffix.
* ``results``: this folder isn't created by `cci project init`. Instead, it will automatically be created the first time you run your tests. It will contain all of the generated logs and screenshots.
* ``tests``: this is where you should put your test suites. You are free to organize this however you wish, including adding subfolders.


Creating Project Tests
======================

Like in the example above, all project tests live in ``.robot`` files stored under the ``robot/<project name>/tests/`` directory in the project.  You can choose how you want to structure the ``.robot`` files into directories by just moving the files around.  Directories are treated by Robot as a parent test suite, so a directory named "standard_objects" would become the "Standard Objects" test suite.

The following document is recommended reading:

https://github.com/robotframework/HowToWriteGoodTestCases/blob/master/HowToWriteGoodTestCases.rst

Using Keywords and Tests from a Different Project
=================================================

Much like you can :ref:`use tasks and flows from a different
project<sources>`, you can also use keywords and tests from other
projects. The keywords are brought into your repository the same way
as with tasks and flows, via the ``sources`` configuration option in
``cumulusci.yml``. However, they require a little extra configuration
before they can be used.

.. note::
   This feature should not be used for general purpose sharing of
   keywords between multiple projects. This feature was designed
   specifically for the case where a product is being built on top of
   another project and needs access to product-specific keywords.


Using keywords
--------------

In order to use the resources from another project you must first
configure the ``robot`` task to use one of the sources that have been
defined for the project. To do this, add a :code:`sources` option in
the ``robot`` task, and add to it the name of one of the imported sources.

For example, if your project is built on top of NPSP and you want to
use keywords from the NPSP project, you must first add the NPSP
repository as a source in the project's ``cumulusci.yml``:

.. code-block:: yaml

    sources:
        npsp:
            github: https://github.com/SalesforceFoundation/NPSP
            release: latest_beta

You must then add :code:`npsp` under the :code:`sources` option for
the robot task. This is because the project as a whole may use tasks
or flows from multiple projects, but ``robot`` only needs keywords from a
single project.

.. code-block:: yaml

    tasks:
       robot:
         options:
            sources:
              - npsp

When the ``robot`` task runs, it adds the directory which contains the
code for the other repository to ``PYTHONPATH``, which Robot uses when
resolving references to libraries and keyword files.

Once this configuration has been saved, you can import the resources
just as if you were in the NPSP repository. For example, in a project
which has been configured to use NPSP as a source, the following
example shows how ``NPSP.robot`` can be imported into a test suite:

.. code-block:: robot

    *** Settings ***
    Resource   robot/Cumulus/resources/NPSP.robot

.. note::
   Even with proper configuration, some keywords or keyword libraries
   might not be usable. You must be careful to not try to use files
   that have the exact same name in multiple repositories.


Running Tests
-------------

Running a test from another project requires prefixing the path to the
test with the source name. The path needs to be relative to the root
of the other repo.

For example, starting from the previous example, to run the
``create_organization.robot`` test suite from NPSP, you would do it
with something like this:

.. code-block:: console

    $ cci task run robot -o suites npsp:robot/Cumulus/tests/browser/contacts_accounts/create_organization.robot


Further Reading
===============

.. toctree::
    :maxdepth: 1

    robot_tutorial.rst
    robot_debugger.rst
