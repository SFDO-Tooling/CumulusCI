Get Started
===========



Install CumulusCI
-----------------

On macOS / Linux
^^^^^^^^^^^^^^^^
`Homebrew <https://brew.sh/>`_ is a prerequisite for installing CumulusCI on macOS and Linux.
To install homebrew enter the following command into a terminal window:

.. code-block:: console

    $ /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

If prompted for a password, this is your computer's password.
Enter it to allow your computer to install Homebrew.


Install via ``pipx`` (recommended)
*************************************
Once Homebrew is installed, you can install ``pipx`` and CumulusCI.

.. code-block:: console

    $ brew install pipx
    $ pipx ensurepath
    $ pipx install cumulusci

Once finished you can `verify your installation`_.

Install via Homebrew
***********************
You can also install CumulusCI using `Homebrew <https://brew.sh/>`_.
Our team is aware of issues with Homebrew installations that can cause issues with the system keychain in some situations.
This is why we recommend installing via ``pipx`` if it is an available option

With Homebrew already installed, you can install CumulusCI with:

.. code-block:: console

    $ brew tap SFDO-Tooling/homebrew-sfdo && brew install cumulusci

These commands can take several minutes to complete.
Once finished, you can `verify your installation`_.



On Windows
^^^^^^^^^^

Install Python 3
********************
1. Go to the `Python downloads page <https://www.python.org/downloads/windows/>`_.
2. Download the Latest Python 3 Release. The "Download Windows x86-64 executable installer" link for the most recent stable release is probably right one to use, but it may depend on your particular computer setup.
3. Use the installation wizard to install.
   *Be sure to check the â€œAdd Python to environment variablesâ€ checkbox at the end of the install wizard*,
   otherwise you may encounter a ``command not found`` error with the next step.
   To access the Advanced Options area, select "Customize Installation" then click through Optional features page.

.. image:: images/windows_python.png

Install via ``pipx``
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

You can now install CumulusCI with::

    $ pipx install cumulusci

Now `verify your installation`_.



Verify Your Installation
^^^^^^^^^^^^^^^^^^^^^^^^

In a new terminal window can verify that CumulusCI is installed correctly by running ``cci version``:

.. code:: console

    $ cci version
    CumulusCI version: 3.19.0 (/path/to/bin/cci)
    Python version: 3.8.5 (/path/to/bin/python)

    You have the latest version of CumulusCI.

You can also use this command in the future to check whether your CumulusCI installation is up to date.

Still need help? `CumulusCI's issues on GitHub <https://github.com/SFDO-Tooling/CumulusCI/issues>`_ may have something useful.



Connect to GitHub
-----------------
In order to allow CumlusCI to work with your CumulusCI projects in GitHub, you need to connect GitHub as a service in ``cci``.

First, `create a new personal access token <https://github.com/settings/tokens/new>`_ with both "repo" and "gist" scopes specified.
(Scopes appear as checkboxes when creating the personal access token in GitHub).
Copy the access token to use as the password when configuring the GitHub service.

Next, run the following command and provide your GitHub username and the access token as the password::

    $ cci service connect github

You can verify the GitHub service is connected by running ``cci service list``:

.. image:: images/service-list.png

Once you've configured the ``github`` service it will be available to **all** CumulusCI projects.
Services are stored in the global CumulusCI keychain by default.



Work on an Existing CumulusCI Project
-------------------------------------
To work on existing CumulusCI project all you need is to:

* `Install CumulusCI`_
* `Install git <https://git-scm.com/book/en/v2/Getting-Started-Installing-Git>`_
* Make a local clone of the projects GitHub repository.



Cloning a GitHub Repository
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Cloning a projects repository gives you a local working copy of the project on your computer.
The following steps assume that you have `git installed <https://git-scm.com/downloads>`_ on your machine.

To clone a GitGub repository:

#.  Navigate to the repository on GitHub
#.  Click the green 'Code' button
#.  Ensure 'HTTPS' is selected #TODO: cover ssh or gh cli?
#.  Click the clipboard button to copy the https repository url to your clipboard.
#.  In a new terminal window exectue the following command:

.. code-block:: console

    $ git clone <repository_url> <project_name>

Replace ``<repository_url>`` with the url copied to your clipboard.
Replace ``<project_name>`` with the name of the project.

You can now change directories into the freshly cloned project and begin executing ``cci`` commands.
For example, ``cci project info`` can be run to display information about the project:

.. code-block:: console

    $ cd cumulusci-test

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
We first need to make a directory with our project's name, navigate into the directory, and initialize it as a git repository.

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
With your ``cumulusci.yml`` file committed, we now want to create a repository on GitHub for our new project and push our changes there.

#. `Create a new repository <https://docs.github.com/en/free-pro-team@latest/articles/creating-a-new-repository>`_ on GitHub.
#. At the top of your GitHub Repository's Quick Setup page, click the clipboard button to copy the remote repository URL.
#. In your terminal, `add the URL for the remote repository <https://docs.github.com/en/free-pro-team@latest/articles/adding-a-remote>`_ to where your local repository will be pushed::

    $ git remote add origin <remote_repository_url>

#. Verify the remote was added successfullly with::

    $ git remote -v

#. `Push the changes <https://docs.github.com/en/free-pro-team@latest/github/using-git/pushing-commits-to-a-remote-repository>`_ in your local repository to GitHub::

    $ git push -u origin master



Convert an Existing Salesforce Project
--------------------------------------

Project Setup
^^^^^^^^^^^^^
#. Create a directory for your project to live in, and navigate to it::

    $ mkdir mySalesforceProject; cd mySalesforceProject

#. Initialize the directory as a git repository::

    $ git init
    Initialized empty Git repository in /Users/MrCCI/repos/mySalesforceProject/.git/

#. Initialize the repository as a CumulusCI project. See `project initialization`_.


Extracting Your Project's Metadata
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Next we need to extract your package metadata.
Depending on what type of org your project is in, there are different methods for extracting the desired pieces of metadata.

Production or Developer Edition Orgs
*******************************************
#. Create a package for your - If you're looking to deploy back to the same org, or would like to be able to use ``cci task run retrieve_source`` ensure that your project's name in ``cumulusci.yml`` matches the name of your package.
#. Add the desired metadata components to the package.
#. Extract package in either metadata (``src/``) or ``sfdx`` (``force-app/``) formats.
    * For metadata format::

        $ cci task run retrieve_source

    * For ``sfdx`` format, replace <namespace> with the namespace of your package::

        $ sfdx force:source:retrieve -n <namespace>

Scratch or Sandbox Orgs
*****************************
Metadata is easier to extract in these orgs as `source tracking <https://developer.salesforce.com/docs/atlas.en-us.sfdx_setup.meta/sfdx_setup/sfdx_setup_enable_source_tracking_sandboxes.htm>`_ can be enabled in them.
``sfdx`` allows for easy retrieval of all metadata changes made to an org with this feature enbaled::

    $ sfdx force:source:pull


That's it! You now have all of the metadata you care about in a single git repository configured for use with CumulusCI.
At this point you may want to `add your repo to github`_, or perhaps begin `configuring CumulusCI` <#TODO doc ref>.



Other Considerations
^^^^^^^^^^^^^^^^^^^^
* If you or your team have been working with `scratch or definition files <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_scratch_orgs_def_file.htm>`_ for use with ``sfdx`` you can see our documentation on `configuring orgs` <#TODO doc ref> to utilize them with CumulusCI.
* If you have metadata that you would like deployed pre or post deployment? `#TODO <pre/post ref>`
* If you have data that you need to include either for testing or production purposes, see the `Automating Data Operations` <#TODO doc ref> section of our docs.
