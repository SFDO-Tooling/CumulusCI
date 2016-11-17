=======
History
=======

2.0.0-alpha18 (2016-11-17)
------------------

* New task `apextestsdb_upload` uploads json test data to an instance of ApexTestsDB
* Fixed bug in CLI when running tasks that don't require an org 
* Include mappings for Community Template metadata types in package.xml generator

2.0.0-alpha17 (2016-11-15)
------------------

* Community contributions by @cdcarter

  * `query` task using the Bulk Data API
  * `--login-url` option on `cumulusci2 org connect`

* Salesforce DX wrapper

  * NOTE: Requires developer preview access to Salesforce DX
  * `cumulusci2 org scratch <config_name> <org_name>` creates a wrapper for a scratch org in your keychain
  * Tasks and Flows run against a scratch org will create the scratch org if needed
  * `cumulusci2 org scratch_delete <org_name>` deletes a scratch org that was created by running a task or flow
  * `cumulusci2 flow run` now supports the `--delete-org` option to delete a scratch org at the end of the flow
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

* Added `cumulusci2 version` command to print out current package version, thanks @cdcarter for the contribution


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

  * cumulusci2 org list
  * cumulusci2 task list
  * cumulusci2 task info
  * cumulusci2 flow list

* Easier project set up: `cumulusci2 project init` now prompts for all project values using the global default values
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

    * ex: cumulusci2 task run --org packaging -o version 1.1 push_all

  * push_qa: Pushes a package version to all org ids in the file push/orgs_qa.txt in the repo

    * ex: cumulusci2 task run --org packaging -o version 1.1 push_qa

  * push_sandbox: Pushes a package version to all available sandbox subscriber orgs

    * ex: cumulusci2 task run --org packaging -o version 1.1 push_sandbox

  * push_trial: Pushes a package version to all org ids in the file push/orgs_trial.txt in the repo

    * ex: cumulusci2 task run --org packaging -o version 1.1 push_trial

  * Configurable push tasks in cumulusci.tasks.push.tasks:

    * SchedulePushOrgList: uses a file with one OrgID per line as the target list
    * SchedulePushOrgQuery: queries PackageSubscribers to select orgs for the target list

  * Additional push tasks can be built by subclassing cumulusci.tasks.push.tasks.BaseSalesforcePushTask
  

2.0.0-alpha7 (2016-10-25)
------------------

* New commands for connecting to other services

  * cumulusci2 project connect_apextestsdb: Stores ApexTestDB auth configuration in the keychain for use by tasks that require ApexTestsDB access
  * cumulusci2 project connect_github: Stores Github auth configuration in the keychain for use by tasks that require Github access
  * cumulusci2 project connect_mrbelvedere: Stores mrbelvedere auth configuration in the keychain for use by tasks that require access to mrbelvedere
  * cumulusci2 project show_apextestsdb: Shows the configured ApexTestsDB auth info
  * cumulusci2 project show_github: Shows the configured Github auth info
  * cumulusci2 project show_mrbelvedere: Shows the configured mrbelvedere auth info
  
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
