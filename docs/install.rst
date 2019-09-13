..  _`installing CumulusCI`:

--------------------
Installing CumulusCI
--------------------

macOS/Linux
^^^^^^^^^^^

On macOS and Linux, the easiest way to install CumulusCI is using `homebrew <https://docs.brew.sh/>`_ :

.. code:: console

   $ brew tap SFDO-Tooling/homebrew-sfdo
   $ brew install cumulusci

Windows
^^^^^^^

Python
~~~~~~

First, install Python 3: https://www.python.org/downloads/windows/

In the installer, be sure to check the "Add Python to PATH" checkbox.

pipx
~~~~

On Windows 10, the easiest way to install CumulusCI is using
`pipx <https://github.com/pipxproject/pipx>`_. In a new command prompt, run:

.. code:: powershell

   python -m pip install --user pipx

Add the following paths to your ``PATH`` environment variable:

1. ``%USERPROFILE%\AppData\Roaming\Python\Python37\Scripts``
2. ``%USERPROFILE%\.local\bin``

.. note::

   From the `Python
   documentation <https://docs.python.org/3/using/windows.html#excursus-setting-environment-variables>`_:
   To permanently modify the default environment variables, click Start and
   search for ‘edit environment variables’, or open System properties,
   Advanced system settings and click the Environment Variables button. In
   this dialog, you can add or modify User and System variables. To change
   System variables, you need non-restricted access to your machine (i.e.
   Administrator rights)

In a new command prompt, run: ``pipx install cumulusci``

.. code:: powershell

   pipx install cumulusci

Verify CumulusCI
^^^^^^^^^^^^^^^^

In a new terminal window or command prompt you can verify that CumulusCI
is installed correctly by running ``cci version``:

.. code:: console

   $ cci version
   CumulusCI version: 2.5.8

Still need help? Search issues on CumulusCI GitHub https://github.com/SFDO-Tooling/CumulusCI/issues
