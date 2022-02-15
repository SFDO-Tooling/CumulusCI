=============================================
Managing Locators
=============================================

The keywords that come with CumulusCI are based on the open source
keyword library `SeleniumLibrary
<http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html>`_. This
library supports multiple ways to reference an element: by XPath, by
CSS selector, by id, by text, and so on. SeleniumLibrary calls these
location strategies.

These strategies can be specified by providing a prefix to the
locator.  For example:

* ``id:123`` specifies an element with an id of 123
* ``xpath://div[text()='Hello, world']`` lets you specify an element by an xpath expression
* ``css:div.slds-spinner`` defines an object by its css path

.. tip::
   The full list of supported locator strategies can be found in the
   section titled `Explicit locator strategy
   <https://robotframework.org/SeleniumLibrary/SeleniumLibrary.html#Explicit%20locator%20strategy>`_
   in the SeleniumLibrary documentation.

In this section, we’ll show how to easily create a project-specific
locator strategy by storing locators in a dictionary and then
associating them with a custom prefix.

Storing locators in a dictionary
--------------------------------

The first step toward creating custom locator strategies with the
locator manager is to define your project’s locators in a
dictionary. If you have just a handful of locators you can define them
directly in a keyword library, or you can save them in a separate
file.

If you need to be able to run tests against a prerelease org you
may want to store your locators in two files: one for the current
release and one for the prerelease. You can then import the
appropriate version at runtime.

.. note::

   In order to keep the examples short we’re only going to focus on
   supporting one release at a time in this documentation.


This dictionary can have nested dictionaries in order to allow the
organization of locators into logical groups. The leaf nodes
can be any locator string supported by
SeleniumLibrary. Notice that these locator strings can include
locators of different types.

For example, consider the following set of locators which we might
find in a library of keywords for dealing with the calendar tab:

.. code-block:: python

   locators = {
       "sidebar": {
           "options button": "css:a[role='button'][title='Calendar Options']",
           "new button": "css:a[role='menuitem'][title='New Calendar']",
       },
       "modal": {
           "window": "xpath://div[@role='dialog'][.//h2[.='Create Calendar']]",
           "next button": "css:a.wzButtonSaveAndNext",
       }
   }

We’ve organized the locators into two logical groupings: one related
to elements on the sidebar, and one related to elements of a modal
window. Notice also that three of the locators are CSS selectors and
one is an XPath.


.. tip::

  Dictionaries can be nested as deeply as you want, though it’s
  rarely necessary to have locators more than a couple of levels deep.


Registering the locator dictionary
----------------------------------

SeleniumLibrary provides a way to register `custom location strategies
<http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html#Custom%20locators>`_
via the `Add Location Strategy
<http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html#Add%20Location%20Strategy>`_
keyword. While it’s possible to write your own strategies using
keywords, the locator manager makes it easy to associate a locator
prefix with a dictionary of locators.

This registration is done via the ``register_locators`` method of the
locator manager, and should be done in the ``__init__`` method of a
keyword library.

For example, here is what it might look like for a library that
contains keywords for the calendar tab.

.. code-block:: python

   from robot.libraries.BuiltIn import BuiltIn
   from cumulusci.robotframework import locator_manager

   locators = {...}  # see previous example

   class CalendarLibrary:
       ROBOT_LIBRARY_SCOPE = "GLOBAL"

       def __init__(self):
           locator_manager.register_locators("calendar", locators)

When this library is imported into a test case file, the prefix
“calendar” will be registered with SeleniumLibrary as a custom locator
strategy.

Using custom locators
---------------------

Once the dictionary has been defined and has been registered with a
prefix, the locators work very similarly to any other locator. Because
the dictionaries can be nested, you can separate the levels with a
period (ie: dot notation).

For example, with our example locators the options button locator can
be used like in the following example:

.. code-block::

   Click element   calendar:sidebar.options button


The following table shows how the locator is parsed:

+--------------------+---------------------------------------------------------------------------------------+
| ``calendar:``      | locator prefix                                                                        |
+--------------------+---------------------------------------------------------------------------------------+
| ``sidebar``        | first level of the dictionary (eg: ``locators['sidebar']``)                           |
+--------------------+---------------------------------------------------------------------------------------+
| ``.``              | a level separator                                                                     |
+--------------------+---------------------------------------------------------------------------------------+
| ``options button`` | the next level of a nested dictionary (eg: ``locators['sidebar']['options_button']``) |
+--------------------+---------------------------------------------------------------------------------------+


Parameterized Locators
----------------------

Sometimes the only difference between multiple elements on a page is
the text displayed in that element. For example, the html markup for a
save, edit, and cancel button may be identical except for the word
"Save", "Edit", or "Cancel".

While you could create three separate locators for these three
buttons, using a parameterized locator means we can replace three
locators with one, which helps to keep our tech debt under control.

Notice in our calendar locators we have one locator for a menuitem
with the title of 'New Calendar':

.. code-block::

    locators = {
        ...
        "new_button": "css:a[role='menuitem'][title='New Calendar']",
        ...
    }

If the calendar menu had multiple menuitems, we could use a unique
locator for each, or we could use a single parameterized locator so
that we only need to maintain one locator.

To create a locator with one or more parameters we simply need to replace a
portion of the locator with `{}`. When the locator is used, parameters
can be provided which will be substituded for the `{}`.

The locator would then look like the following example.

.. code-block::

    locators = {
        ...
        "menu_item": "css:a[role='menuitem'][title='{}']",
        ...
    }

When using the locator, one or more parameters can be passed by
specfying a comma separated list of values after a colon. For example:

.. code-block::

    Click element  calendar:sidebar.menu_item:New Calendar

When the locator is used with a keyword, the `{}` will get replaced with `New
Calendar` to give us the actual locator.

.. note::

   If your locator has more than one parameter (ie: more than one
   instance of `{}` within the locator definition), parameters will be
   replaced in the order in which they are supplied. The first
   parameter after the `:` and before a comma will be used in place of
   the first `{}`, the next parameter will be used in place of the
   next `{}`, and so on.
