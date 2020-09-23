Get started
===========



Install CumulusCI
-----------------

macOS
^^^^^

On Mac, the easiest way to install CumulusCI is using `Homebrew <https://brew.sh/>`_.
To install homebrew:

1. Open your preferred terminal application
   (e.g. `Terminal <https://macpaw.com/how-to/use-terminal-on-mac>`_).

2. Enter::

       /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

3. If you are prompted for a password, this is your computer's password.
   Enter it to allow your computer to install Homebrew.

Stay in the terminal application to install CumulusCI and enter the following command::

    brew tap SFDO-Tooling/homebrew-sfdo && brew install cumulusci

When you run these commands, you'll see many lines of information while it's installing;
this will take around 4min to complete. When it's done, you'll see your command prompt
(perhaps a $ symbol) reappear.

Now `verify your installation`_.

Windows
^^^^^^^

First install Python 3:

1. Go to the `Python downloads page <https://www.python.org/downloads/windows/>`_.
2. Download the Latest Python 3 Release. The "Download Windows x86-64 executable installer" link for the most recent stable release is probably right one to use, but it may depend on your particular computer setup.
3. Use the installation wizard to install.
   *Be sure to check the â€œAdd Python to environment variablesâ€ checkbox at the end of the install wizard*,
   otherwise you may encounter a â€œcommand not foundâ€ error with the next step.
   To access the Advanced Options area, select "Customize Installation" then click through Optional features page.

.. image:: images/windows_python.png

Next install pipx:

Open your preferred terminal application
(e.g. `CMD.exe <https://www.bleepingcomputer.com/tutorials/windows-command-prompt-introduction/>`_ on Windows).
If you already have your terminal open, close it and reopen it. Enter the following command::

    python -m pip install --user pipx

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

    pipx --version

You should see a version number after entering in this command, such as: ``0.12.3.1``.
If you get an error instead, such as ``'pipx' is not recognized as an internal or external command,
operable program or batch file.``, please check that your environment variables have been updated.

Finally, install CumulusCI: Still in your terminal application, enter the following command::

    pipx install cumulusci

Now `verify your installation`_.


Linux
^^^^^

Homebrew can also be used to install CumulusCI on Linux.
First install Homebrew using the instructions for `Homebrew on Linux <https://docs.brew.sh/Homebrew-on-Linux>`_.
Then run::

   brew tap SFDO-Tooling/homebrew-sfdo && brew install cumulusci

..  _`verify installation`:

Verify your installation
^^^^^^^^^^^^^^^^^^^^^^^^

In a new terminal window or command prompt you can verify that CumulusCI
is installed correctly by running ``cci version``:

.. code:: console

   $ cci version
    CumulusCI version: 3.9.0 (/path/to/bin/cci)
    Python version: 3.7.4 (/path/to/bin/python)

    You have the latest version of CumulusCI.

You can also use this command in the future to check whether your CumulusCI installation is up to date.

Still need help? Search issues on CumulusCI GitHub https://github.com/SFDO-Tooling/CumulusCI/issues



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



Start a new CumulusCI project
-----------------------------
The `cci` command is git repository aware. Changing directories from one local git repository to another will change the project context. Each project context isolates the following:

* Orgs: Connected Salesforce Orgs are stored in a project specific keychain
* Services: Named service connections such as Github

If you run the `cci` command from outside a git repository, it will generate an error.

If you run the `cci project info` command from inside a git repository that has already been set up for CumulusCI, it will print the project info:

.. code-block:: console

    $ cd path/to/your/repo

.. code-block:: console

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

If you run the same command from inside a git repository that has not yet been set up for CumulusCI, you will get an error:

.. code-block:: console

    $ cci project info
    The file cumulusci.yml was not found in the repo root. Are you in a CumulusCI project directory?

You can use the `cci project init` command to initialize the configuration:

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

The newly created `cumulusci.yml` file is the configuration file for wiring up any project specific tasks, flows, and CumulusCI customizations for this project. You can add and commit it to your git repository:

.. code-block:: console

    $ git add cumulusci.yml
    $ git commit -m "Initialized CumulusCI Configuration"

Work on an existing CumulusCI project
-------------------------------------

Convert an existing package to CumulusCI
----------------------------------------
In order to have an existing Salesforce Package project use CumulusCI the following must be true:
    * CumulusCI must be installed on your host.
    * Your project must be located in a GitHub repository.
    * Your project must adhere to either `metadata or source formats<https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_source_file_format.htm?search_text=source%20format>`_.

If the above are both true, then integrating CumulusCI into your project is accomplished in a few simple steps.

Generate Your ``cumulusci.yml`` File
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    1. Run ``cci project init``, and provide answers when prompted with questions.
    2. Configure any org definition files
    3. 
