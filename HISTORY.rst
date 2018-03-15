=======
History
=======

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

* New task `batch_apex_wait` allows pausing until an Apex batch job completes.  More details at https://github.com/SalesforceFoundation/CumulusCI/pull/372
* SalesforceBrowserTest task now accepts `extra` argument for specifying extra command line arguments separate from the command itself
* Resolved #369: Scratch org tokens expiring after upgrade to SFDX beta

2.0.0-beta48 (2017-06-28)
------------------------

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
------------------------

* Fix typo in tasks.util

2.0.0-beta46 (2017-06-23)
------------------------

* Fix bug in implementation of the `--no-prompt` flag when sentry is configured

2.0.0-beta45 (2017-06-23)
------------------------

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
------------------------

* Fix issue in `update_dependencies` when a github dependency depends on another github dependency

2.0.0-beta43 (2017-06-09)
------------------------

* Fix issue in `mrbelvedere_publish` where the new zip_url dependencies weren't being skipped

2.0.0-beta42 (2017-06-09)
------------------------

* Move github dependency resolution logic into project_config.get_static_dependencies() for reuse in tasks other than UpdateDependencies
* Fixed the mrbelvedere_publish task when using github references
* Improved output from parsing github dependencies
* Fix issue in `BulkDataQuery` character encoding when value contains utf8 special characters

2.0.0-beta41 (2017-06-07)
------------------------

* The `dependencies` section in cumulusci.yml now supports the `skip` option for Github dependencies which can be used to skip specific subfolders under `unpackaged/` in the target repository
* New task class BulkDataQuery reverses the BulkDataLoad and uses the mapping to build SOQL queries to capture the data in the mapping from the target org.  The data is written to a database that can then be used by BulkDataLoad to load into a different org.
* The Delete util task now uses the glob library so it can support paths with wildcards like src/*
* New tasks `meta_xml_api` and `meta_xml_dependencies` handle updating `*-meta.xml` files with api versions or underlying package versions.

2.0.0-beta40 (2017-06-03)
------------------------

* More enhancements to `update_dependencies` including the ability to handle namespace injection, namespace stripping, and unmanaged versions of managed repositories.  See the new doc at http://cumulusci.readthedocs.io/en/latest/dependencies.html

2.0.0-beta39 (2017-06-02)
------------------------

* Fix new bug in `update_dependencies` which caused failure when running against an org that already has a required package installed

2.0.0-beta38 (2017-06-01)
------------------------

* `update_dependencies` now properly handles references to a github repository that itself contains dependencies in its cumulusci.yml file
* `update_dependencies` now handles deploying unmanaged metadata from subfolders under unpackaged/pre of a referenced Github repository
* The `dependencies` section of `cumulusci.yml` now supports installing from a zip of metadata hosted at a url if you provide a `zip_url` and optionally a `subfolder`

2.0.0-beta37 (2017-06-01)
------------------------

* `update_dependencies` now supports dynamically referencing other Github repositories configured with a cumulusci.yml file.  The referenced repository's cumulusci.yml is parsed and the dependencies are included.  Also, the Github API is used to find the latest release of the referenced repo if the cumulusci.yml has a namespace configured.  Welcome to dynamic package dependency management ;)
* `cci task run` now supports the option flags `--debug-before` and `--debug-after`
* Fix for JUnit output rendering in run_tests


2.0.0-beta36 (2017-05-19)
------------------------

* Flows can now accept arguments in the CLI to override task options

  * `cci flow run install_beta -o install_managed_beta__version "1.0 (Beta 123)"`   

* Flows can now accept arguments to in the CLI to skip tasks

  * `cci flow run ci_feature --skip run_tests_debug --skip deploy_post`   
  
* Anonymous apex failures will now throw an exception and fail the build in `execute_anon`
* Fixes #322: local variable 'message' referenced before assignment

2.0.0-beta35 (2017-05-19)
------------------------

* New task `execute_anon` is available to run anonymous apex and takes the extra task option `apex`

2.0.0-beta34 (2017-05-16)
------------------------

* Fixes #317: ERROR: Invalid version specified

2.0.0-beta33 (2017-05-11)
------------------------

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
------------------------

* Scratch orgs now get an auto-generated password which is available via `cci org info`
* Added metadata mapping for StandardValueSets to fix #310
* Throw nicer exceptions when scratch org interaction fails

2.0.0-beta31 (2017-04-12)
------------------------

* Use UTC for all Salesforce API date/time fields
* Fix issue with listing metadata types
* Add generic polling method to BaseTask

2.0.0-beta30 (2017-04-04)
------------------------

* New task list_metadata_types
* [push upgrades] Fix push request status Cancelled --> Canceled
* [push upgrades] Fix datetime namespace issues
* [pyinstaller] Import project-level modules with run-time hook

2.0.0-beta29 (2017-04-04)
------------------------

* Report push status if start time is less than 1 minute in the future

2.0.0-beta28 (2017-03-30)
------------------------

* Fix bug in Push API batch retry logic introduced in beta25

2.0.0-beta27 (2017-03-29)
------------------------

* Skip org in push if statusCode is UKNOWN_EXCEPTION

2.0.0-beta26 (2017-03-29)
------------------------

* Fixes #278: Push upgrade raises exception for DUPLICATE_VALUE statusCode

2.0.0-beta25 (2017-03-28)
------------------------

* Fixes #277: Push API tasks now correctly handle errors in individual orgs in a batch when scheduling a push job

2.0.0-beta24 (2017-03-27)
------------------------

* Fixes #231: Handle unicode in package.xml generation
* Fixes #239: Replace fix for windows path issues from beta23 with a better implementation
* Fixes #275: Properly pass purge_on_delete option value in uninstall_packaged_incremental

2.0.0-beta23 (2017-03-22)
------------------------

* Fixes #239: Add local path to import path when looking up classes.  This should fix an error that appeared only in Windows

2.0.0-beta22 (2017-03-20)
------------------------

* `github_release_notes` now supports the `link_pr` option to add links to the pull request where each line of content came from
* Fixes #266: `update_dependencies` now supports the `purge_on_delete` option to allow running against production orgs
* Fixes #267: package.xml generation now skips RecordType when rendering in delete mode

2.0.0-beta21 (2017-03-17)
------------------------

* Fix parsing of OrgId from the access token using the new sfdx CLI

2.0.0-beta20 (2017-03-17)
------------------------

* Switch to using the `sfdx` CLI for interacting with scratch orgs.  If you use `cci` with scratch orgs, this release will no longer work with the `heroku force:*` commands from the prior Salesforce DX release.
* Upgrades to release notes generator
  * Content is now grouped by subheading under each heading
  * Better error message is thrown if a lightweight tag is found when an annotated tag is needed

2.0.0-beta19 (2017-03-15)
------------------------

* Fixes #261: cci org info should refresh token first

2.0.0-beta18 (2017-03-14)
------------------------

* Skip deleting Scontrols in incremental delete
* Escape package name when generating package.xml

2.0.0-beta17 (2017-03-14)
------------------------

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
------------------------

* Allow batch size to be configured for push jobs with the `batch_size` job

2.0.0-beta15 (2017-02-15)
------------------------

* Bug fix release for bug in `update_admin_profile` from the beta 14 release changes to the ApiRetrieveUnpackaged class

2.0.0-beta14 (2017-02-15)
------------------------

* The new `RetrieveReportsAndDashboards` task class that can retrieve all reports and dashboards from a specified list of folders
* Documentation improvements contributed by @tet3
* Include userinfo in the OrgConfig, and print username and org id at the beginning of every task run.  Contribution by @cdcarter
* `project_local_dir` (e.g., `~/.cumulusci/NPSP-Extension-Template/`, home of the encrypted keychain and local override config) now rely on the project name configured in cumulusci.yml instead of the existence of a git remote named origin.  Contribution by @cdcarter

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
