Get Started
===========
Getting started with CumulusCI is easy, and once installed, you can:
    * Work on any existing Salesforce projects configured for CumulusCI
    * Create new Salesforce projects configured for CumulusCI
    * Convert existing Salesforce projects to work with CumulusCI

Install CumulusCI
-----------------

macOS / Linux
^^^^^^^^^^^^^
`Homebrew <https://brew.sh/>`_ is a prerequisite for installing CumulusCI on macOS and Linux.
To install homebrew enter the following command into a terminal window:

.. code-block:: console

    $ /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

If prompted for a password, this is your computer's password.
Enter it to allow your computer to install Homebrew.


Install via ``pipx`` (recommended)
*************************************
To install pipx:

.. code-block:: console

    $ brew install pipx
    $ pipx ensurepath

After pipx is installed you can install CumulusCI:

.. code-block:: console

    $ pipx install cumulusci

Once finished you can `verify your installation`_.

Install via Homebrew
***********************
You can also install CumulusCI is using `Homebrew <https://brew.sh/>`_.
Our team has seen issues related to the way that Homebrew installs an manages project dependencies, that can cause issues with the system keychain.
This is why we recommend installing via ``pipx`` if it is an available option to you.

With Homebrew already installed, you can install CumulusCI with:

.. code-block:: console

    $ brew tap SFDO-Tooling/homebrew-sfdo && brew install cumulusci

These commands can take several minutes to complete.
Once finished, you can `verify your installation`_.

Windows
^^^^^^^

Install Python 3
********************
1. Go to the `Python downloads page <https://www.python.org/downloads/windows/>`_.
2. Download the Latest Python 3 Release. The "Download Windows x86-64 executable installer" link for the most recent stable release is probably right one to use, but it may depend on your particular computer setup.
3. Use the installation wizard to install.
   *Be sure to check the â€œAdd Python to environment variablesâ€ checkbox at the end of the install wizard*,
   otherwise you may encounter a ``command not found`` error with the next step.
   To access the Advanced Options area, select "Customize Installation" then click through Optional features page.

.. image:: images/windows_python.png

Install ``pipx``
***********************

Open your preferred terminal application
(e.g. `CMD.exe <https://www.bleepingcomputer.com/tutorials/windows-command-prompt-introduction/>`_ on Windows).
If you already have your terminal open, close it and reopen it. Enter the following command::

    $ python -m pip install --user pipx

.. image:: images/pipx.png

To permanently modify the default environment variables:

1. Click Start and search for â€˜edit environment variablesâ€™ or open System properties,
   Advanced system settings.
2. Click the Environment Variables button.
3. To change System variables, you need non-restricted access to your machine
   (i.e. Administrator rights). Add the following paths to your PATH environment variable:

   a. ``%USERPROFILE%\AppData\Roaming\Python\Python37\Scripts``
   b. ``%USERPROFILE%\.local\bin``

.. image:: images/env-var.png

Open a new command prompt and verify that pipx is available::

    $ pipx --version

You should see a version number after entering in this command, such as: ``0.12.3.1``.
If you get an error instead, such as ``'pipx' is not recognized as an internal or external command,
operable program or batch file.``, please check that your environment variables have been updated.

Install CumulusCI
*************************
You can now install CumulusCI with::

    $ pipx install cumulusci

Now `verify your installation`_.


Verify Your Installation
^^^^^^^^^^^^^^^^^^^^^^^^

In a new terminal window or command prompt you can verify that CumulusCI
is installed correctly by running ``cci version``:

.. code:: console

    $ cci version
    CumulusCI version: 3.9.0 (/path/to/bin/cci)
    Python version: 3.7.4 (/path/to/bin/python)

    You have the latest version of CumulusCI.

You can also use this command in the future to check whether your CumulusCI installation is up to date.

Still need help? Search through `CumulusCI's issues on GitHub <https://github.com/SFDO-Tooling/CumulusCI/issues>`_



Connect to GitHub
-----------------
In order to allow CumlusCI to work with your CumulusCI projects in GitHub, you need to connect GitHub as a service in ``cci``.

First, `create a new personal access token <https://github.com/settings/tokens/new>`_ with both "repo" and "gist" scopes specified. 
(Scopes appear as checkboxes when creating the personal access token in GitHub).
Copy the access token to use as the password when configuring the GitHub service.

Next, run the following command and provide your GitHub username and the access token as the password:

.. code-block:: console

    $ cci service connect github

Once you've configured the `github` service it will be available to **all** projects.  Services are stored in the global CumulusCI keychain by default.


Work on an Existing CumulusCI Project
-------------------------------------
If you're new to a team that is using the CumulusCI workflow, or want to work on an existin CumlusCI project all you need is:
    * Install CumulusCI on you host
    * Make a local clone of the projects GitHub repository.

Once completed, you can change directories into a git repository that has been configured for CumulusCI and run `cci project info` to view information about it: 

.. code-block:: console

    $ cd path/to/your/repo

    $ cci project info
    name: CumulusCI Test
    package:
        name: CumulusCI Test
        name_managed: None
        namespace: ccitest
        install_class: None
        uninstall_class: None
        api_version: 33.0
    git:
        default_branch: main
        prefix_feature: feature/
        prefix_beta: beta/
        prefix_release: release/
        release_notes:
            parsers:
                1:
                    class_path: cumulusci.tasks.release_notes.parser.GithubLinesParser
                    title: Critical Changes
                2:
                    class_path: cumulusci.tasks.release_notes.parser.GithubLinesParser
                    title: Changes
                3:
                    class_path: cumulusci.tasks.release_notes.parser.GithubIssuesParser
                    title: Issues Closed
                4:
                    class_path: cumulusci.tasks.release_notes.parser.GithubLinesParser
                    title: New Metadata
                5:
                    class_path: cumulusci.tasks.release_notes.parser.GithubLinesParser
                    title: Deleted Metadata
        repo_url: https://github.com/SFDO-Tooling/CumulusCI-Test
    test:
        name_match: %_TEST%


Starting a New CumulusCI Project
--------------------------------
This section assumes that you have CumulusCI and ``git`` installed on your host.
We first need to make a directory with our projects name, navigate into the directory, and initialize it as a git repository.

.. code-block:: console

    $ mkdir cci_project; cd cci_project

    $ git init

We now need to initialize our project as a CumulusCI project.

Project Initialization
^^^^^^^^^^^^^^^^^^^^^^
Use the `cci project init` command from within a git repository to generate the initial version of a project's ``cumulusci.yml`` file.

.. code-block:: console

    $ cci project init
    Name: MyRepoName
    Package name: My Repo Name
    Package namespace: mynamespace
    Package api version [38.0]:
    Git prefix feature [feature/]:
    Git default branch [main]:
    Git prefix beta [beta/]:
    Git prefix release [release/]:
    Test namematch [%_TEST%]:
    Your project is now initialized for use with CumulusCI
    You can use the project edit command to edit the project's config file

.. code-block:: console

    $ cat cumulusci.yml
    project:
        name: MyRepoName
        package:
            name: My Repo Name
            namespace: mynamespace

The newly created `cumulusci.yml` file is the configuration file for your project specific tasks, flows, and CumulusCI customizations. 
For more information regarding configuraiton, checkout our `project configuration <#TODO internal ref here>`_ section of the docs. 
You can add and commit it to your git repository:

.. code-block:: console

    $ git add cumulusci.yml
    $ git commit -m "Initialized CumulusCI Configuration"



Add Your Repo to GitHub
^^^^^^^^^^^^^^^^^^^^^^^
With your ``cumulusci.yml`` file committed, we are now ready 



Convert an Existing Salesforce Project
--------------------------------------
If you have a Salesforce project that currently lives in multiple persistent Salesforce orgs that you would like to begin tracking in version control

In order to configure an existing Salesforce Package project for CumulusCI the following must be true:
    * CumulusCI must be installed on your host.
    * Your project must be located in a GitHub repository.
    * Your project must adhere to either `metadata or source formats<https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_source_file_format.htm?search_text=source%20format>`_.

If the above are true, then you run ``cci project init`` from inside the project repository root to generate your projects ``cumulusci.yml`` file.
See `project initialization`_ for more info.

Conversion Considerations
^^^^^^^^^^^^^^^^^^^^^^^^^

    * Generate your projects ``cumulusci.yml`` with ``cci project init``.
    * Migrate any existing org.json files under ``orgs/``.
    * Do you have metadata that you would like deployed pre or post deployment? `pre/post link`_ 
    * 
