=====
Tasks
=====

apextestsdb_upload
==========================================

**Description:** Upload results from Apex tests to database

**Class::** cumulusci.tasks.apextestsdb.ApextestsdbUpload

Options:
------------------------------------------

* **execution_url** *(required)*: URL of test execution
* **environment_name** *(required)*: Name of test environment
* **execution_name** *(required)*: Name of test execution
* **branch_name**: Name of branch where tests were run
* **commit_sha**: Commit SHA from where tests were run
* **results_file_url** *(required)*: URL of test results file

create_package
==========================================

**Description:** Creates a package in the target org with the default package name for the project

**Class::** cumulusci.tasks.salesforce.CreatePackage

Options:
------------------------------------------

* **api_version** *(required)*: The api version to use when creating the package.  Defaults to project__package__api_version
* **package** *(required)*: The name of the package to create.  Defaults to project__package__name

create_managed_src
==========================================

**Description:** Modifies the src directory for managed deployment.  Strips //cumulusci-managed from all Apex code

**Class::** cumulusci.tasks.metadata.managed_src.CreateManagedSrc

Options:
------------------------------------------

* **path** *(required)*: The path containing metadata to process for managed deployment
* **revert_path** *(required)*: The path to copy the original metadata to for the revert call

create_unmanaged_ee_src
==========================================

**Description:** Modifies the src directory for unmanaged deployment to an EE org

**Class::** cumulusci.tasks.metadata.ee_src.CreateUnmanagedEESrc

Options:
------------------------------------------

* **path** *(required)*: The path containing metadata to process for managed deployment
* **revert_path** *(required)*: The path to copy the original metadata to for the revert call

deploy
==========================================

**Description:** Deploys the src directory of the repository to the org

**Class::** cumulusci.tasks.salesforce.Deploy

Options:
------------------------------------------

* **path** *(required)*: The path to the metadata source to be deployed

deploy_pre
==========================================

**Description:** Deploys all metadata bundles under unpackaged/pre/

**Class::** cumulusci.tasks.salesforce.DeployBundles

Options:
------------------------------------------

* **path** *(required)*: The path to the parent directory containing the metadata bundles directories

deploy_post
==========================================

**Description:** Deploys all metadata bundles under unpackaged/post/

**Class::** cumulusci.tasks.salesforce.DeployNamespacedBundles

Options:
------------------------------------------

* **namespace_token** *(required)*: The string token to replace with the namespace
* **path** *(required)*: The path to the parent directory containing the metadata bundles directories
* **namespace**: The namespace to replace the token with if in managed mode. Defaults to project__package__namespace
* **managed**: If True, will insert the actual namespace prefix.  Defaults to False or no namespace
* **filename_token** *(required)*: The path to the parent directory containing the metadata bundles directories

deploy_post_managed
==========================================

**Description:** Deploys all metadata bundles under unpackaged/post/

**Class::** cumulusci.tasks.salesforce.DeployNamespacedBundles

Options:
------------------------------------------

* **namespace_token** *(required)*: The string token to replace with the namespace
* **path** *(required)*: The path to the parent directory containing the metadata bundles directories
* **namespace**: The namespace to replace the token with if in managed mode. Defaults to project__package__namespace
* **managed**: If True, will insert the actual namespace prefix.  Defaults to False or no namespace
* **filename_token** *(required)*: The path to the parent directory containing the metadata bundles directories

dx_push
==========================================

**Description:** Uses Salesforce DX to push code to a scratch workspace org

**Class::** cumulusci.tasks.salesforcedx.BaseSalesforceDXTask

Options:
------------------------------------------

* **command** *(required)*: The Saleforce DX command to call.  For example: force:src:push
* **options**: The command line options to pass to the command

get_installed_packages
==========================================

**Description:** Retrieves a list of the currently installed managed package namespaces and their versions

**Class::** cumulusci.tasks.salesforce.GetInstalledPackages


github_clone_tag
==========================================

**Description:** Lists open pull requests in project Github repository

**Class::** cumulusci.tasks.github.CloneTag

Options:
------------------------------------------

* **tag** *(required)*: The new tag to create by cloning the src tag.  Ex: release/1.0
* **src_tag** *(required)*: The source tag to clone.  Ex: beta/1.0-Beta_2

github_master_to_feature
==========================================

**Description:** Merges the latest commit on the master branch into all open feature branches

**Class::** cumulusci.tasks.github.MergeBranch

Options:
------------------------------------------

* **commit**: The commit to merge into feature branches.  Defaults to the current head commit.
* **branch_prefix**: The prefix of branches that should receive the merge.  Defaults to project__git__prefix_feature
* **source_branch**: The source branch to merge from.  Defaults to project__git__default_branch.

github_pull_requests
==========================================

**Description:** Lists open pull requests in project Github repository

**Class::** cumulusci.tasks.github.PullRequests


github_release
==========================================

**Description:** Creates a Github release for a given managed package version number

**Class::** cumulusci.tasks.github.CreateRelease

Options:
------------------------------------------

* **commit**: Override the commit used to create the release.  Defaults to the current local HEAD commit
* **message**: The message to attach to the created git tag
* **version** *(required)*: The managed package version number.  Ex: 1.2
* **draft**: Set to True to create a draft release.  Defaults to False

github_release_notes
==========================================

**Description:** Generates release notes by parsing pull request bodies of merged pull requests between two tags

**Class::** cumulusci.tasks.release_notes.task.GithubReleaseNotes

Options:
------------------------------------------

* **last_tag**: Override the last release tag.  This is useful to generate release notes if you skipped one or more release
* **tag** *(required)*: The tag to generate release notes for.  Ex: release/1.2
* **publish**: If True, publishes to the release matching the tag release notes were generated for.

install_managed
==========================================

**Description:** Install the latest managed production release

**Class::** cumulusci.tasks.salesforce.InstallPackageVersion

Options:
------------------------------------------

* **retries**: Number of retries (default=5)
* **version** *(required)*: The version of the package to install.  "latest" and "latest_beta" can be used to trigger lookup via Github Releases on the repository.
* **namespace** *(required)*: The namespace of the package to install.  Defaults to project__package__namespace

install_managed_beta
==========================================

**Description:** Installs the latest managed beta release

**Class::** cumulusci.tasks.salesforce.InstallPackageVersion

Options:
------------------------------------------

* **retries**: Number of retries (default=5)
* **version** *(required)*: The version of the package to install.  "latest" and "latest_beta" can be used to trigger lookup via Github Releases on the repository.
* **namespace** *(required)*: The namespace of the package to install.  Defaults to project__package__namespace

mrbelvedere_publish
==========================================

**Description:** Publishes a release to the mrbelvedere web installer

**Class::** cumulusci.tasks.mrbelvedere.MrbelvederePublish

Options:
------------------------------------------

* **tag** *(required)*: The tag to publish to mrbelvedere

push_all
==========================================

**Description:** Schedules a push upgrade of a package version to all subscribers

**Class::** cumulusci.tasks.push.tasks.SchedulePushOrgQuery

Options:
------------------------------------------

* **min_version**: If set, no subscriber with a version lower than min_version will be selected for push
* **version** *(required)*: The managed package version to push
* **namespace**: The managed package namespace to push. Defaults to project__package__namespace.
* **start_time**: Set the start time to queue a future push. Ex: 2016-10-19T10:00
* **subscriber_where**: A SOQL style where clause for filtering PackageSubscriber objects.  Ex: OrgType = 'Sandbox'

push_qa
==========================================

**Description:** Schedules a push upgrade of a package version to all orgs listed in push/orgs_qa.txt

**Class::** cumulusci.tasks.push.tasks.SchedulePushOrgList

Options:
------------------------------------------

* **orgs** *(required)*: The path to a file containing one OrgID per line.
* **start_time**: Set the start time to queue a future push. Ex: 2016-10-19T10:00
* **version** *(required)*: The managed package version to push
* **namespace**: The managed package namespace to push. Defaults to project__package__namespace.

push_sandbox
==========================================

**Description:** Schedules a push upgrade of a package version to all subscribers

**Class::** cumulusci.tasks.push.tasks.SchedulePushOrgQuery

Options:
------------------------------------------

* **min_version**: If set, no subscriber with a version lower than min_version will be selected for push
* **version** *(required)*: The managed package version to push
* **namespace**: The managed package namespace to push. Defaults to project__package__namespace.
* **start_time**: Set the start time to queue a future push. Ex: 2016-10-19T10:00
* **subscriber_where**: A SOQL style where clause for filtering PackageSubscriber objects.  Ex: OrgType = 'Sandbox'

push_trial
==========================================

**Description:** Schedules a push upgrade of a package version to Trialforce Template orgs listed in push/orgs_trial.txt

**Class::** cumulusci.tasks.push.tasks.SchedulePushOrgList

Options:
------------------------------------------

* **orgs** *(required)*: The path to a file containing one OrgID per line.
* **start_time**: Set the start time to queue a future push. Ex: 2016-10-19T10:00
* **version** *(required)*: The managed package version to push
* **namespace**: The managed package namespace to push. Defaults to project__package__namespace.

query
==========================================

**Description:** Queries the connected org

**Class::** cumulusci.tasks.salesforce.SOQLQuery

Options:
------------------------------------------

* **query** *(required)*: A valid bulk SOQL query for the object
* **object** *(required)*: The object to query
* **result_file** *(required)*: The name of the csv file to write the results to

retrieve_packaged
==========================================

**Description:** Retrieves the packaged metadata from the org

**Class::** cumulusci.tasks.salesforce.RetrievePackaged

Options:
------------------------------------------

* **path** *(required)*: The path where the retrieved metadata should be written
* **api_version** *(required)*: Override the default api version for the retrieve.  Defaults to project__package__api_version
* **package** *(required)*: The package name to retrieve.  Defaults to project__package__name

retrieve_src
==========================================

**Description:** Retrieves the packaged metadata into the src directory

**Class::** cumulusci.tasks.salesforce.RetrievePackaged

Options:
------------------------------------------

* **path** *(required)*: The path where the retrieved metadata should be written
* **api_version** *(required)*: Override the default api version for the retrieve.  Defaults to project__package__api_version
* **package** *(required)*: The package name to retrieve.  Defaults to project__package__name

revert_managed_src
==========================================

**Description:** Reverts the changes from create_managed_src

**Class::** cumulusci.tasks.metadata.managed_src.RevertManagedSrc

Options:
------------------------------------------

* **path** *(required)*: The path containing metadata to process for managed deployment
* **revert_path** *(required)*: The path to copy the original metadata to for the revert call

revert_unmanaged_ee_src
==========================================

**Description:** Reverts the changes from create_unmanaged_ee_src

**Class::** cumulusci.tasks.metadata.ee_src.RevertUnmanagedEESrc

Options:
------------------------------------------

* **path** *(required)*: The path containing metadata to process for managed deployment
* **revert_path** *(required)*: The path to copy the original metadata to for the revert call

run_tests
==========================================

**Description:** Runs all apex tests

**Class::** cumulusci.tasks.salesforce.RunApexTests

Options:
------------------------------------------

* **test_name_exclude**: Query to find Apex test classes to exclude ("%" is wildcard).  Defaults to project__test__name_exclude
* **managed**: If True, search for tests in the namespace only.  Defaults to False
* **test_name_match** *(required)*: Query to find Apex test classes to run ("%" is wildcard).  Defaults to project__test__name_match
* **poll_interval**: Seconds to wait between polling for Apex test results.  Defaults to 3
* **namespace**: Salesforce project namespace.  Defaults to project__package__namespace
* **junit_output**: File name for JUnit output.  Defaults to test_results.xml

run_tests_debug
==========================================

**Description:** Runs all apex tests

**Class::** cumulusci.tasks.salesforce.RunApexTestsDebug

Options:
------------------------------------------

* **test_name_exclude**: Query to find Apex test classes to exclude ("%" is wildcard).  Defaults to project__test__name_exclude
* **junit_output**: File name for JUnit output.  Defaults to test_results.xml
* **managed**: If True, search for tests in the namespace only.  Defaults to False
* **json_output**: The path to the json output file.  Defaults to test_results.json
* **test_name_match** *(required)*: Query to find Apex test classes to run ("%" is wildcard).  Defaults to project__test__name_match
* **namespace**: Salesforce project namespace.  Defaults to project__package__namespace
* **debug_log_dir**: Directory to store debug logs. Defaults to temp dir.
* **poll_interval**: Seconds to wait between polling for Apex test results.  Defaults to 3

run_tests_managed
==========================================

**Description:** Runs all apex tests in the packaging org or a managed package subscriber org

**Class::** cumulusci.tasks.salesforce.RunApexTests

Options:
------------------------------------------

* **test_name_exclude**: Query to find Apex test classes to exclude ("%" is wildcard).  Defaults to project__test__name_exclude
* **managed**: If True, search for tests in the namespace only.  Defaults to False
* **test_name_match** *(required)*: Query to find Apex test classes to run ("%" is wildcard).  Defaults to project__test__name_match
* **poll_interval**: Seconds to wait between polling for Apex test results.  Defaults to 3
* **namespace**: Salesforce project namespace.  Defaults to project__package__namespace
* **junit_output**: File name for JUnit output.  Defaults to test_results.xml

uninstall_managed
==========================================

**Description:** Uninstalls the managed version of the package

**Class::** cumulusci.tasks.salesforce.UninstallPackage

Options:
------------------------------------------

* **namespace** *(required)*: The namespace of the package to uninstall.  Defaults to project__package__namespace

uninstall_packaged
==========================================

**Description:** Uninstalls all deleteable metadata in the package in the target org

**Class::** cumulusci.tasks.salesforce.UninstallPackaged

Options:
------------------------------------------

* **package** *(required)*: The package name to uninstall.  All metadata from the package will be retrieved and a custom destructiveChanges.xml package will be constructed and deployed to delete all deleteable metadata from the package.  Defaults to project__package__name

uninstall_packaged_incremental
==========================================

**Description:** Deletes any metadata from the package in the target org not in the local workspace

**Class::** cumulusci.tasks.salesforce.UninstallPackagedIncremental

Options:
------------------------------------------

* **path** *(required)*: The local path to compare to the retrieved packaged metadata from the org.  Defaults to src
* **package** *(required)*: The package name to uninstall.  All metadata from the package will be retrieved and a custom destructiveChanges.xml package will be constructed and deployed to delete all deleteable metadata from the package.  Defaults to project__package__name

uninstall_src
==========================================

**Description:** Uninstalls all metadata in the local src directory

**Class::** cumulusci.tasks.salesforce.UninstallLocal

Options:
------------------------------------------

* **path** *(required)*: The path to the metadata source to be deployed

uninstall_pre
==========================================

**Description:** Uninstalls the unpackaged/pre bundles

**Class::** cumulusci.tasks.salesforce.UninstallLocalBundles

Options:
------------------------------------------

* **path** *(required)*: The path to the metadata source to be deployed

uninstall_post
==========================================

**Description:** Uninstalls the unpackaged/post bundles

**Class::** cumulusci.tasks.salesforce.UninstallLocalNamespacedBundles

Options:
------------------------------------------

* **path** *(required)*: The path to a directory containing the metadata bundles (subdirectories) to uninstall
* **namespace**: The namespace to replace the token with if in managed mode. Defaults to project__package__namespace
* **managed**: If True, will insert the actual namespace prefix.  Defaults to False or no namespace
* **filename_token** *(required)*: The path to the parent directory containing the metadata bundles directories

uninstall_post_managed
==========================================

**Description:** Uninstalls the unpackaged/post bundles

**Class::** cumulusci.tasks.salesforce.UninstallLocalNamespacedBundles

Options:
------------------------------------------

* **path** *(required)*: The path to a directory containing the metadata bundles (subdirectories) to uninstall
* **namespace**: The namespace to replace the token with if in managed mode. Defaults to project__package__namespace
* **managed**: If True, will insert the actual namespace prefix.  Defaults to False or no namespace
* **filename_token** *(required)*: The path to the parent directory containing the metadata bundles directories

update_admin_profile
==========================================

**Description:** Retrieves, edits, and redeploys the Admin.profile with full FLS perms for all objects/fields

**Class::** cumulusci.tasks.salesforce.UpdateAdminProfile

Options:
------------------------------------------

* **package_xml**: Override the default package.xml file for retrieving the Admin.profile and all objects and classes that need to be included by providing a path to your custom package.xml

update_dependencies
==========================================

**Description:** Installs all dependencies in project__dependencies into the target org

**Class::** cumulusci.tasks.salesforce.UpdateDependencies


update_meta_xml
==========================================

**Description:** Updates all -meta.xml files to have the correct API version and extension package versions

**Class::** cumulusci.tasks.ant.AntTask

Options:
------------------------------------------

* **target** *(required)*: The ant target to run
* **verbose**: The ant target to run

update_package_xml
==========================================

**Description:** Updates src/package.xml with metadata in src/

**Class::** cumulusci.tasks.metadata.package.UpdatePackageXml

Options:
------------------------------------------

* **path** *(required)*: The path to a folder of metadata to build the package.xml from
* **delete**: If True, generate a package.xml for use as a destructiveChanges.xml file for deleting metadata
* **managed**: If True, generate a package.xml for deployment to the managed package packaging org
* **output**: The output file, defaults to <path>/package.xml

update_package_xml_managed
==========================================

**Description:** Updates src/package.xml with metadata in src/

**Class::** cumulusci.tasks.metadata.package.UpdatePackageXml

Options:
------------------------------------------

* **path** *(required)*: The path to a folder of metadata to build the package.xml from
* **delete**: If True, generate a package.xml for use as a destructiveChanges.xml file for deleting metadata
* **managed**: If True, generate a package.xml for deployment to the managed package packaging org
* **output**: The output file, defaults to <path>/package.xml

upload_beta
==========================================

**Description:** Uploads a beta release of the metadata currently in the packaging org

**Class::** cumulusci.tasks.salesforce.PackageUpload

Options:
------------------------------------------

* **name** *(required)*: The name of the package version.
* **namespace**: The namespace of the package.  Defaults to project__package__namespace
* **production**: If True, uploads a production release.  Defaults to uploading a beta
* **post_install_url**: The fully-qualified URL of the post-installation instructions. Instructions are shown as a link after installation and are available from the package detail view.
* **password**: An optional password for sharing the package privately with anyone who has the password. Don't enter a password if you want to make the package available to anyone on AppExchange and share your package publicly.
* **release_notes_url**: The fully-qualified URL of the package release notes. Release notes are shown as a link during the installation process and are available from the package detail view after installation.
* **description**: A description of the package and what this version contains.

upload_production
==========================================

**Description:** Uploads a beta release of the metadata currently in the packaging org

**Class::** cumulusci.tasks.salesforce.PackageUpload

Options:
------------------------------------------

* **name** *(required)*: The name of the package version.
* **namespace**: The namespace of the package.  Defaults to project__package__namespace
* **production**: If True, uploads a production release.  Defaults to uploading a beta
* **post_install_url**: The fully-qualified URL of the post-installation instructions. Instructions are shown as a link after installation and are available from the package detail view.
* **password**: An optional password for sharing the package privately with anyone who has the password. Don't enter a password if you want to make the package available to anyone on AppExchange and share your package publicly.
* **release_notes_url**: The fully-qualified URL of the package release notes. Release notes are shown as a link during the installation process and are available from the package detail view after installation.
* **description**: A description of the package and what this version contains.

util_sleep
==========================================

**Description:** Sleeps for N seconds

**Class::** cumulusci.tasks.util.Sleep

Options:
------------------------------------------

* **seconds** *(required)*: The number of seconds to sleep
