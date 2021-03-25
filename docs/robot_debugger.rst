==============
Robot Debugger
==============
 
CumulusCI includes a rudimentary Robot debugger that when enabled uses the ``Breakpoint`` keyword from the ``Salesforce`` keyword library to pause execution. When the ``Breakpoint`` keyword is encountered, you are given a prompt to interactively issue commands.
 
For example, try this simple test.
 
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
 
 
 
Enable the Debugger
-------------------
 
To enable the debugger, set the ``debug`` option to ``True`` for the ``robot`` task from the command line when running tests locally.
 
.. note:: 
    **Never set the ``debug`` option in your ``cumulusci.yml`` file.** Doing so could cause tests to block when run on a CI server like MetaCI.
 
For example, run the ``example.robot`` test file.
 
.. code-block:: console
 
    $ cci task run robot --debug True --suites example.robot
 
 
 
Set Breakpoints
---------------
 
The Salesforce keyword library includes a keyword named ``Breakpoint``. When the debugger is enabled, ``Breakpoint`` causes the test to pause. The debugger then offers a prompt where you can interactively enter commands.
 
.. code-block:: console
 
    $ cci task run robot --debug True --suites example.robot
 
    cci task run robot --debug True --suites example.robot
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
 
.. note:: 
    The ``Breakpoint`` keyword has no effect on a test if the ``debug`` option is not set to ``True``. While it's not encouraged to leave this keyword in your test cases, it's safe to do so as long as you only set the ``debug`` option when running tests locally.
 
 
 
Get Help
--------
 
Whenever you see the debugger prompt ``rdb>``, you can request help by typing ``help`` or ``?``, which provides a list of available commands. To get help with a specific command, type ``help`` followed by the command.
 
.. code-block:: console
 
    rdb> help
 
    Documented commands (type help <topic>):
    ========================================
    continue  locate_elements  quit            shell  vars
    help      pdb              reset_elements  step   where
 
    rdb> help vars
    Print the value of all known variables
    rdb>
 
 
 
Examine Variables
-----------------
 
The simplest method to examine the current value of a Robot variable is to return the name of a variable at the prompt. The debugger shows the value of that single variable.
 
.. code-block:: console
 
    rdb> ${BROWSER}
    chrome
 
To see a list of all variables and their values, enter the ``vars`` command.
 
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
 
 
 
Execute Robot Keywords
----------------------
 
You can execute Robot keywords at the prompt by entering the ``shell`` command (or the shortcut ``!``) followed by the keyword and arguments just as you would in a test.
 
For example, run the SeleniumLibrary keyword `Get Location <http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html#Get%20Location>`_.
 
.. code-block:: console
 
    rdb> shell get location
    status: PASS
    result: https://ability-enterprise-4887-dev-ed.lightning.force.com/lightning/setup/SetupOneHome/home
 
The ``shell`` command runs the keyword and then reports the status of the keyword and displays the return value.
 
.. note:: 
    Similar to a test, separate arguments from keywords by two or more spaces.
 
 
Set Robot Variables
-------------------
 
To capture the output of a keyword into a variable, use a variable name with two or more spaces and then the keyword.
 
.. code-block:: console
 
    rdb> ! ${loc}  get location
    status: PASS
    ${loc} was set to https://ability-enterprise-4887-dev-ed.lightning.force.com/lightning/setup/SetupOneHome/home
    rdb> ${loc}
    https://ability-enterprise-4887-dev-ed.lightning.force.com/lightning/setup/SetupOneHome/home
 
In addition to setting variables from the results of keywords, you can also set variables with the ``shell`` command using the built-in keywords `Set Test Variable <http://robotframework.org/robotframework/latest/libraries/BuiltIn.html#Set%20Test%20Variable>`_, `Set Suite Variable <http://robotframework.org/robotframework/latest/libraries/BuiltIn.html#Set%20Suite%20Variable>`_, or `Set Global Variable <http://robotframework.org/robotframework/latest/libraries/BuiltIn.html#Set%20Global%20Variable>`_.
 
.. code-block:: console
 
    rdb> ! set test variable  ${message}  hello, world
    status: PASS
    result: None
    rdb> ${message}
    hello, world
 
 
 
Locate Elements on the Web Page
-------------------------------
 
One of the most powerful features of the debugger is the ability to locate elements on a web page, which makes it easy to experiment with xpaths and other types of locators.
 
For example, find all items on the page that contain the title "Learn More".
 
.. code-block:: console
 
    rdb> locate_elements  //button[@title='Learn More']
    Found 1 matches
 
The elements will be highlighted with a yellow border.
 
.. image:: images/locate_elements_screenshot.png
  
To remove the highlighting, run the ``reset_elements`` debugger command.
 
 
 
Step Through the Test
---------------------
 
The debugger lets you step through a test one keyword at a time. From the ``rdb>`` prompt, enter the``step`` command to continue to the next step in the test.
 
.. code-block:: console
 
    rdb> step
    .
 
    > Example.Example test case
    -> <Keyword: BuiltIn.Log  this is step two>
 
The last lines give context that you are currently right before the keyword ``BuiltIn.Log``. To get a full stack, issue the command ``where``.
 
.. code-block:: console
 
    rdb> where
    0: -> Example
    1:   -> Example.Example test case
    2:     -> BuiltIn.Log



Continue or Quit the Test
-------------------------
 
To let the test run to the end, or to the next ``Breakpoint`` keyword, issue the command ``continue``. To stop execution gracefully (that is, allow all test and suite teardowns to run), issue the ``quit`` command.
