=======
History
=======

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
