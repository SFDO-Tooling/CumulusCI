=======
History
=======

2.3.3 (2019-02-28)
------------------

* Fixed a bug where flow options specified on the command line were not passed to tasks correctly.
* ``cci service connect`` now shows a more helpful error message if you call it with a service name that CumulusCI doesn't know about. Fixes #752.
* Deleted scratch orgs will no longer show the number of days since they were created in ``cci org list``. Thanks to @21aslade for the fix.
* Updates to the MetaDeploy publish task:

  * It is now possible to publish a new plan for an existing version.
  * It is now possible to specify the AllowedList to which a plan is visible.

* Updates to Robot Framework support:

  * Fixed a bug in the ``robot`` task: it now accepts an option called ``test`` rather than ``tests``, since the latter was ignored by Robot Framework.
  * Fixed some stability problems with the ``Populate Field`` keyword.
  * The ``robot_libdoc`` task has been replaced with a new task of the same name that can generate a single HTML document for multiple keyword files by passing a comma-separated list of files to the ``path`` option.

2.3.2 (2019-02-19)
------------------

* Mapping enhancements for bulk ``QueryData`` and ``LoadData`` tasks
  
  * The mapping yaml file no longer requires using ``Id: sf_id`` as a field mapping.  If not provided, ``QueryData`` and ``LoadData`` will use local database ids instead of Saleforce OIDs for storing lookup relationships.  Previous mappings which specify the ``Id: sf_id`` mapping will continue to work as before using the Salesforce OID as the mapping value.
  * The mapping yaml file's ``lookups:`` section now handles defaults to allow simpler lookup mappings.  The only key required is now ``table``.  If the ``key_field`` is provided it will be used.

* The ``sql_path`` option on ``QueryData`` can be used to provide the file path where a SQL script should be written.  If this option is used, a sqlite in-memory database is used and discarded.  This is useful for storing data sets in a Github repository and allowing diffs of the dataset to be visible when reviewing Pull Requests
  
  * When using this option, it is best to make sure your mapping yaml file does not provide a field mapping for the ``Id`` field.  This will help avoid merge conflicts if querying data from different orgs such as scratch orgs.

* The `sql_path` option on ``LoadData`` can be used to provide the file path where a SQL script file should be read and used to load an in-memory sqlite database for the load operation.

2.3.1 (2019-02-15)
------------------

* Fixed a bug that caused the ``cci`` command to check for a newer version on every run, rather than occasionally. Also we now detect whether CumulusCI was installed using Homebrew and recommend an upgrade command accordingly.
* CumulusCI now automatically generates its own keychain key and stores it in the system keychain (using the Python `keyring` library). This means that it is no longer necessary to specify a CUMULUSCI_KEY as an environment variable. (However, the environment variable will still be preferred if it is there, and it will be migrated to the system keychain.)
* New task ``connected_app`` makes it easier to deploy and configure the Connected App needed for CumulusCI's keychain to work with persistent orgs.  The connected app is deployed using ``sfdx`` to an org in the ``sfdx`` keychain and defaults to the ``defaultdevhubusername``.
* The ``robot`` task gives a more helpful error message if you forget to specify an org.
* Updates to the task for publishing to MetaDeploy:

  * Dependency installation steps are now named using the package name and version.
  * The task options have been revised to match changes in the MetaDeploy API. An optional ``plan_template_id`` is now accepted. ``preflight_message`` is now named ``preflight_message_additional`` and is optional. ``post_install_message`` is now named ``post_install_message_additional`` and is optional.

2.3.0 (2019-02-04)
------------------

Changes:

* When installing a managed package dependency, pre & post metadata bundles are now fetched from the git commit corresponding to the most recent release of the managed package, instead of master.
* Improvements to the task for publishing a release to MetaDeploy:
  * It can now publish a tag even if it's a different commit than what is currently checked out in the working directory.
  * It now pins managed deployments of metadata bundles to the git commit corresponding to the most recent release of the managed package.

Issues Closed:

* #962: ``cumulusci.utils.findReplace`` uses wrong file encoding in Python 3
* #967: Allow ``cci service`` commands to be run from outside a project repository

2.3.0b1 (2019-01-28)
--------------------

Breaking Changes:

* We refactored the code for running flows. The full list of steps to run is now calculated from nested flow configuration when the flow is initialized instead of during runtime. Your existing flows should continue to run as before, but if you're interacting with CumulusCI at the Python API level, you'll need to use the ``FlowCoordinator`` instead of ``BaseFlow``.
* Tasks are now expected to have no side effects when they are instantiated. If tasks need to set up resources, do that in ``_init_task`` instead of ``__init__`` or ``_init_options`` to make sure it doesn't happen until the task is actually being run.

Changes:

* There is now a ``dev_org_beta_deps`` flow which sets up an org in the same way as ``dev_org``, but installs the latest beta versions of managed package dependencies.
* The ``github_release`` task now records the release dependencies as JSON in the release's tag message.
* Looking up the latest release from GitHub is now done using a single HTTP request rather than listing all releases.
* We added S-Controls to the list of metadata types that the ``uninstall_packaged_incremental`` task will delete.
* Salesforce Robot Framework library: The ``Get Current Record Id`` keyword now parses the Id correctly when prefixed with ``%2F``, which apparently happens.
* The ``push_failure_report`` task now avoids an error when querying for info about lots of subscriber orgs.

Issues Closed:

* #911: Fix UnicodeDecodeError when parsing XML retrieved from the Metadata API.

2.2.6 (2019-01-03)
------------------

Changes:

* Added support for more metadata types: Group, SharingSet, SharingCriteriaRule, SharingOwnerRule, and SharingTerritoryRule.
* Release process: We now have tools in place to release cumulusci so that it can be installed using Homebrew or Linuxbrew.

Issues Closed:

* Fixed an issue where tasks using the Salesforce REST API could build a wrong URL with an extra slash after the instance URL.
* Fixed an issue where overriding a flow step to set flow: None did not work.
* Robot Framework: Added an automatic retry to work around an issue with an intermittent ConnectionResetError when connecting to headless Chrome in Python 3.

2.2.5 (2018-12-26)
------------------

* The ``install_managed`` and ``install_managed_beta`` tasks now take optional ``activateRSS`` and ``password`` options. ``activateRSS`` is set to true by default so that any active Remote Site Settings in the package will remain active when installed.

* When running a task with the ``--debug`` flag, HTTP requests are now logged.

* Robot Framework:

  * Fix issue where "Get Current Record Id" could accidentally match the object name instead of the record Id.
  * Fix issue where "Load Related List" would fail to scroll down to the list.
  * Fix issue where errors deleting records during test teardown would cause a hidden test failure.


2.2.4 (2018-12-17)
------------------

Changes:

* Bulk query task:

  * Fixed an issue with querying data filtered by record type (#904).
  * Fixed an issue where the optimized approach for loading data into PostgreSQL was not used.
  * The task will now prevent you from accidentally overwriting existing data by exiting with an error if the table already exists.

* The ``deploy`` task now logs the size of the zip payload in bytes.

* Fixed a TypeError in the ``commit_apex_docs`` task (#901).

* Robot Framework:

  * Add location strategies for locating elements by text and by title.

2.2.3 (2018-12-07)
------------------

Changes:

* Improved error messages when scratch org creation failed and when a service is not configured.
* Robot Framework: Limit how long the "Load Related List" keyword will wait.

2.2.2 (2018-11-27)
------------------

Changes:

* Improved error handling during scratch org creation:

  * Capture and display stderr output from SFDX (issue #413).
  * Avoid infinite recursion if username wasn't found in output from SFDX.

* Robot Framework: Increased the timeout for initial loading of the browser.


2.2.1 (2018-11-21)
------------------

Oops, an update in CumulusCI 2.2.0 ended up breaking the update_dependencies task! Now fixed.

2.2.0 (2018-11-21)
------------------

Changes:

* Tasks can now be placed in groups for the task list! Just specify a ``group`` when defining the task in YAML.

* By popular request, there is now an ``org import`` command to import an org from the SFDX keychain to the CumulusCI keychain. It takes two arguments: the SFDX username or alias, and the org name.

* Robot Framework:

  * The ``Populate Field`` keyword now clears an existing value using keystrokes to make sure that change events are fired.
  * Added a ``Get Namespace Prefix`` keyword to the CumulusCI library to get the namespace prefix for a package.
  * Fixed a bug that broke opening a browser after using the ``Run Task`` keyword.

* Documentation updates:

  * The readme now includes a link to the full documentation.
  * The instructions for installing CumulusCI on macOS have been simplified and now recommend using the official Python installer from python.org instead of Homebrew. (Homebrew should still work fine, but is no longer necessary.) We also now suggest creating a virtualenv using venv rather than pyenv since the former is included with Python. It's fine to continue using pyenv if you want.
  * Give more useful links for how to set up SFDX.
  * Updated robot library docs.

* Internal refactoring:

  * Removed dependency on HiYaPyCo for YAML loading, which would not report which file failed to load in the event of a YAML parse error.
  * We now consistently load YAML in the same manner throughout the entire library, which will work with all supported Python versions.
  * Simplified the Python API for setting up a CumulusCI runtime. Begone, YamlGlobalConfig and YamlProjectConfig. Our Python API is not yet documented, but we're working on it. In the meantime, if you were relying on running CCI from within Python, you can now just use BaseGlobalConfig (and its get_project_config member) to bootstrap CCI.
  * BaseProjectConfig has shrugged off some methods that just delegated to the keychain.
  * BaseGlobalConfig has shrugged off some unimplemented methods, and BaseGlobalConfig.get_project_config is now deprecated in favor of using a runtime.
  * Introducing... 🥁CumulusCIRuntime! In order to alleviate the complexities of getting CumulusCI tasks/flows running from within a Python application, CumulusCIRuntime encapsulates a lot of the details and wiring between Keychain, GlobalConfig, and ProjectConfig. Usage docs are barely included.
  * CliConfig has been renamed to CliRuntime and now inherits from CumulusCIRuntime. It is still accessible as CliConfig.
  * Upgraded dependencies.

* Contributor improvement: The contributor docs now explain how to install pre-commit hooks to make sure our linters have run before you commit.

Issues Closed:

* #674: ``cci org import <username> <org_name>``
* #877: CumulusCI should be able to connect to any DX alias and/or understand dx auth files

2.1.2 (2018-10-29)
------------------

Oops, we broke a few things! This is a bugfix release to fix a few issues found during the Salesforce.org Open Source Community Sprint last week.

Issues Closed:

* #858 Dataload bulk query fails to load data into the sqlite db
* #862 CLI options fail on robot task in 2.1.1
* #864 Deploying a -meta.xml file with non-ASCII characters breaks in Python 2

2.1.1 (2018-10-23)
------------------

Changes:

* Our robotframework library for Salesforce got a number of improvements:

  * New keywords:

    * ``Click Header Field Link``: Clicks a link in a record header
    * ``Load Related List``: Scrolls to a related list and waits for it to load
    * ``Click Related List Button``: Clicks a button in the header of a related list
    * ``Click Related Item Link``: Clicks the main link for an item in a related list
    * ``Click Related Item Popup Link``: Clicks a link in the popup menu for an item in a related list

  * Updated to ``robotframework-seleniumlibrary`` 3.2.0 which includes a ``Scroll Element Into View`` keyword.
  * ``Wait Until Loading Is Complete`` now waits for the main body of the page to render
  * ``Populate Lookup Field`` now tries several times in case there's an indexing delay
  * Added a ``-o verbose True`` option to the robot task which logs each keyword as it runs.
  * We now ignore errors while running the script that waits for XHRs to complete
    (it can fail if the page reloads before the script finishes).

* Popup notifications upon completion of a flow or task now work on Linux too,
  if you have the ``notify-send`` command from libnotify.
  On Ubuntu, install the ``notify-osd`` package.

Issues Closed:

* #827 Bulk data load breaks in Python 2
* #832 pip install cumulusci gets the wrong version of urllib3

2.1.1b1 (2018-10-17)
--------------------

* ``uninstall_packaged_incremental`` task: Added ``ignore`` option to specify components to skip trying to delete even if they are present in the org but not in the local source.

2.1.0 (2018-10-16)
------------------

* Fixed the ``cci project init`` command, which was failing because it wanted
  the project to already exist! Fixes #816. In addition, other commands
  will now function without an active project or keychain when it possible
  to do so. (For example, try ``cci version`` which now works when you're
  not in a project directory.)
* ``update_dependencies`` task:
    * Added support for installing private github repositories as dependencies.
      Thanks to Anthony Backhouse (@1handclapping) for the patch. Fixes #793
    * Added a ``dependencies`` option to override the project dependencies.
* ``execute_apex`` task:
    * Print more useful error messages when there are Apex exceptions.
* ``robot`` task:
    * Our logic for automatically retrying failed selenium commands has been
      encapsulated into the ``cumulusci.robotframework.utils.selenium_retry``
      decorator which can be applied to a robot library class for increased
      stability.
    * There is now an option to pause and enter the Python debugger
      after a keyword fails. Run with ``-o pdb True``.
    * Revised keywords and locators to support the Winter '19 release of Salesforce
      and improve stability.
    * The ``Salesforce.robot`` file now includes the ``OperatingSystem`` and ``XML``
      libraries from Robot Framework by default. These libraries are helpful in
      building integration tests such as modifying and deploying a PageLayout
      to include a field needed in Suite Setup of an integration test.
* Revised installation instructions for Windows. Thanks Matthew Blanski (@Auchtor).
* Internal change: Use a thread-local variable instead of a global to track the current running task.

2.1.0b1 (2018-10-05)
--------------------

* It's happening! Hot on the heels of the last release, CumulusCI is making the jump to the modern era by adding **support for Python 3**! (Specifically, Python 3.6 and 3.7.) Don't worry, we'll also continue to support Python 2 for the time being. Because this is a bit more wide-reaching change than normal, we're releasing a beta first. To install the beta you'll need to explicitly request its version: ``pip install cumulusci==2.1.0b1``.
  If you already have CumulusCI, after the update it will continue to run under your Python 2 interpreter. If you want to switch to the Python 3 interpreter (which is not yet required), we recommend deleting
  your Python virtualenv and starting over with the instructions in the `tutorial <https://cumulusci.readthedocs.io/en/latest/tutorial.html>`_.  If you want to keep your Python 2-based virtualenv around just in case, follow those instructions but name the new virtualenv ``cci-py3`` instead of ``cci``.
* There are also some big changes to the **bulk data** tasks. Did you know CumulusCI has bulk data tasks? They are not configured by default, because we need to finish documenting them. But we'll list the changes in case someone is already relying on them:
  * Fixed connection resets by downloading an entire result file before processing.
  * Improved performance by processing batches in parallel, avoiding the SQLAlchemy ORM, storing inserted Ids in separate tables, and doing lookups using SQL joins rather than a separate query for each row.
  * If you're using a postgres database for local storage, performance gets even better by taking advantage of postgres' ``COPY`` command to load CSV directly.
  * Added a ``hardDelete`` option for bulk deletes.
  * Added a ``start_step`` option for bulk loads which can be used to resume loading after an error.
* The ``push_failure_report`` task will now by default hide failures that occurred due to the "Package Uninstalled" or "Salesforce Subscription Expired" errors, which are generally benign.
* Fixed the check for newer CumulusCI versions to work around an issue with old ``setuptools``.
* Contributor change: We switched CumulusCI's own tests to run using ``pytest``.
* Internal change: We switched to the ``cryptography`` library for handling keychain encryption.

2.0.13 (2018-10-02)
-------------------
* Happy Spooky October! It's unlucky release 2.0.13, with some scary-cool improvements. Just to show you how ramped up our RelEng team is now, this release had TWENTY THREE pull requests in 12 days! From all four of your friendly SFDO Release Engineering committers. Thanks so much for continuing to use CCI for all your Salesforce automation needs.
* NEW FLOW: ci_beta_dependencies installs the latest beta of project dependencies and run tests. Includes task error when running against non-scratch orgs.
* NEW TASK: ReportPushFailures pulls a list of Package Push Upgrade Request failures after a push attempt, including grouping by important factors.
* Issue a terminal "Bell" sound and attempt to display a macOS notification when a commandline task or flow completes.
* Cleaned up python exception and error handling across the board, so that we can provide you, the user, with only the most relevant information. Try using CCI without setting your CUMULUSCI_KEY and see a simplified error message.
* Fixed the utils for processing namespaces in package zip files to handle non-ASCII characters
* The CONTRIBUTING.rst docs and Makefile have been updated to show how we release updates of CCI.
* Skip beta releases when checking for a newer cumulusci version
* When using the strip_namespace option on deployments, we now log which files had changes made before deploying.
* Going Out: the SFDXDeploy and SFDXJsonPollingTasks have been removed, as they didn't work.
* Going Out: Use the safe_load() method when loading YAML instead of the naive load(). If you relied on executing code in your CCI YAML file parsing, that will no longer work.

2.0.12 (2018-09-20)
-------------------

* Fixed apexdoc URL
* Fixed `update_admin_profile` to set any existing record type defaults to false before setting new defaults.
* Fixed deployment of -meta.xml files containing non-ASCII characters.
* Updated the robot selector for "Click Modal Button" to work for modals opened by a Quick Action.

2.0.11 (2018-09-14)
-------------------

* `update_admin_profile` now uses xml parsing instead of string replacement for more targeted editing of Admin.profile to fix issues with deploying record types via dependencies
* Projects can declare a dependency on a minimum version of cumulusci by specifying `minimum_cumulusci_version` in cumulusci.yml

2.0.10 (2018-09-13)
-------------------

* `update_admin_profile` task now sets application and tab visibility and supports setting record type visibility and default via the new `record_types` task option
* Restructured exceptions to include two new parent exceptions useful in client implementations:

  * CumulusCIFailure: Used to signify a failure rather than an error, such as test or metadata deployment failures
  * CumulusCIUsageError: Use to signify a usage error such as accessing a task that does not exist

* `execute_anon` task now accepts either `apex` (string) or `path` (Apex in a local file) for the Apex to execute.  Also, the `managed` and `namespaced` options allow injecting namespace prefixes into the Apex to be executed.

* New flow `retrieve_scratch` can be used to retrieve declarative changes from a scratch org into the src/ directory

2.0.9 (2018-09-10)
------------------

* Make robot commands use new lightning URLs
* Remove unused filter_name arg from Go to Record Home robot keyword.
* Fix metadata map for Settings.

2.0.8 (2018-08-21)
------------------
* Flows that are executed from within another flow now support task-level control flow.
* We no longer support the undocumented ability for a Flow to provide its own class_path.
* Use the connected app details to set a client name on HTTP requests to Salesforce.

2.0.7 (2018-08-16)
------------------
* `cci service show` has been renamed `cci service info`!
* Update default API version in the base YAML to v43.0.
* Doc updates in the tutorial, thanks to @justindonnaruma!
* Significant refactor of the cli module, including a bunch of small usability and exception handling changes. See https://github.com/SFDO-Tooling/CumulusCI/pull/708 for details.
* Display the file name for error causing files in more cases.
* Strip packageVersions tags from aura/, components/, and pages/ metadata.
* Update PyYAML dependency.

2.0.6 (2018-08-07)
------------------
* In Robot tests that use the standard keyword for interacting with a lookup field, we now wait for all AJAX requests to complete before submitting.
* Add unit tests for large sections of the library.
* We now support Flow, DuplicateRule, and other new Metadata types thanks to @carlosvl.
* Fixed refreshing oauth token when deploying metadata to persistent orgs.

2.0.5 (2018-08-01)
------------------

* Fixes #695: Update InstallPackageZipBuilder to set activateRSS to unblock installs.

2.0.4 (2018-07-30)
------------------

* Fixes #611: Scratch org operations were failing on Windows
* Fixes #664: Scratch org aliases incorrectly included double quotes in the alias name

2.0.3 (2018-07-27)
------------------

* Added support for waiting on Aura HTTP Requests to complete after a browser action is performed in selenium from the Robot Salesforce Library: http://cumulusci.readthedocs.io/en/latest/robotframework.html#waiting-for-lightning-ui
* Github API client will now automatically retry on 502 errors
* Better error messages from parsing errors during package.xml generation which show the file causing the error

2.0.2 (2018-06-06)
------------------
* Bugfix: Update InstallPackageZipBuilder to use a recent api version to unblock installs.

2.0.1 (2018-06-06)
------------------
* Bugfix: Allow passing a connected app directly to OrgConfig.refresh_oauth_token.

2.0.0 (2018-06-01)
------------------

After over 19 months of development as alpha (40 version over 3 months) and beta (98 releases over 16 months) releases and over a year running production builds using CumulusCI, it's time to remove the "beta" label.

This marks the first production release of CumulusCI 2.x!

2.0.0-beta99 (2018-05-31)
-------------------------

* Ensure that github credentials are never shown in the log for github dependencies with unmanaged metadata

2.0.0-beta98 (2018-05-31)
-------------------------
**WARNING: This release introduces breaking changes to the syntax for flow definitions and to the default flows.  If you customized any of the default flows in your project or have defined custom flows, you will need to modify your cumulusci.yml file to work with this release.**

Changes default flows shipped with CumulusCI to a new syntax and structure taking advantage of the ability for flows to call other flows.  This allows flows to be modularized in ways that weren't possible when the original set of flows was designed.

* The **tasks:** section in cumulusci.yml for a flow is now renamed to **steps:**  A **FlowConfigError** will be raised if an old style flow definition is detected.  All existing flow customizations and custom flows need to be changed in the **cumulusci.yml** to avoid raising an exception.
* All default flows have been restructured.  Existing customizations of default flows likely need to be changed to adapt to the new structure.  In most cases, you will want to move your customizations to some of the new **config_*** or **deploy_*** instead of the main flows.
* **ci_beta_install** has been removed and replaced with **install_beta** and **uninstall_managed**  **install_beta** does not attempt to uninstall an existing version of the package.  If you need to uninstall the package first, use the **uninstall_managed** flow before running **install_beta**
* Added new **qa_org** flow to allow different configurations for dev vs QA orgs
* New modularized flows structure allows for easier and more reusable customization:

    * **dependencies** Runs the pre-package deployment dependency tasks **update_dependencies** and **deploy_pre**  This flow is called by almost all the main flows.
    * **config_*** flows provide a place to customize the package configuration for different environments.  These flows are called by the main flows after the package metadata is deployed or a managed version is installed.  Customizations to the config flows automatically apply to the main flows.

        * **config_apextest** Configure org for running apex tests
        * **config_dev** Configure org for dev use
        * **config_managed** Configure org with a managed package version installed
        * **config_packaging** Configure the packaging org
        * **config_qa** Configure org for QA use

    * **deploy_*** flows provide a place to customize how metadata deployments are done.  The deploy flows do more than just a simple deployment such as unscheduling scheduled jobs, rebuilding the package.xml, and incrementally deleting any stale metadata in the package from the org.

        * **deploy_unmanaged** Used to do a standard deployment of the unmanaged metadata
        * **deploy_packaging** Used to deploy to packaging.  Wraps the **create_managed_src** task around the deploy to inject metadata that can only be deployed to the packaging org
        * **deploy_unmanaged_ee** Used to deploy unmanaged metadata to an Enterprise Edition org using the **create_unmanaged_ee_src** task

* **github** dependencies can now point to a private Github repository.  All zip downloads from Github will pass the password (should be a personal access token) from the **github** service configured in the CumulusCI keychain.
* **GithubRelease**, **PushUpgradeRequest**, and **PackageUploadRequest** now track the release data as return values

2.0.0-beta97 (2018-05-31)
-------------------------
- Salesforce Connected App is now a CCI Service! Instead of using `cci org config_connected_app` you can use the familiar `cci service` commands.
- Better error handling when running commands without specifying a default org (thanks @topherlandry)
- Fix issue where scratch org password may become outdated
- Improve Robot test runner task to use the already configured CCI environment instead of trying to create a new one.
- Enable Robot testing in Headless Chrome on Heroku.
- Address Python3 print statement issues.
- Add LogLine task class to log statements and variables.
- Add PassOptionAsResult, PassOptionAsReturnValue to pass options around in Flows.
- Further extended the Flow runner subclass API.

2.0.0-beta96 (2018-05-18)
-------------------------

- Fixes for CumulusCI on Windows - CumulusCI 2 now supports Windows environments!
- Support skipping scratch org password creation by specifying `--no-password` to `cci org scratch`
- Add additional logging to PackageUpload

2.0.0-beta95 (2018-05-10)
-------------------------

- Add pytz to requirements

2.0.0-beta94 (2018-05-10)
-------------------------

- Support added for nested flows. Specify a flow instead of a task inside another flow in cumulusci.yml
- Add new task github_release_report to report info from GitHub release notes
- Add new flow dev_deploy for minimal deploy (tasks: unschedule_jobs, deploy)
- Enhance BaseFlow to be more easily subclassed/overridden/observed. Preserves task step number and adds several hook methods for subclasses (_pre_task, _post_task, _post_task_exception)
- Refactor github_release_notes task to use github3.py instead of calling the GitHub API directly. Includes these minor changes to functionality:
    - Cannot create release with this task (use github_create_release instead)
    - Merge existing release notes even when not publishing
- Fix issue that caused duplicate entries in the dependency tree
- Sort output of os.listdir in all occurrences. Guarantees ordered iteration over files on disk
- Validate CUMULUSCI_KEY value and raise more helpful exceptions if invalid

2.0.0-beta93 (2018-04-20)
-------------------------

- Fix issue in command task for Windows
- Support interactive in command task (thanks Chris Landry!)
- Search more pull requests (100 vs 30) when generating release notes
- Add options to Apex documentation generator task

2.0.0-beta92 (2018-04-04)
-------------------------

- Ignore OWNERS file in package.xml generation
- Pipe stderr in command tasks

2.0.0-beta91 (2018-04-03)
-------------------------

- Fix issue in ZIP functionality for Windows

2.0.0-beta90 (2018-03-26)
-------------------------

- Include missing scratch_def.json template file needed by cci project init

2.0.0-beta89 (2018-03-23)
-------------------------

- Improved cci project init
    - Prompt for extending a repository with HEDA and NPSP as selectable options
    - Use jinja2 templates included with cumulusci to create files
    - Include a default Robot test
- update_package_xml now ignores CODEOWNERS files used by Github
- Fixed an import error for click in cci

2.0.0-beta88 (2018-03-20)
-------------------------

* Fix issue in parsing version from tag name

2.0.0-beta87 (2018-03-15)
-------------------------

* Fix issue in getting latest version

2.0.0-beta86 (2018-03-13)
-------------------------

* Initial Integration with Robot Framework (see here for details: http://cumulusci.readthedocs.io/en/latest/robotframework.html)
* Add support for GlobalValueSetTranslation Metadata Type (thanks Christian Szandor Knapp!)
* Use Tooling API for PackageUploadRequest
* New doc "Why CumulusCI?"
* Add documentation for the skip option on GitHub dependencies

2.0.0-beta85 (2018-02-21)
-------------------------

* Support bigobject index element in .object
* Only run meta.xml file cleaning on classes/* and triggers/* directory
* Add docs on CumulusCI Flow
* Add reference to needing the Push API to run release_beta in tutorial doc

2.0.0-beta84 (2018-02-12)
-------------------------

* Add new Status 'Queued' to PackageUploadRequest check

2.0.0-beta83 (2018-02-08)
-------------------------

* Add a sleep in between successful PackageUploadRequest and querying for MetadataPackageVersion to address issue in Spring '18 packaging orgs.

2.0.0-beta82 (2018-02-02)
-------------------------

* Update salesforce-bulk package to version 2.0.0
* Fix issue in bulk load data task

2.0.0-beta81 (2018-01-18)
-------------------------

* Filter SObjects by record type in bulk data retrieve
* Fix issue in removing XML elements from file

2.0.0-beta80 (2018-01-08)
-------------------------

* The deploy tasks now automatically clean all meta.xml files in the deployed metadata of any namespace references by removing the <packageVersions> element and children.  This allows CumulusCI to fully manage the dependencies and avoids the need for new commits to change referenced versions in meta.xml files.
    * The default functionality can be disabled with the by setting `clean_meta_xml` to False
* Github dependencies can now point to a specific tag in the repository.  The tag is used to determine the version to install for the dependency if the repository has a namespace configured and will be used to determine which unpackaged metadata to deploy.

2.0.0-beta79 (2017-11-30)
-------------------------

* Fixes #540: Using a custom `prefix_beta` fails if releases with the same version but different prefix already exist in the repository.  Changed to use `tag_name` instead of `name` to check if the release already exists in Github.

2.0.0-beta78 (2017-11-22)
-------------------------

Resolving a few issues from beta77:

* A bug in BaseKeychain.create_scratch_org was causing the creation of ScratchOrgConfig's with a days value of None.  This caused issues with subsequent calls against the org.
* Fixed output from new logging in namespace injection
* Switch to using org_config.date_created to check if an org has been created
* Fix bug in recreation of an expired scratch org

2.0.0-beta77 (2017-11-22)
-------------------------

* New Salesforce DX tasks: `dx_convert_from`, `dx_convert_to`, `dx_pull`, and `dx_push`
* New flow for creating production releases (use with caution!): `release_production`
* Scratch org configs can now specify `days` as an option which defaults to 1.  The default for a scratch config can be overridden in `cci org scratch` with the `--days N` option
* `cci org remove` will now attempt to first delete a scratch org if one was already created
* `cci org scratch` will prevent you from overwritting a scratch config that has already created a scratch org (which would create an orphaned scratch org) and direct you to use `cci org remove` instead.
* `cci org list` now shows the duration days, elapsed days, and if an org is expired.
* `cci org info` now shows the expiration date for scratch orgs
* All `cci` commands that update an org config will now attept to automatically recreate an expired scratch org
* New namespace inject token strings are supported for injecting namespaces into Lightning Component references:

  * **%%%NAMESPACE_OR_C%%%***: Replaced with either 'your_namespace' (unmanaged = False) or 'c' (unmanaged = True)
  * **%%%NAMESPACED_ORG_OR_C%%%***: Replaced with either 'your_namespace' (namespaced_org = True) or 'c' (namespaced_org = False)
* Deleted all tasks and code related to `apextestsdb` since its functionality is now integrated into MetaCI and no longer used

2.0.0-beta76 (2017-11-14)
-------------------------

* Fix bug in namespace injection
* Add option to print org info as JSON

2.0.0-beta75 (2017-11-07)
-------------------------

* Fix syntax for github dependency with `--extend` option on `cci project init`

2.0.0-beta74 (2017-11-07)
-------------------------

* Default to Salesforce API version 41.0

2.0.0-beta73 (2017-11-07)
-------------------------

* Fix bug in creating the `dev_namespaced` scratch org config from `cci project init`

2.0.0-beta72 (2017-11-06)
-------------------------

* Fix bug in setting namespace from `cci project init`

2.0.0-beta71 (2017-11-06)
-------------------------

* Update docs, including tutorial for Windows (thanks Dave Boyce!)
* Add missing "purge on delete" option for BaseUninstallMetadata
* Fix crash when decoding certain strings from the Metadata API response
* Add support for featureParameter* metadata types (thanks Christian Szandor Knapp!)

2.0.0-beta70 (2017-10-30)
-------------------------

* Fix issue in zip file processing that was introduced in v2.0.0b69

2.0.0-beta69 (2017-10-27)
-------------------------

* cumulusci.core has been made compatible with Python 3!
* `cci project init` has been upgraded

  * Better prompt driven user experience with explanations of each prompt
  * `--extend <repo_url>` option to set up a recursive dependency on another CumulusCI project's Github repository
  * Creates `sfdx-project.json` if it doesn't already exist
  * Creates and populates the `orgs/` directory if it does not already exist.  The directory is populated with starter scratch org shape files for the 4 main scratch org configs in CumulusCI: `beta.json`, `dev.json`, `feature.json`, `release.json`

* Fix issue with namespace injection
* `push_*` tasks now accept `now` for the `start_time` option which will start the push upgrade now (technically 5 seconds from now but that's better than 5 minutes).

2.0.0-beta68 (2017-10-20)
-------------------------

* Configure `namespace_inject` for `deploy_post_managed`

2.0.0-beta67 (2017-10-20)
-------------------------

* Fix bug where auto-created scratch orgs weren't getting the `scratch` attribute set properly on their `ScratchOrgConfig` instance.


2.0.0-beta66 (2017-10-20)
-------------------------

* Configure `namespace_inject` for `deploy_post`
* Fix the `--debug` flag on `cci task run` and `cci flow run` to allow debugging of exceptions which are caught by the CLI such as MetadataApiError, MetadataComponentError, etc.

2.0.0-beta65 (2017-10-18)
-------------------------

Breaking Changes
================

* If you created custom tasks off of `DeployNamespaced` or `DeployNamespacedBundles`, you will need to switch to using `Deploy` and `DeployBundles`.  The recommended configuration for such custom tasks is represented below.  In flows that need to inject the actual namespace prefix, override the `unmanaged` option .. ::

    custom_deploy_task:
        class_path: cumulusci.tasks.salesforce.Deploy
        options:
            path: your/custom/metadata
            namespace_inject: $project_config.project__package__namespace
            unmanaged: False

Enhancements
============

* The `cci` CLI will now check for new versions and print output at the top of the log if a new version is available
* The `cci` keychain now automatically creates orgs for all named scratch org configs in the project.  The orgs are created with the same name as the config.  Out of the box, CumulusCI comes with 4 org configs: `dev`, `feature`, `beta`, and `release`.  You can add additional org configs per project using the `orgs` -> `scratch` section of the project's `cumulusci.yml`.  With this change, `cci org list` will always show at least 4 orgs for any project.  If an org already exists in the keychain, it is not touched and no scratch org config is auto-created for that config.  The goal is to eliminate the need to call `cci org scratch` in most cases and make it easier for new users to get up and running with scratch orgs and CumulusCI.
* `cci org remove <org_name>` is now available to remove orgs from the keychain
* Scratch orgs created by CumulusCI are now aliased using the naming format `ProjectName__org_name` so you can easily run sfdx commands against scratch orgs created by CumulusCI
* `cci org list` now shows more information including `scratch`, `config_name`, and `username`.  NOTE: config_name will only be populated for newly created scratch configs.  You can use `cci org scratch` to recreate the config in the keychain.
* The new flow `dev_org_namespaced` provides a base flow for deploying unmanaged metadata into a namespaced org such as a namespaced scratch org
* All tasks which previously supported `namespace_inject` now support a new option, `namespaced_org`.  This option is designed to handle use cases of namespaced orgs such as a namespaced scratch org.  In namespaced orgs, all unmanaged metadata gets the namespace prefix even if it is not included in the package.  You can now use the `namespaced_org` option along with the file content token `%%%NAMESPACED_ORG%%%` and the file name token `___NAMESPACED_ORG___` to inject the namespace when deploying to a namespaced org.  `namespaced_org` defaults to False to be backwards compatible with previous functionality.
* New task `push_list` supports easily pushing a list of OrgIds via the Push API from the CLI: `cci task run push_list -o file <file_path> -o version 1.2 --org packaging`


2.0.0-beta64 (2017-09-29)
-------------------------

* Show proper exit status for failed tests in heroku_ci.sh
* Handle BrowserTestFailure in CLI
* Fix issue that prevented auto-merging master to parent branch

2.0.0-beta63 (2017-09-26)
-------------------------

* Documentation has been updated!
* CumulusCI now supports auto detection of repository information from CI environments.  This release includes an implementation for Heroku CI

2.0.0-beta62 (2017-09-19)
-------------------------

* cci now supports both namespaced and non-namespaced scratch org configurations in the same project.  The default behavior changes slightly with this release.  Before, if the `sfdx-project.json` had a namespace configured, all scratch orgs created via `cci org scratch` would get the namespace.  With the new functionality, all orgs would by default not have the namespace.  You can configure individual org configs in your project's `cumulusci.yml` file by setting `namespace: True` under `orgs -> scratch -> <org_name>`

2.0.0-beta61 (2017-09-12)
-------------------------

* Fix bug that was causing a forced token refresh with `sfdx force:org:open` at the start of a flow or task run against a freshly created scratch org.
* Add support for Big Objects with `__b` suffix in `update_package_xml` and `update_package_xml_managed`
* Fix bug that caused release notes sections to not render if only h2 content found

2.0.0-beta60 (2017-09-06)
-------------------------

* Add support for Platform Events with `__e` suffix in `update_package_xml` and `update_package_xml_managed`

2.0.0-beta59 (2017-09-06)
-------------------------

* `YamlProjectConfig` can now accept an `additional_yaml` keyword argument on initialization.  This allows a 5th level of layering to the `cumulusci.yml` config.  This change is not wired up to the CLI yet but is available for application built on top of cumulusci to use.
* `cumulusci.core.flow` and `cumulusci.core.keychain` now have 100% test coverage

2.0.0-beta58 (2017-08-29)
-------------------------

* Fix import error in `github_release_notes` task introduced in beta57

2.0.0-beta57 (2017-08-28)
-------------------------

* Task options can now dynamically reference attributes from the project_config using the syntax `$project_config.attr_name`.  For example, `$project_config.repo_branch` will resolve to the current branch when the task options are initialized.
* New task `github_parent_to_children` uses new functionality in `MergeBranch` to support merging from a parent feature branch (ex. `feature/parent`) into all child branches (ex. `feature/parent__child`).
* `github_master_to_feature` task will now skip child branches if their corresponding parent branch exists
* `ci_feature` flow now runs `github_parent_to_children` at the end of the flow
* Github task classes were restructured but the `class_path` used in `cumulusci.yml` remains the same
* New test coverage for github tasks


2.0.0-beta56 (2017-08-07)
-------------------------

* Add stderr logging to scratch org info command

2.0.0-beta55 (2017-08-07)
-------------------------

* Fix API version issue in Apex test runner

2.0.0-beta54 (2017-08-04)
-------------------------

* Fix issue in parsing test failure details when org has objects that need to be recompiled.

2.0.0-beta53 (2017-08-04)
-------------------------

* Fix "cci org config_connected_app" for Windows
* Update tutorial for Windows usage
* Reverse pull request order for release notes

2.0.0-beta52 (2017-08-02)
-------------------------

* Release notes parsers now specified in cumulusci.yml

2.0.0-beta51 (2017-08-01)
-------------------------

* New task to commit ApexDoc output
* New test runner uses Tooling API to get limits data

2.0.0-beta50 (2017-07-18)
-------------------------

* Fix handling of boolean command line args

2.0.0-beta49 (2017-07-10)
-------------------------

* New task `batch_apex_wait` allows pausing until an Apex batch job completes.  More details at https://github.com/SFDO-Tooling/CumulusCI/pull/372
* SalesforceBrowserTest task now accepts `extra` argument for specifying extra command line arguments separate from the command itself
* Resolved #369: Scratch org tokens expiring after upgrade to SFDX beta

2.0.0-beta48 (2017-06-28)
-------------------------

* Upgraded to the Salesforce DX Beta (thanks to @Szandor72 for the contribution!)

  * NOTE: CumulusCI will no longer work with the sfdx pilot release after this version!
  * Replaced call to `force:org:describe` with `force:org:display`
  * Changed json response parsing to match beta format

* New SFDX wrapper tasks

  * `SFDXBaseTask`: Use for tasks that don't need org access
  * `SFDXOrgTask`: Use for sfdx tasks that need org access.  The task will refresh the cci keychain org's token and pass it to sfdx as the target org for the command
  * `SFDXJsonTask`: Use for building tasks that interact with sfdx via json responses
  * `SFDXJsonPollingTask`: Use for building tasks that wrap sfdx json responses including polling for task completion
  * `SFDXDeploy`: An example of using `SFDXJsonPollingTask` to wrap `force:mdapi:deploy`

* Fixed infinite loop if setting scratch org password fails

2.0.0-beta47 (2017-06-26)
-------------------------

* Fix typo in tasks.util

2.0.0-beta46 (2017-06-23)
-------------------------

* Fix bug in implementation of the `--no-prompt` flag when sentry is configured

2.0.0-beta45 (2017-06-23)
-------------------------

* The new `BaseSalesforceApiTask` class replaces `BaseSalesforceApiTask`, `BaseSalesforceBulkApiTask`, and `BaseSalesforceToolingApiTask` by combining them into a single task class with access to all 3 API's via `self.sf`, `self.tooling`, and `self.bulk` from inside a task instance.
* Added integration with sentry.io

  * Use `cci service connect sentry` to enable the sentry service
  * All task execution exceptions will be logged as error events in sentry
  * `cci task run` and `cci flow run` will now show you the url to the sentry event if one was registered and prompt to open in a browser.
  * `cci task run` and `cci flow run` now accept the `--no-prompt` option flag for running in non-interactive mode with the sentry service configured.  Use this if you want to log build errors in sentry but not have builds fail due to a hanging prompt.

* If a scratch org password has expired, it is now regenerated when calling `cci org info`
* New task `unschedule_apex` was added to unschedule background jobs and added to the start of the `dev_org` flow
* `update_meta_xml` task now uses the project's dependencies as the namespace/version to update in the meta.xml files
* The bulkdata mapping now properly supports Record Types
* Fixed a bug with BulkDataQuery where local references weren't getting properly set
* New CumulusCI Branch & Release Overview diagram presention is available at http://developer.salesforce.org/CumulusCI/diagram/process_overview.html  Use left/right arrow buttons on your keyboard to navigate through the presentation.
* CumulusCI is now being built by Heroku CI using the config in `app.json`


2.0.0-beta44 (2017-06-09)
-------------------------

* Fix issue in `update_dependencies` when a github dependency depends on another github dependency

2.0.0-beta43 (2017-06-09)
-------------------------

* Fix issue in `mrbelvedere_publish` where the new zip_url dependencies weren't being skipped

2.0.0-beta42 (2017-06-09)
-------------------------

* Move github dependency resolution logic into project_config.get_static_dependencies() for reuse in tasks other than UpdateDependencies
* Fixed the mrbelvedere_publish task when using github references
* Improved output from parsing github dependencies
* Fix issue in `BulkDataQuery` character encoding when value contains utf8 special characters

2.0.0-beta41 (2017-06-07)
-------------------------

* The `dependencies` section in cumulusci.yml now supports the `skip` option for Github dependencies which can be used to skip specific subfolders under `unpackaged/` in the target repository
* New task class BulkDataQuery reverses the BulkDataLoad and uses the mapping to build SOQL queries to capture the data in the mapping from the target org.  The data is written to a database that can then be used by BulkDataLoad to load into a different org.
* The Delete util task now uses the glob library so it can support paths with wildcards like src/*
* New tasks `meta_xml_api` and `meta_xml_dependencies` handle updating `*-meta.xml` files with api versions or underlying package versions.

2.0.0-beta40 (2017-06-03)
-------------------------

* More enhancements to `update_dependencies` including the ability to handle namespace injection, namespace stripping, and unmanaged versions of managed repositories.  See the new doc at http://cumulusci.readthedocs.io/en/latest/dependencies.html

2.0.0-beta39 (2017-06-02)
-------------------------

* Fix new bug in `update_dependencies` which caused failure when running against an org that already has a required package installed

2.0.0-beta38 (2017-06-01)
-------------------------

* `update_dependencies` now properly handles references to a github repository that itself contains dependencies in its cumulusci.yml file
* `update_dependencies` now handles deploying unmanaged metadata from subfolders under unpackaged/pre of a referenced Github repository
* The `dependencies` section of `cumulusci.yml` now supports installing from a zip of metadata hosted at a url if you provide a `zip_url` and optionally a `subfolder`

2.0.0-beta37 (2017-06-01)
-------------------------

* `update_dependencies` now supports dynamically referencing other Github repositories configured with a cumulusci.yml file.  The referenced repository's cumulusci.yml is parsed and the dependencies are included.  Also, the Github API is used to find the latest release of the referenced repo if the cumulusci.yml has a namespace configured.  Welcome to dynamic package dependency management ;)
* `cci task run` now supports the option flags `--debug-before` and `--debug-after`
* Fix for JUnit output rendering in run_tests


2.0.0-beta36 (2017-05-19)
-------------------------

* Flows can now accept arguments in the CLI to override task options

  * `cci flow run install_beta -o install_managed_beta__version "1.0 (Beta 123)"`

* Flows can now accept arguments to in the CLI to skip tasks

  * `cci flow run ci_feature --skip run_tests_debug --skip deploy_post`

* Anonymous apex failures will now throw an exception and fail the build in `execute_anon`
* Fixes #322: local variable 'message' referenced before assignment

2.0.0-beta35 (2017-05-19)
-------------------------

* New task `execute_anon` is available to run anonymous apex and takes the extra task option `apex`

2.0.0-beta34 (2017-05-16)
-------------------------

* Fixes #317: ERROR: Invalid version specified

2.0.0-beta33 (2017-05-11)
-------------------------

* cci org connect and cci org scratch now accept the --default option flag to set the newly connected org as the default org for the repo
* cci org scratch now accepts a new option, --devhub <username>, which allows you to specify an alternate devhub username to use when creating the scratch org
* The SalesforceBrowserTest class now throws a BrowserTestFailure if the command returns an exit status of 1
* Scratch org creation no longer throws an exception if it fails to set a random password on the newly created org
* Push API task enhancements:

  * Push org lists (text files with one org ID per line) can now have comments and blank lines. The first word on the line is assumed to be the org ID and anything after that is ignored.
  * Fixes #294
  * Fixes #306
  * Fixes #208

2.0.0-beta32 (2017-05-04)
-------------------------

* Scratch orgs now get an auto-generated password which is available via `cci org info`
* Added metadata mapping for StandardValueSets to fix #310
* Throw nicer exceptions when scratch org interaction fails

2.0.0-beta31 (2017-04-12)
-------------------------

* Use UTC for all Salesforce API date/time fields
* Fix issue with listing metadata types
* Add generic polling method to BaseTask

2.0.0-beta30 (2017-04-04)
-------------------------

* New task list_metadata_types
* [push upgrades] Fix push request status Cancelled --> Canceled
* [push upgrades] Fix datetime namespace issues
* [pyinstaller] Import project-level modules with run-time hook

2.0.0-beta29 (2017-04-04)
-------------------------

* Report push status if start time is less than 1 minute in the future

2.0.0-beta28 (2017-03-30)
-------------------------

* Fix bug in Push API batch retry logic introduced in beta25

2.0.0-beta27 (2017-03-29)
-------------------------

* Skip org in push if statusCode is UKNOWN_EXCEPTION

2.0.0-beta26 (2017-03-29)
-------------------------

* Fixes #278: Push upgrade raises exception for DUPLICATE_VALUE statusCode

2.0.0-beta25 (2017-03-28)
-------------------------

* Fixes #277: Push API tasks now correctly handle errors in individual orgs in a batch when scheduling a push job

2.0.0-beta24 (2017-03-27)
-------------------------

* Fixes #231: Handle unicode in package.xml generation
* Fixes #239: Replace fix for windows path issues from beta23 with a better implementation
* Fixes #275: Properly pass purge_on_delete option value in uninstall_packaged_incremental

2.0.0-beta23 (2017-03-22)
-------------------------

* Fixes #239: Add local path to import path when looking up classes.  This should fix an error that appeared only in Windows

2.0.0-beta22 (2017-03-20)
-------------------------

* `github_release_notes` now supports the `link_pr` option to add links to the pull request where each line of content came from
* Fixes #266: `update_dependencies` now supports the `purge_on_delete` option to allow running against production orgs
* Fixes #267: package.xml generation now skips RecordType when rendering in delete mode

2.0.0-beta21 (2017-03-17)
-------------------------

* Fix parsing of OrgId from the access token using the new sfdx CLI

2.0.0-beta20 (2017-03-17)
-------------------------

* Switch to using the `sfdx` CLI for interacting with scratch orgs.  If you use `cci` with scratch orgs, this release will no longer work with the `heroku force:*` commands from the prior Salesforce DX release.
* Upgrades to release notes generator
  * Content is now grouped by subheading under each heading
  * Better error message is thrown if a lightweight tag is found when an annotated tag is needed

2.0.0-beta19 (2017-03-15)
-------------------------

* Fixes #261: cci org info should refresh token first

2.0.0-beta18 (2017-03-14)
-------------------------

* Skip deleting Scontrols in incremental delete
* Escape package name when generating package.xml

2.0.0-beta17 (2017-03-14)
-------------------------

* OrgConfig and subclasses now support self.username to get the username
* Flows no longer have access to task instance attributes for subsequent task options. Instead, custom task classes should set their task return_values member.
* Improve printing of org info when running tasks from a flow by only printing once at the start of flow.  All tasks have an optional self.flow attribute now that contains the flow instance if the task is being run from a flow.
* BaseTask now includes methods for handling retry logic.  Implemented in the InstallPackageVersion and RunApexTests
* New task `retrieve_unpackaged` can be used to retrieve metadata from a package.xml manifest
* Fixes #240 - CumulusCI should now properly handle escaping special characters in xml where appropriate
* Fixes #245 - Show config values in task info
* Fixes #251 - ApiRetrieveUnpackaged _clean_package_xml() can't handle metadata with spaces in names
* Fixes #255 - ApiListMetadata does not list certain metadata types with default folder value

2.0.0-beta16 (2017-02-17)
-------------------------

* Allow batch size to be configured for push jobs with the `batch_size` job

2.0.0-beta15 (2017-02-15)
-------------------------

* Bug fix release for bug in `update_admin_profile` from the beta 14 release changes to the ApiRetrieveUnpackaged class

2.0.0-beta14 (2017-02-15)
-------------------------

* The new `RetrieveReportsAndDashboards` task class that can retrieve all reports and dashboards from a specified list of folders
* Documentation improvements contributed by @tet3
* Include userinfo in the OrgConfig, and print username and org id at the beginning of every task run.  Contribution by @cdcarter
* `project_local_dir` (e.g., `~/.cumulusci/NPSP-Extension-Template/`, home of the encrypted keychain and local override config) now rely on the project name configured in cumulusci.yml instead of the existence of a git remote named origin.  Contribution by @cdcarter

2.0.0-beta13 (2017-02-09)
-------------------------

* New services registration support added by community contribution from @cdcarter

  * Services and their schemas can now be defined in the cumulusci.yml file.  See https://github.com/SFDO-Tooling/CumulusCI/issues/224 for more details until docs are fully updated
  * `cci services list`
  * `cci services show github`
  * `cci services connect github`

* Improved error handling for metadata deployment failures:

  * Metadata deployments now throw more specific errors when appropriate: MetadataComponentFailure, ApexTestFailure, or MetadataApiError
  * Output for each component failure on a deploy now includes more information such as the column number of the error

* `release_beta` now ignores errors in the `github_release_notes` process by default

2.0.0-beta12 (2017-02-02)
-------------------------

* Throw better exceptions if there are failures creating or deleting scratch orgs

2.0.0-beta11 (2017-02-01)
-------------------------

* Fixes and new functionality for `update_package_xml_managed` task.

  * Added support for project -> package -> name_managed in the cumulusci.yml file to specify a different package name to use when deploying to the packaging org.
  * Fixed bug with install_class and uninstall_class handling

2.0.0-beta10 (2017-01-20)
-------------------------

* Completed removed CumulusCI 1 code from the repository and egg.  The egg should be 17MB smaller now.
* Removed `cumulusci.tasks.ant.AntTask`.  Please replace any usage with `cumulusci.tasks.command.Command` or `cumulusci.tasks.command.SalesforceCommand`
* Removed the `update_meta_xml` task for now since it was the only task relying on Ant.  A new and much better Python based implementation will be coming soon.

2.0.0-beta9 (2017-01-20)
------------------------

* A few upgrades to the Command task:

  * No longer strip left side whitespace from output to preserve indentation
  * New method `_process_output` can be overridden to change how output lines are processed
  * New method `_handle_returncode` can be overridden to change how exit status is handled

2.0.0-beta8 (2017-01-19)
------------------------

* Added new task classes util.DownloadZip, command.SalesforceCommand, and command.SalesforceBrowserTestCommand that can be mapped in individual projects to configure browser tests or other commands run against a Salesforce org.  The commands are automatically passed a refreshed `SF_ACCESS_TOKEN` and `SF_INSTANCE_URL` environment variables.
* Added new CLI commands `cci project connect_saucelabs` and `cci project show_saucelabs`
* Added `ci_install_beta` flow that uninstalls the previous managed version then installs the latest beta without running apex tests
* Added new method cumulusci.utils.download_extract_zip to download and extract a zip including re-rooting the zip to a subfolder.
* All Salesforce tasks now delete any tempdirs they create to prevent wasting disk space

2.0.0-beta7 (2017-01-17)
------------------------

* `run_tests_debug` now ignores all non-test methods including any method decorated with @testSetup

2.0.0-beta6 (2017-01-17)
------------------------

* Return full info when a component failure occurs on a Metadata API deployment.  Previously only the problem was shown without context like file name and line number making it difficult to figure out what caused the failure.
* `run_tests_debug` now ignores the @testSetup method when parsing debug logs.  Previously it would throw an error if tests used @testSetup

2.0.0-beta5 (2017-01-16)
------------------------

* Fixes for the `unmanaged_ee` flow to fix a bug where avialableFields elements were not properly being stripped from fieldsSets in .object files
* Fixes for `github_master_to_feature` where merge conflicts would throw exception rather than creating a pull request as expected

2.0.0-beta4 (2017-01-13)
------------------------

* Add `update_admin_profile` to all flows that deploy or install to a Salesforce org.  Note that this adjusted the task numbers in some flows so you should double check your project specific flow customizations.

2.0.0-beta3 (2017-01-13)
------------------------

* Remove `deploy_post_managed` task from the default `ci_master` flow.  Deploying the unpackaged/post content to the packaging org risks the spider accidentally including some of it in the package.  Projects that want to run `deploy_post_managed` against the packaging org can extend `ci_master` in their cumulusci.yml file to add it.

2.0.0-beta2 (2017-01-12)
------------------------

* Fix a bug in project_config.get_latest_version() with tags that don't match either the beta or release prefix.

2.0.0-beta1 (2017-01-12)
------------------------

* Move into the master branch!
* Changed primary CLI command to `cci` and left `cumulusci2` available for legacy support
* Changed all docs to use `cci` command in examples
* Peg push api tasks to api version 38.0 rather than project api version
* Added 2 new flows: `install_beta` and `install_prod` which install the latest managed version of the package with all dependencies but without running tests
* `release_beta` flow now runs `github_master_to_feature` at the end of the flow

2.0.0-alpha42 (2017-01-10)
--------------------------

* Metadata API calls now progressively wait longer between each status check to handle calls with long Pending times.  Each check also now outputs a line saying how long it will sleep before the next check.

2.0.0-alpha41 (2017-01-06)
--------------------------

* Fix bug in `uninstall_packaged_incremental` where the task would error out if no metadata was found to delete

2.0.0-alpha40 (2017-01-06)
--------------------------

* `uninstall_packaged_incremental` task now skips the deploy step if now metadata was found to be deleted

2.0.0-alpha39 (2017-01-06)
--------------------------

* Two new task classes exist for loading and deleting data via Bulk API.  Note that there are no default task mappings for these classes as the mappings should be project specific.  Define your own mappings in your project's cumulusci.yml file to use them.

  * **cumulusci.tasks.bulkdata.LoadData**: Loads relational data from a sqlite database into Salesforce objects using a yaml file for mapping
  * **cumulusci.tasks.bulkdata.DeleteData**: Deletes all records from specified objects in order of object list

* Added support for customPermissions
* Added new Command task that can be used to call arbitrary commands with configurable environment variables

2.0.0-alpha38 (2016-12-28)
--------------------------

* Scratch orgs now cache the org info locally during flow execution to prevent multiple calls out to the Heroku CLI that are unnecessary
* Scratch org calls now properly capture and print both stdout and stderr in the case of an exception in calls to Heroku CLI
* `run_tests_debug` now deletes existing TraceFlag objects in addition to DebugLevels
* Fix bug in `push_all` and `push_sandbox`
* Push tasks now use timezone for start_date option

2.0.0-alpha37 (2016-12-20)
--------------------------

* `github_release_notes` now correctly handles the situation where a merge commit's date can be different than the PR's merged_at date in Github by comparing commit sha's

2.0.0-alpha36 (2016-12-20)
--------------------------

* `github_release` now works with an existing tag/ref and sleeps for 3 seconds after creating the tag to allow Github time to catch up

2.0.0-alpha35 (2016-12-20)
--------------------------

* Remove `draft` option from `github_release` since the Github API doesn't support querying draft releases

2.0.0-alpha34 (2016-12-20)
--------------------------

* Fix bug with `github_release` that was causing validation errors from Github

2.0.0-alpha33 (2016-12-20)
--------------------------

* `github_release_notes` now raises an exception in `publish` mode if the release doesn't exist instead of attempting to create it.  Use `github_release` to create the release first before calling `github_release_notes`
* Fix a bug with dynamic task option lookup in flows

2.0.0-alpha32 (2016-12-19)
--------------------------

* Move logger configuration out of core and into CLI so other implementations can provide their own logger configurations
* Added `retry_interval` and `retry_interval_add` options to `install_beta` to introduce a progressive delay between retry attempts when the package is unavailable

2.0.0-alpha30 (2016-12-13)
--------------------------

* **IMPORANT** This release changes the yaml structure for flows.  The new structure now looks like this::

    flows:
        flow_name:
            tasks:
                1:
                    task: deploy
                2:
                    task: run_tests

* See the new flow customization examples in the cookbook for examples of why this change was made and how to use it: http://cumulusci.readthedocs.io/en/latest/cookbook.html#custom-flows-via-yaml


2.0.0-alpha30 (2016-12-12)
--------------------------

* Bug fixes submitted by @ccarter:

  * `uninstall_post` was failing to substitute namespaces
  * new util method `findRename` to rename files with a token in their name

* Bug fix with Unicode handling in run_tests_debug

2.0.0-alpha29 (2016-12-12)
--------------------------

* Require docutils to supprot rst2ansi

2.0.0-alpha28 (2016-12-12)
--------------------------

* Modified tasks and flows to properly re-raise exceptions

2.0.0-alpha27 (2016-12-12)
--------------------------

* `cci` should now throw the direct exception rather than making it look like the exception came through click
* `cci task doc` command outputs RST format documentation of all tasks
* New doc with info on all tasks: http://cumulusci.readthedocs.io/en/latest/tasks.html

2.0.0-alpha26 (2016-12-09)
--------------------------

* Bug fix, missing import of re in core/config.py

2.0.0-alpha25 (2016-12-09)
--------------------------

* Fixed run_tests and run_tests_debug tasks to fail throwing an exception on test failure
* run_tests_debug now stores debug logs in a tempdir
* Have the CLI handle ApexTestException events with a nicer error rather than a full traceback which isn't helpful to determining the apex failure
* BaseMetadataApi will now throw MetadataApiError after a Failed status is set
* BaseFlow now throws the original exception rather than a more generic one that obscures the actual failure

2.0.0-alpha24 (2016-12-09)
--------------------------

* Bug fix release, flow_run in the CLI should accept debug argument and was throwing and error

2.0.0-alpha23 (2016-12-09)
--------------------------

* `cci org browser` now saves the org back to the keychain.  This fixes an issue with scratch orgs where a call to org browser on a scratch org that hasn't been created yet gets created but doesn't persist after the command

* `task run` and `flow run` now support the `--debug` flag which will drop you into the Python interactive debugger (pdb) at the point of the exception.

* Added Cookbook to the docs: http://cumulusci.readthedocs.io/en/latest/cookbook.html

* `flow run` with the `--delete-org` option flag and scratch orgs no longer fails the flow if the delete org call fails.

* Fixed the `deploy_post` task which has having errors with namespaced file names

* Fixed `update_admin_profile` to properly update the profile.  This involved fixing the utils `findReplace` and `findReplaceRegex`.

* Reworked exceptions structure and ensure that tasks throw an exception where approriate.

2.0.0-alpha22 (2016-12-02)
--------------------------

* Fix for bug in deploy_post when using the filename token to merge namespace into a filename

2.0.0-alpha21 (2016-12-01)
--------------------------

* Added support for global and project specific orgs, services, and connected app.  The global credentials will be used by default if they exist and individual projects an override them.

  * Orgs still default to creating in the project level but the `--global` flag can be used in the CLI to create an org

  * `config_connected_app` command now sets the connected app as global by default.  Use the '--project' flag to set as a project override

  * `connect_github`, `connect_mrbelvedere`, and `connect_apextestsdb` commands now set the service as global by default.  Use the '--project' flag to set as a project override

2.0.0-alpha20 (2016-11-29)
--------------------------

* Remove pdb from BaseFlow.__call__ (oops)

2.0.0-alpha19 (2016-11-29)
--------------------------

* Fix IOError issue with update_admin_profile when using the egg version
* Changed cci task_run and flow_run commands to no longer swallow unknown exceptions so a useful error message with traceback is shown
* Centralized loggers for BaseConfig, BaseTask, and BaseFlow under cumulusci.core.logger and changed logs to always write to a temp file available as self.log_file on any config, task, or flow subclass.

2.0.0-alpha18 (2016-11-17)
--------------------------

* New task `apextestsdb_upload` uploads json test data to an instance of ApexTestsDB
* Fixed bug in CLI when running tasks that don't require an org
* Include mappings for Community Template metadata types in package.xml generator

2.0.0-alpha17 (2016-11-15)
--------------------------

* Community contributions by @cdcarter

  * `query` task using the Bulk Data API
  * `--login-url` option on `cci org connect`

* Salesforce DX wrapper

  * NOTE: Requires developer preview access to Salesforce DX
  * `cci org scratch <config_name> <org_name>` creates a wrapper for a scratch org in your keychain
  * Tasks and Flows run against a scratch org will create the scratch org if needed
  * `cci org scratch_delete <org_name>` deletes a scratch org that was created by running a task or flow
  * `cci flow run` now supports the `--delete-org` option to delete a scratch org at the end of the flow
  * `BaseSalesforceDXTask` wraps the heroku force:* commands.  The `dx_push` task is provided as an example.

    * NOTE: Currently the command output is buffered and only outputs when the command completes.

* Integration with mrbelvedere

  * `mrbelvedere_publish` task publishes a beta or release tag to an existing package on mrbelvedere

* Flow changes

    * `ci_feature` now runs tests as part of the flow
    * New flow task configuration `ignore_failure` can be used to ignore a failure from a particular task in the flow

* CUMULUSCI_KEY is no longer required if using a keychain class with the encrypted attribute set to False such as the EnvironmentProjectKeychain
* Refactored OAuth token refresh to be more centralized and raise a proper exception if there is an issue
* The org keychain now correctly uses the instance url when appropriate
* Calls to runTestsAsynchronous in the Tooling API are now done via POST instead of GET

2.0.0-alpha16 (2016-11-3)
-------------------------

* Fix bug in SOAP calls to MDAPI with newer versions of the requests library
* This version was used to record the demo screencast: https://asciinema.org/a/91555

2.0.0-alpha15 (2016-11-3)
-------------------------

* Fix CLI bug in new exception handling logic

2.0.0-alpha14 (2016-11-3)
-------------------------

* Fix version number
* Fix bug in BaseSalesforceBulkApiTask (thanks @cdcarter)

2.0.0-alpha13 (2016-11-3)
-------------------------

* Nicer log output from tasks and flows using `coloredlogs`
* Added handling for packed git references in the file .git/packed-refs
* Docs now available at http://cumulusci.readthedocs.io
* Tasks and Flows run through the CLI now show a more simple message if an exception is thrown

2.0.0-alpha12 (2016-11-2)
-------------------------

* Automatic detection of latest production and beta release via Github Releases

  * project_config.get_latest_release() added to query Github Releases to find the latest production or beta release version
  * InstallPackage now accepts the virtual versions 'latest' and 'latest_beta' as well as specific versions for the version option

* New flows:

  * ci_feature: Runs a full deployment of the unmanaged code for testing in a feature org
  * ci_master: Runs a full deployment of the managed version of the code into the packaging org
  * ci_beta: Installs the latest beta and runs all tests
  * ci_release: Installs the latest release and runs all tests
  * release_beta: Uploads a beta release of the metadata in the packaging org, creates a Github Release, and generates release notes

* Removed the hard coded slots in the keychain for github, mrbelvedere, and apextestsdb and replaced with a more generic concept of named keychain services.  keychain.get_service('name') retrieves a named service.  The CLI commands for setting github, mrbelvedere, and apextestsdb were modified to write the service configs to the new structure.

* Flow tasks can now access previous tasks' attributes in their options definitions.  The syntax is ^^task_name.attr1.attr2

* Flow output is now nicer showing the flow configuration and the active configuration for each task before execution

* New tasks

  * update_package_xml_managed: Create a new package.xml from the metadata in src/ with attributes only available when deploying to packaging org
  * run_tests: Runs matching apex tests in parallel and generate a JUnit report
  * run_tests_debug: Runs matching apex tests in parallel, generates JUnit report, captures debug logs, and parses debug logs for limits usage outputing results to test_results.json
  * run_tests_managed: Runs matching apex tests in parallel from the package's namespace and generate a JUnit report


2.0.0-alpha11 (2016-10-31)
--------------------------

* project_config.repo_root is now added to the python syspath, thanks @cdcarter for the contribution
* Tasks for the new Package Upload API

  * upload_beta: Uploads a beta release of the metadata currently in the packaging org
  * upload_production: Uploads a production release of the metadata currently in the packaging org

* Dependency management for managed packages:

  * update_dependencies: Task that ensures the target org has all dependencies installed at the correct version
  * Dependencies are configured using the dependencies: heading in cumulusci.yml under the project: section

* Integrated salesforce-bulk and created BaseSalesforceBulkApiTask for building bulk data tasks

* Added `cci version` command to print out current package version, thanks @cdcarter for the contribution


2.0.0-alpha10 (2016-10-28)
--------------------------

* More pure Python tasks to replace ant targets:

  * create_ee_src
  * retrieve_packaged
  * retrieve_src
  * revert_ee_src
  * uninstall_packaged_incremental
  * update_admin_profile

* New flow:

  * unmanaged_ee: Deploys unmanaged code to an EE org

* New cumulusci.utils

  * CUMULUSCI_PATH: The absolute path to the root of CumulusCI
  * findReplaceRegex: Recursive regex based search/replace for files
  * zip_subfolder: Accepts a zipfile and path, returns a zipfile with path as root

* Fix bug where repo_name was not being properly handled if it origin ended in .git

2.0.0-alpha9 (2016-10-27)
-------------------------

* Switch to using `plaintable` for printing text tables in the following CLI commands:

  * cci org list
  * cci task list
  * cci task info
  * cci flow list

* Easier project set up: `cci project init` now prompts for all project values using the global default values
* More pure Python Metadata API tasks:

  * create_package
  * install_package
  * uninstall_managed
  * uninstall_packaged
  * uninstall_pre
  * uninstall_post
  * uninstall_post_managed

* New tasks to interact with the new PackageUploadRequest object in the Tooling API

  * upload_beta
  * upload_production

* Python task to replace deployUnpackagedPost ant target with support for replacing namespace prefix in filenames and file contents

  * deploy_post
  * deploy_post_managed

* Python tasks to replace createManagedSrc and revertManagedSrc ant targets

  * create_managed_src
  * revert_managed_src

2.0.0-alpha8 (2016-10-26)
-------------------------

* New tasks for push upgrading packages

  * push_all: Pushes a package version to all available subscriber orgs

    * ex: cci task run --org packaging -o version 1.1 push_all

  * push_qa: Pushes a package version to all org ids in the file push/orgs_qa.txt in the repo

    * ex: cci task run --org packaging -o version 1.1 push_qa

  * push_sandbox: Pushes a package version to all available sandbox subscriber orgs

    * ex: cci task run --org packaging -o version 1.1 push_sandbox

  * push_trial: Pushes a package version to all org ids in the file push/orgs_trial.txt in the repo

    * ex: cci task run --org packaging -o version 1.1 push_trial

  * Configurable push tasks in cumulusci.tasks.push.tasks:

    * SchedulePushOrgList: uses a file with one OrgID per line as the target list
    * SchedulePushOrgQuery: queries PackageSubscribers to select orgs for the target list

  * Additional push tasks can be built by subclassing cumulusci.tasks.push.tasks.BaseSalesforcePushTask


2.0.0-alpha7 (2016-10-25)
-------------------------

* New commands for connecting to other services

  * cci project connect_apextestsdb: Stores ApexTestDB auth configuration in the keychain for use by tasks that require ApexTestsDB access
  * cci project connect_github: Stores Github auth configuration in the keychain for use by tasks that require Github access
  * cci project connect_mrbelvedere: Stores mrbelvedere auth configuration in the keychain for use by tasks that require access to mrbelvedere
  * cci project show_apextestsdb: Shows the configured ApexTestsDB auth info
  * cci project show_github: Shows the configured Github auth info
  * cci project show_mrbelvedere: Shows the configured mrbelvedere auth info

* Github Tasks

  * The new BaseGithubTask wraps the github3.py API library to allow writing tasks targetting Github
  * The following new Github tasks are implemented on top of BaseGithubTask:

    * github_clone_tag: Clones one git tag to another via the Github API
    * github_master_to_feature: Merges the HEAD commit on master to all open feature branches via the Github API
    * github_release: Creates a Release via the Github API
    * github_release_notes: Generates release notes by parsing merged Github pull request bodies between two tags

* BaseTask now enforces required task_options raising TaskOptionError if required options are missing
* Restructured the project: heading in cumulusci.yml

2.0.0-alpha6 (2016-10-24)
-------------------------

* Moved the build and ci directories back to the root so 2.0 is backwards compatible with 1.0
* Allow override of keychain class via CUMULUSCI_KEYCHAIN_CLASS env var
* New keychain class cumulusci.core.keychain.EnvironmentProjectKeychain for storing org credentials as json in environment variables
* Tasks now support the salesforce_task option for requiring a Salesforce org
* The new BaseSalesforceToolingApi task wraps simple-salesforce for building tasks that interact with the Tooling API
* cumulusci org default <name>

  * Set a default org for tasks and flows
  * No longer require passing org name in task run and flow run
  * --unset option flag unsets current default
  * cumulusci org list shows a * next to the default org

* BaseAntTask split out into AntTask and SalesforceAntTask
* cumulusci.tasks.metadata.package.UpdatePackageXml:

  * Pure python based package.xml generation controlled by metadata_map.yml for mapping in new types
  * Wired into the update_package_xml task instead of the old ant target

* 130 unit tests and counting, and our test suite now exceeds 1 second!

2.0.0-alpha5 (2016-10-21)
-------------------------

* Update README

2.0.0-alpha4 (2016-10-21)
-------------------------

* Fix imports in tasks/ant.py

2.0.0-alpha3 (2016-10-21)
-------------------------

* Added yaml files to the MANIFEST.in for inclusion in the egg
* Fixed keychain import in cumulusci.yml

2.0.0-alpha2 (2016-10-21)
-------------------------

* Added additional python package requirements to setup.py for automatic installation of dependencies

2.0.0-alpha1 (2016-10-21)
-------------------------

* First release on PyPI.
