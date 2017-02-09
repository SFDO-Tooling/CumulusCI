=======
History
=======

2.0.0-beta13 (2017-02-09)
------------------------

* New services registration support added by community contribution from @cdcarter

  * Services and their schemas can now be defined in the cumulusci.yml file.  See https://github.com/SalesforceFoundation/CumulusCI/issues/224 for more details until docs are fully updated
  * `cci services list`
  * `cci services show github`
  * `cci services connect github`

* Improved error handling for metadata deployment failures:

  * Metadata deployments now throw more specific errors when appropriate: MetadataComponentFailure, ApexTestFailure, or MetadataApiError
  * Output for each component failure on a deploy now includes more information such as the column number of the error

* `release_beta` now ignores errors in the `github_release_notes` process by default

2.0.0-beta12 (2017-02-02)
------------------------

* Throw better exceptions if there are failures creating or deleting scratch orgs

2.0.0-beta11 (2017-02-01)
------------------------

* Fixes and new functionality for `update_package_xml_managed` task.

  * Added support for project -> package -> name_managed in the cumulusci.yml file to specify a different package name to use when deploying to the packaging org.
  * Fixed bug with install_class and uninstall_class handling

2.0.0-beta10 (2017-01-20)
------------------------

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
------------------

* Metadata API calls now progressively wait longer between each status check to handle calls with long Pending times.  Each check also now outputs a line saying how long it will sleep before the next check.

2.0.0-alpha41 (2017-01-06)
------------------

* Fix bug in `uninstall_packaged_incremental` where the task would error out if no metadata was found to delete

2.0.0-alpha40 (2017-01-06)
------------------

* `uninstall_packaged_incremental` task now skips the deploy step if now metadata was found to be deleted

2.0.0-alpha39 (2017-01-06)
------------------

* Two new task classes exist for loading and deleting data via Bulk API.  Note that there are no default task mappings for these classes as the mappings should be project specific.  Define your own mappings in your project's cumulusci.yml file to use them.

  * **cumulusci.tasks.bulkdata.LoadData**: Loads relational data from a sqlite database into Salesforce objects using a yaml file for mapping
  * **cumulusci.tasks.bulkdata.DeleteData**: Deletes all records from specified objects in order of object list

* Added support for customPermissions
* Added new Command task that can be used to call arbitrary commands with configurable environment variables

2.0.0-alpha38 (2016-12-28)
------------------

* Scratch orgs now cache the org info locally during flow execution to prevent multiple calls out to the Heroku CLI that are unnecessary
* Scratch org calls now properly capture and print both stdout and stderr in the case of an exception in calls to Heroku CLI
* `run_tests_debug` now deletes existing TraceFlag objects in addition to DebugLevels
* Fix bug in `push_all` and `push_sandbox`
* Push tasks now use timezone for start_date option

2.0.0-alpha37 (2016-12-20)
------------------

* `github_release_notes` now correctly handles the situation where a merge commit's date can be different than the PR's merged_at date in Github by comparing commit sha's

2.0.0-alpha36 (2016-12-20)
------------------

* `github_release` now works with an existing tag/ref and sleeps for 3 seconds after creating the tag to allow Github time to catch up

2.0.0-alpha35 (2016-12-20)
------------------

* Remove `draft` option from `github_release` since the Github API doesn't support querying draft releases

2.0.0-alpha34 (2016-12-20)
------------------

* Fix bug with `github_release` that was causing validation errors from Github

2.0.0-alpha33 (2016-12-20)
------------------

* `github_release_notes` now raises an exception in `publish` mode if the release doesn't exist instead of attempting to create it.  Use `github_release` to create the release first before calling `github_release_notes`
* Fix a bug with dynamic task option lookup in flows

2.0.0-alpha32 (2016-12-19)
------------------

* Move logger configuration out of core and into CLI so other implementations can provide their own logger configurations
* Added `retry_interval` and `retry_interval_add` options to `install_beta` to introduce a progressive delay between retry attempts when the package is unavailable

2.0.0-alpha30 (2016-12-13)
------------------

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
------------------

* Bug fixes submitted by @ccarter:
  
  * `uninstall_post` was failing to substitute namespaces
  * new util method `findRename` to rename files with a token in their name

* Bug fix with Unicode handling in run_tests_debug

2.0.0-alpha29 (2016-12-12)
------------------

* Require docutils to supprot rst2ansi

2.0.0-alpha28 (2016-12-12)
------------------

* Modified tasks and flows to properly re-raise exceptions

2.0.0-alpha27 (2016-12-12)
------------------

* `cci` should now throw the direct exception rather than making it look like the exception came through click
* `cci task doc` command outputs RST format documentation of all tasks
* New doc with info on all tasks: http://cumulusci.readthedocs.io/en/latest/tasks.html

2.0.0-alpha26 (2016-12-09)
------------------

* Bug fix, missing import of re in core/config.py

2.0.0-alpha25 (2016-12-09)
------------------

* Fixed run_tests and run_tests_debug tasks to fail throwing an exception on test failure
* run_tests_debug now stores debug logs in a tempdir
* Have the CLI handle ApexTestException events with a nicer error rather than a full traceback which isn't helpful to determining the apex failure
* BaseMetadataApi will now throw MetadataApiError after a Failed status is set
* BaseFlow now throws the original exception rather than a more generic one that obscures the actual failure

2.0.0-alpha24 (2016-12-09)
------------------

* Bug fix release, flow_run in the CLI should accept debug argument and was throwing and error

2.0.0-alpha23 (2016-12-09)
------------------

* `cci org browser` now saves the org back to the keychain.  This fixes an issue with scratch orgs where a call to org browser on a scratch org that hasn't been created yet gets created but doesn't persist after the command

* `task run` and `flow run` now support the `--debug` flag which will drop you into the Python interactive debugger (pdb) at the point of the exception.

* Added Cookbook to the docs: http://cumulusci.readthedocs.io/en/latest/cookbook.html

* `flow run` with the `--delete-org` option flag and scratch orgs no longer fails the flow if the delete org call fails.

* Fixed the `deploy_post` task which has having errors with namespaced file names

* Fixed `update_admin_profile` to properly update the profile.  This involved fixing the utils `findReplace` and `findReplaceRegex`.

* Reworked exceptions structure and ensure that tasks throw an exception where approriate.

2.0.0-alpha22 (2016-12-02)
------------------

* Fix for bug in deploy_post when using the filename token to merge namespace into a filename

2.0.0-alpha21 (2016-12-01)
------------------

* Added support for global and project specific orgs, services, and connected app.  The global credentials will be used by default if they exist and individual projects an override them.

  * Orgs still default to creating in the project level but the `--global` flag can be used in the CLI to create an org

  * `config_connected_app` command now sets the connected app as global by default.  Use the '--project' flag to set as a project override

  * `connect_github`, `connect_mrbelvedere`, and `connect_apextestsdb` commands now set the service as global by default.  Use the '--project' flag to set as a project override

2.0.0-alpha20 (2016-11-29)
------------------

* Remove pdb from BaseFlow.__call__ (oops)

2.0.0-alpha19 (2016-11-29)
------------------

* Fix IOError issue with update_admin_profile when using the egg version
* Changed cci task_run and flow_run commands to no longer swallow unknown exceptions so a useful error message with traceback is shown
* Centralized loggers for BaseConfig, BaseTask, and BaseFlow under cumulusci.core.logger and changed logs to always write to a temp file available as self.log_file on any config, task, or flow subclass.

2.0.0-alpha18 (2016-11-17)
------------------

* New task `apextestsdb_upload` uploads json test data to an instance of ApexTestsDB
* Fixed bug in CLI when running tasks that don't require an org 
* Include mappings for Community Template metadata types in package.xml generator

2.0.0-alpha17 (2016-11-15)
------------------

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
------------------

* Fix bug in SOAP calls to MDAPI with newer versions of the requests library
* This version was used to record the demo screencast: https://asciinema.org/a/91555

2.0.0-alpha15 (2016-11-3)
------------------

* Fix CLI bug in new exception handling logic

2.0.0-alpha14 (2016-11-3)
------------------

* Fix version number
* Fix bug in BaseSalesforceBulkApiTask (thanks @cdcarter)

2.0.0-alpha13 (2016-11-3)
------------------

* Nicer log output from tasks and flows using `coloredlogs`
* Added handling for packed git references in the file .git/packed-refs
* Docs now available at http://cumulusci.readthedocs.io
* Tasks and Flows run through the CLI now show a more simple message if an exception is thrown

2.0.0-alpha12 (2016-11-2)
------------------

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
------------------

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
------------------

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
------------------

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
------------------

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
------------------

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
------------------

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
------------------

* Update README

2.0.0-alpha4 (2016-10-21)
------------------

* Fix imports in tasks/ant.py 

2.0.0-alpha3 (2016-10-21)
------------------

* Added yaml files to the MANIFEST.in for inclusion in the egg
* Fixed keychain import in cumulusci.yml

2.0.0-alpha2 (2016-10-21)
------------------

* Added additional python package requirements to setup.py for automatic installation of dependencies

2.0.0-alpha1 (2016-10-21)
------------------

* First release on PyPI.
