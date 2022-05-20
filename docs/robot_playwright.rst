=============================================
Experimental Playwright Support
=============================================

Since its inception, CumulusCI has relied on Selenium to provide the
foundation of our browser automation keywords.

In 2020, Microsoft introduced a new browser automation tool named
`Playwright <https://playwright.dev/>`_.
Playwright is a ground-up reinvention of a browser automation
library that aims to address several shortcomings of Selenium.  For
example, playwright has built-in support for waiting for elements to
appear, for working with the shadow DOM, video capture of a testing
session, and so on.

In 2021 the Robot Framework project introduced the
`Browser <https://robotframework-browser.org/>`_ library which adds
keywords based on top of Playwright.

Starting with CumulusCI version 3.58.0, we are providing experimental
support for Playwright and the Browser library in CumulusCI.

Installation
------------

We have not yet bundled Playwright and the Browser library with
CumulusCI. However, we have provided a script to make it easy to
install or uninstall Playwright and the Browser library while we continue to work
on fully supporting it.

Step 1: Install Node.js
^^^^^^^^^^^^^^^^^^^^^^^

Playwright is based on Node.js. If you don't 
already have Node.js installed, you can find
a Node.js installer for your platform on the
`Node.js downloads page <https://nodejs.org/en/download/>`_.

.. warning:: You must have Node.js installed before continuing with these instructions.

Step 2: Run the Playwright installation command
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Installing the browser library requires a couple of manual steps, which we've
automated in a single script. This script does three things:

* it verifies that Node.js has been installed
* it downloads and installs the Browser keyword library
* it downloads and installs the Node.js modules and drivers for
  playwright.

.. note::

   The installation of Playwright contains drivers for all supported
   browsers, so there's no need to manually install drivers such as
   ChromeDriver. It works right out of the box!

Before you run the script, make sure your working directory is at
the root of your repository. You can then run the script with the following command:

.. code-block:: console

    $ cci robot install_playwright

.. tip::

   You can use the ``--dry_run`` (or ``-n``) option to see what the
   command will do without actually installing anything.


Running an example test
-----------------------

As mentioned earlier, this is an experimental release of Playwright
integration, so any CumulusCI keywords that rely on Selenium won't
work. However, the following example shows how easy it can be to
write Playwright-based tests with off-the-shelf `keywords provided by
the Browser library
<https://marketsquare.github.io/robotframework-browser/Browser.html>`_

.. code-block:: robotframework

    *** Settings ***
    Resource     cumulusci/robotframework/Salesforce.robot
    Library      Browser

    Suite Setup  Open test browser

    *** Keywords ***
    Open test browser
        New Browser  chromium  headless=false
        ${url}=      Login URL
        New Page     ${url}
        Wait until network is idle

    *** Test Cases ***

    Go to user profile
        Click    button:has-text("View profile")
        Click    .profile-card-name .profile-link-label

        Wait until network is idle
        Take screenshot

    Go to contacts home
        Click            button:has-text("App Launcher")
        Fill text        input[placeholder='Search apps and items...']  Contacts
        Click            one-app-launcher-menu-item:has-text("Contacts")

        Wait until network is idle
        Take screenshot

To run the test, save the above code in a ``.robot file`` (e.g.
``example.robot``) and then run it with the standard robot task:

.. code-block:: console

    $ cci task run robot --suites example.robot


Things to Notice
^^^^^^^^^^^^^^^^

This example test is unable to use any of the existing
Selenium-based keywords. For that reason, this test creates
a new ``Open Test Browser`` that uses the Browser keywords
`New Browser
<https://marketsquare.github.io/robotframework-browser/Browser.html#New%20Browser>`_
and `New Page
<https://marketsquare.github.io/robotframework-browser/Browser.html#New%20Page>`_
to open the browser.

This test also uses the Browser keyword
`Wait until network is idle
<https://marketsquare.github.io/robotframework-browser/Browser.html#Wait%20Until%20Network%20Is%20Idle>`_
before taking a screenshot. This is a convenient keyword that usually
waits until the page is fully rendered before returning, saving
the need to wait for some specific element to show up.

This test has no explicit waits for the buttons and links that it
clicks on. The underlying Playwright engine automatically waits for
elements, so there should almost never be a need for keywords such as
``Wait until page contains element`` or ``Wait until element is
enabled``.

Finally, notice how easy it is to interact with both the app menu and
the user profile. Playwright locators are often much easier to write
than Selenium locators, which translates to tests and keywords that
don't have to be tweaked when the page markup changes.

Summary
-------

This is just a preview of things to come. The CumulusCI team will be
spending more time evaluating playwright, with an eye toward making it
a viable and more robust replacement for Selenium.


Resources
---------

* `Browser Library Home Page <https://robotframework-browser.org/>`_
* `Browser Library Keyword Documentation <https://marketsquare.github.io/robotframework-browser/Browser.html>`_
* `Playwright Home Page <https://playwright.dev>`_
