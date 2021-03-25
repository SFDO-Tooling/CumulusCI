==============
Robot Tutorial
==============
 

This tutorial is written with the understanding that you've worked through the `CumulusCI tutorial<TODO>`_ to the point where you recognize the ``cci project init`` command. It is also assumed that you've read the `robotframework<TODO>`_ section of this document, which gives an overview of CumulusCI/Robot Framework integration.

 
 
Part 1: Folder Structure
========================
 
It is best practice that all Robot tests, keywords, data, and log and report files live under a folder named ``robot`` at the root of your repository. If you worked through the `CumulusCI tutorial<TODO>`_, these folders have already been created under ``<project_name>/robot/<project_name>``.
 
* ``doc`` stores test documentation.
* ``resources`` stores Robot libraries and keyword files that are unique to your project
* ``results`` stores log and report files written by Robot Framework during a test.
* ``tests`` stores all tests.
 
 
 
Part 2: Create a Custom Object
==============================
 
For this tutorial, go to Setup and create:
 
* A Custom Object with the name ``MyObject``.
* A Custom Tab associated with this object.
 
 
 
Part 3: Create and Run Your First Robot Test
============================================
 
Create a test that verifies access to the listing page of the Custom Object ``MyObject``. Verifying access to the listing page proves that the test is configured properly.
 
Open the editor and create a file named ``MyObject.robot`` in the ``robot/MyProject/tests`` folder. Copy and paste this code into the file and save.
 
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
 
   ``Go to page`` and ``Current page should be`` accept a page type (``Listing``) and object name (``MyObject__c``). Even though the page object hasn't been created yet, the keywords work by using a generic implementation. When the page object is created, the test uses the custom implementation in the ``MyObject.robot`` file.
 
To run just this test:
 
.. code-block:: console
 
    $ cci task run robot --suites robot/MyProject/tests/MyObject.robot --org dev
 
If successful, each test output announces a ``PASS`` result.
 
.. code-block:: console
 
    $ cci task run robot --suites robot/MyProject/tests/MyObject.robot --org dev
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
 
 
 
Part 4: Create a Page Object
============================
 
Most projects need custom keywords. For example, NPSP has a keyword that fills in a batch gift entry form, and EDA has a keyword with custom logic to validate an affiliated contact.
 
It's best practice to create and organize these keywords by placing them in page object libraries. These libraries contain normal Python classes and methods that have been decorated with the ``pageobjects`` decorator provided by CumulusCI. With page objects, you can write keywords that are unique to a given page, making them easier to find and manage.
 
 
 
Define the Class
-----------------
 
CumulusCI provides base classes that are a good starting point for your page object. For more details on base classes, see `Page Object Base Classes <https://cumulusci.readthedocs.io/en/main/robot.html#page-object-base-classes>`_). 
 
For example, to write a keyword that works on the listing page, create a class that inherits from the ``ListingPage`` class.
 
.. note::
 
    Your class also needs to use the ``pageobject`` decorator, so you must import that along with the ``ListingPage`` class.
 
First, create a new file named ``MyObjectPages.py`` in the folder ``robot/MyProject/resources``. At the top of the new keyword file, add this import statement.
 
.. code-block:: python
 
    from cumulusci.robotframework.pageobjects import pageobject, ListingPage
 
Next, create the class definition.
 
.. code-block:: python
 
    @pageobject(page_type="Listing", object_name="MyObject__c") class MyObjectListingPage(ListingPage):
 
The first line registers this class as a page object for a listing page for the ``MyObject__c`` object. The second line begins the class definition.
 
 
 
Create the Keyword
------------------
 
Create the keyword by creating a method on the ``MyObject__c`` object. The method name should be lowercase, with underscores instead of spaces. When called from a Robot test, the case is ignored, and all spaces are converted to underscores.
 
For example, create a method named ``click_on_the_row_with_name`` that finds a link with a given name, clicks on the link, and then waits for the new page to load. The method uses a ``SeleniumLibrary`` keyword, ``wait_until_page_contains_element``, to wait until the page contains the link before clicking on it. While not strictly necessary on this page, waiting for elements before interacting with them is considered a best practice.
 
Add this code under the class definition.
 
.. code-block:: python
 
    def click_on_the_row_with_name(self, name):
        xpath='xpath://a[@title="{}"]'.format(name)
        self.selenium.wait_until_page_contains_element(xpath)
        self.selenium.click_link(xpath)
        self.salesforce.wait_until_loading_is_complete()
 
Note that this code uses the built-in properties ``self.selenium`` and ``self.salesforce`` to directly call keywords in the ``SeleniumLibrary`` and ``Salesforce`` keyword libraries.
 
 
 
Put It All Together
-------------------
 
This is now the content of the ``MyObjectPages.py`` file.
 
.. code-block:: python
 
    from cumulusci.robotframework.pageobjects import pageobject, ListingPage
 
 
    @pageobject(page_type="Listing", object_name="MyObject__c")
    class MyObjectListingPage(ListingPage):
        def click_on_the_row_with_name(self, name):
            xpath='xpath://a[@title="{}"]'.format(name)
            self.selenium.wait_until_page_contains_element(xpath)
            self.selenium.click_link(xpath)
            self.salesforce.wait_until_loading_is_complete()
 
The next step is to import this page object into your tests. In the first iteration of the test, you imported ``cumulusci.robotframework.PageObjects``, which provided your test with keywords such as ``Go to page`` and ``Current page should be``. In addition to the page object being the source of these keywords, it is also the best method to import page object files into a test case.
 
To import a file with one or more page objects, supply the path to the page object file as an argument when importing ``PageObjects``.
 
.. note::
    
    Use Robot's continuation characters ``...`` on a separate line.
 
Modify the import statements at the top of the ``MyObject.robot`` file.
 
.. code-block:: robotframework
 
    *** Settings ***
 
    Resource  cumulusci/robotframework/Salesforce.robot
    Library   cumulusci.robotframework.PageObjects
    ...  robot/MyProject/resources/MyObjectPages.py
 
These statements import the page object definitions into the test case, but the keywords won't be available until the page object is loaded. Page objects load automatically when you call ``Go to page``, or you explicitly load them with ``Load page object``. In both cases, the first argument is the page type (such as ``Listing``, ``Home``, and so on), and the second argument is the object name, ``MyObject__c``.
 
This test already uses ``Go to page``, so the keyword is available once you've visited the page.
 
 
 
Part 5: Add Test Data
=====================
 
You want to test that when a custom object on the listing page is clicked, it redirects you to the detail page for that object. To achieve this redirect, the test needs test data. While that can be complicated in a real-world scenario, for simple tests use the Salesforce API to create test data when the suite first starts up.
 
To create the data when the suite starts, add ``Suite Setup`` in the settings section of the test. ``Suite Setup`` takes the name of a keyword as an argument. In this example, create a custom keyword in the test to add test data.
 
.. note:: 
 
    It is not necessary to do this step during setup. For example, it could be a step in an individual test case. However, writing the step in the ``Suite Setup`` guarantees it will run before any tests in the same file are run.
 
Open up the ``MyObject.robot`` file and add the ``Create test data`` keyword before ``*** Test Cases ***``.
 
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
 
Then modify ``Suite Setup`` to call this keyword in addition to calling the ``Open Test Browser`` keyword. Because ``Suite Setup`` only accepts a single keyword, use the built-in keyword ``Run keywords`` to run more than one keyword in the setup.
 
.. note::
 
    It is critical to use use all caps for ``AND``, which in Robot's syntax delineates where one keyword ends and the next begins.
 
.. code-block:: robotframework
 
    Suite Setup     Run keywords
    ...  Create test data
    ...  AND  Open test browser
 
Notice that ``Suite Teardown`` calls ``Delete records and close browser``. The ``records`` in that keyword refer to any data records created by ``Salesforce Insert``. This makes it possible to create and later clean up temporary data used for a test.
 
.. important::
    ``Suite Teardown`` isn't guaranteed to run if you forcibly kill a running Robot test. For that reason, there's a step in ``Create test data`` to check for an existing record before adding it. If a previous test was interrupted, and the record already exists, there's no reason to create a new record.
 
 
 
Part 6: Use the New Keyword
===========================
 
Because there is now test data in the database, and the custom keyword definition in your page object file, you can modify the test to use the new keyword.
 
Once again, edit the ``MyObject.robot`` file by adding these statements at the end of the test.
 
.. code-block:: robotframework
 
    Click on the row with name  Leeroy Jenkins
    Current page should be  Detail  MyObject__c
 
The test text now looks like this.
 
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
 
Now run the ``run robot`` task on the test file. If successful, every step of the test should read ``PASS``.
 
.. code-block:: console
 
    $ cci task run robot --suites robot/MyProject/tests/MyObject.robot --org dev
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


