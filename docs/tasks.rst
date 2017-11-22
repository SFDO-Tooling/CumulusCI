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

batch_apex_wait
==========================================

**Description:** Waits on a batch apex job to finish.

**Class::** cumulusci.tasks.apex.batch.BatchApexWait

Options:
------------------------------------------

* **class_name** *(required)*: Name of the Apex class to wait for.
* **poll_interval**: Seconds to wait before polling for batch job completion. Defaults to 10 seconds.

command
==========================================

**Description:** Run an arbitrary command

**Class::** cumulusci.tasks.command.Command

Options:
------------------------------------------

* **command** *(required)*: The command to execute
* **env**: Environment variables to set for command. Must be flat dict, either as python dict from YAML or as JSON string.
* **dir**: If provided, the directory where the command should be run from.
* **pass_env** *(required)*: If False, the current environment variables will not be passed to the child process. Defaults to True

commit_apex_docs
==========================================

**Description:** commit local ApexDocs to GitHub branch

**Class::** cumulusci.tasks.github.CommitApexDocs

Options:
------------------------------------------

* **dir_local**: Local dir of ApexDocs (contains index.html). default=repo_root/ApexDocumentation
* **commit_message**: Message for commit; default="Update Apex docs"
* **dir_repo**: Location relative to repo root. default=project__apexdoc__repo_dir
* **dry_run**: Execute a dry run if True (default=False)
* **branch**: Branch name; default=project__apexdoc__branch

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

* **path** *(required)*: The path containing metadata to process for managed deployment **Default: src**
* **revert_path** *(required)*: The path to copy the original metadata to for the revert call **Default: src.orig**

create_unmanaged_ee_src
==========================================

**Description:** Modifies the src directory for unmanaged deployment to an EE org

**Class::** cumulusci.tasks.metadata.ee_src.CreateUnmanagedEESrc

Options:
------------------------------------------

* **path** *(required)*: The path containing metadata to process for managed deployment **Default: src**
* **revert_path** *(required)*: The path to copy the original metadata to for the revert call **Default: src.orig**

deploy
==========================================

**Description:** Deploys the src directory of the repository to the org

**Class::** cumulusci.tasks.salesforce.Deploy

Options:
------------------------------------------

* **namespace_strip**: If set, all namespace prefixes for the namespace specified are stripped from files and filenames
* **namespaced_org**: If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.
* **namespace_inject**: If set, the namespace tokens in files and filenames are replaced with the namespace's prefix
* **unmanaged**: If True, changes namespace_inject to replace tokens with a blank string
* **path** *(required)*: The path to the parent directory containing the metadata bundles directories **Default: src**
* **namespace_tokenize**: If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject

deploy_pre
==========================================

**Description:** Deploys all metadata bundles under unpackaged/pre/

**Class::** cumulusci.tasks.salesforce.DeployBundles

Options:
------------------------------------------

* **namespace_inject**: If set, the namespace tokens in files and filenames are replaced with the namespace's prefix
* **path** *(required)*: The path to the parent directory containing the metadata bundles directories **Default: unpackaged/pre**
* **unmanaged**: If True, changes namespace_inject to replace tokens with a blank string
* **namespace_strip**: If set, all namespace prefixes for the namespace specified are stripped from files and filenames
* **namespaced_org**: If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.
* **namespace_tokenize**: If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject

deploy_post
==========================================

**Description:** Deploys all metadata bundles under unpackaged/post/

**Class::** cumulusci.tasks.salesforce.DeployBundles

Options:
------------------------------------------

* **namespace_inject**: If set, the namespace tokens in files and filenames are replaced with the namespace's prefix **Default: $project_config.project__package__namespace**
* **path** *(required)*: The path to the parent directory containing the metadata bundles directories **Default: unpackaged/post**
* **unmanaged**: If True, changes namespace_inject to replace tokens with a blank string **Default: True**
* **namespace_strip**: If set, all namespace prefixes for the namespace specified are stripped from files and filenames
* **namespaced_org**: If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.
* **namespace_tokenize**: If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject

deploy_post_managed
==========================================

**Description:** Deploys all metadata bundles under unpackaged/post/

**Class::** cumulusci.tasks.salesforce.DeployBundles

Options:
------------------------------------------

* **namespace_inject**: If set, the namespace tokens in files and filenames are replaced with the namespace's prefix **Default: $project_config.project__package__namespace**
* **path** *(required)*: The path to the parent directory containing the metadata bundles directories **Default: unpackaged/post**
* **unmanaged**: If True, changes namespace_inject to replace tokens with a blank string
* **namespace_strip**: If set, all namespace prefixes for the namespace specified are stripped from files and filenames
* **namespaced_org**: If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.
* **namespace_tokenize**: If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject

dx_convert_to
==========================================

**Description:** Converts src directory metadata format into sfdx format under force-app

**Class::** cumulusci.tasks.sfdx.SFDXBaseTask

Options:
------------------------------------------

* **command** *(required)*: The full command to run with the sfdx cli. **Default: force:mdapi:convert -r src**
* **extra**: Append additional options to the command

dx_convert_from
==========================================

**Description:** Converts force-app directory in sfdx format into metadata format under src

**Class::** cumulusci.tasks.sfdx.SFDXBaseTask

Options:
------------------------------------------

* **command** *(required)*: The full command to run with the sfdx cli. **Default: force:mdapi:convert -r force-app -d src**
* **extra**: Append additional options to the command

dx_push
==========================================

**Description:** Uses sfdx to push the force-app directory metadata into a scratch org

**Class::** cumulusci.tasks.sfdx.SFDXOrgTask

Options:
------------------------------------------

* **command** *(required)*: The full command to run with the sfdx cli. **Default: force:source:push**
* **extra**: Append additional options to the command

execute_anon
==========================================

**Description:** Execute a string of anonymous apex via the tooling api.

**Class::** cumulusci.tasks.apex.anon.AnonymousApexTask

Options:
------------------------------------------

* **apex** *(required)*: The apex to run.

generate_apex_docs
==========================================

**Description:** Generate documentation for local code

**Class::** cumulusci.tasks.apexdoc.GenerateApexDocs

Options:
------------------------------------------

* **tag** *(required)*: The tag to use for links back to repo.
* **out_dir**: Directory to write Apex docs. ApexDoc tool will write files to a subdirectory called ApexDocumentation which will be created if it does not exist. default=repo_root

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
* **children_only**: If True, merge will only be done to child branches.  This assumes source branch is a parent feature branch.  Defaults to False
* **branch_prefix**: The prefix of branches that should receive the merge.  Defaults to project__git__prefix_feature
* **source_branch**: The source branch to merge from.  Defaults to project__git__default_branch.

github_parent_to_children
==========================================

**Description:** Merges the latest commit on a parent feature branch into all child feature branches

**Class::** cumulusci.tasks.github.MergeBranch

Options:
------------------------------------------

* **commit**: The commit to merge into feature branches.  Defaults to the current head commit.
* **children_only**: If True, merge will only be done to child branches.  This assumes source branch is a parent feature branch.  Defaults to False **Default: True**
* **branch_prefix**: The prefix of branches that should receive the merge.  Defaults to project__git__prefix_feature
* **source_branch**: The source branch to merge from.  Defaults to project__git__default_branch. **Default: $project_config.repo_branch**

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

github_release_notes
==========================================

**Description:** Generates release notes by parsing pull request bodies of merged pull requests between two tags

**Class::** cumulusci.tasks.release_notes.task.GithubReleaseNotes

Options:
------------------------------------------

* **last_tag**: Override the last release tag. This is useful to generate release notes if you skipped one or more releases.
* **link_pr**: If True, insert link to source pull request at end of each line.
* **tag** *(required)*: The tag to generate release notes for. Ex: release/1.2
* **publish**: Publish to GitHub release if True (default=False)

install_managed
==========================================

**Description:** Install the latest managed production release

**Class::** cumulusci.tasks.salesforce.InstallPackageVersion

Options:
------------------------------------------

* **retry_interval_add**: Number of seconds to add before each retry (default=30),
* **retries**: Number of retries (default=5)
* **version** *(required)*: The version of the package to install.  "latest" and "latest_beta" can be used to trigger lookup via Github Releases on the repository. **Default: latest**
* **namespace** *(required)*: The namespace of the package to install.  Defaults to project__package__namespace
* **retry_interval**: Number of seconds to wait before the next retry (default=5),

install_managed_beta
==========================================

**Description:** Installs the latest managed beta release

**Class::** cumulusci.tasks.salesforce.InstallPackageVersion

Options:
------------------------------------------

* **retry_interval_add**: Number of seconds to add before each retry (default=30),
* **retries**: Number of retries (default=5)
* **version** *(required)*: The version of the package to install.  "latest" and "latest_beta" can be used to trigger lookup via Github Releases on the repository. **Default: latest_beta**
* **namespace** *(required)*: The namespace of the package to install.  Defaults to project__package__namespace
* **retry_interval**: Number of seconds to wait before the next retry (default=5),

list_metadata_types
==========================================

**Description:** Prints the metadata types in a project

**Class::** cumulusci.tasks.util.ListMetadataTypes

Options:
------------------------------------------

* **package_xml**: The project package.xml file. Defaults to <project_root>/src/package.xml

meta_xml_apiversion
==========================================

**Description:** Set the API version in *meta.xml files

**Class::** cumulusci.tasks.metaxml.UpdateApi

Options:
------------------------------------------

* **version** *(required)*: API version number e.g. 37.0
* **dir**: Base directory to search for *-meta.xml files

meta_xml_dependencies
==========================================

**Description:** Set the version for dependent packages

**Class::** cumulusci.tasks.metaxml.UpdateDependencies

Options:
------------------------------------------

* **dir**: Base directory to search for *-meta.xml files

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
* **start_time**: Set the start time (UTC) to queue a future push. Ex: 2016-10-19T10:00
* **subscriber_where**: A SOQL style WHERE clause for filtering PackageSubscriber objects. Ex: OrgType = 'Sandbox'

push_list
==========================================

**Description:** Schedules a push upgrade of a package version to all orgs listed in the specified file

**Class::** cumulusci.tasks.push.tasks.SchedulePushOrgList

Options:
------------------------------------------

* **orgs** *(required)*: The path to a file containing one OrgID per line.
* **start_time**: Set the start time (UTC) to queue a future push. Ex: 2016-10-19T10:00
* **version** *(required)*: The managed package version to push
* **namespace**: The managed package namespace to push. Defaults to project__package__namespace.
* **batch_size**: Break pull requests into batches of this many orgs. Defaults to 200.

push_qa
==========================================

**Description:** Schedules a push upgrade of a package version to all orgs listed in push/orgs_qa.txt

**Class::** cumulusci.tasks.push.tasks.SchedulePushOrgList

Options:
------------------------------------------

* **orgs** *(required)*: The path to a file containing one OrgID per line. **Default: push/orgs_qa.txt**
* **start_time**: Set the start time (UTC) to queue a future push. Ex: 2016-10-19T10:00
* **version** *(required)*: The managed package version to push
* **namespace**: The managed package namespace to push. Defaults to project__package__namespace.
* **batch_size**: Break pull requests into batches of this many orgs. Defaults to 200.

push_sandbox
==========================================

**Description:** Schedules a push upgrade of a package version to all subscribers

**Class::** cumulusci.tasks.push.tasks.SchedulePushOrgQuery

Options:
------------------------------------------

* **min_version**: If set, no subscriber with a version lower than min_version will be selected for push
* **version** *(required)*: The managed package version to push
* **namespace**: The managed package namespace to push. Defaults to project__package__namespace.
* **start_time**: Set the start time (UTC) to queue a future push. Ex: 2016-10-19T10:00
* **subscriber_where**: A SOQL style WHERE clause for filtering PackageSubscriber objects. Ex: OrgType = 'Sandbox' **Default: OrgType = 'Sandbox'**

push_trial
==========================================

**Description:** Schedules a push upgrade of a package version to Trialforce Template orgs listed in push/orgs_trial.txt

**Class::** cumulusci.tasks.push.tasks.SchedulePushOrgList

Options:
------------------------------------------

* **orgs** *(required)*: The path to a file containing one OrgID per line. **Default: push/orgs_trial.txt**
* **start_time**: Set the start time (UTC) to queue a future push. Ex: 2016-10-19T10:00
* **version** *(required)*: The managed package version to push
* **namespace**: The managed package namespace to push. Defaults to project__package__namespace.
* **batch_size**: Break pull requests into batches of this many orgs. Defaults to 200.

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

* **namespace_inject**: If set, the namespace tokens in files and filenames are replaced with the namespace's prefix
* **api_version**: Override the default api version for the retrieve. Defaults to project__package__api_version
* **path** *(required)*: The path to write the retrieved metadata **Default: packaged**
* **unmanaged**: If True, changes namespace_inject to replace tokens with a blank string
* **package** *(required)*: The package name to retrieve.  Defaults to project__package__name
* **namespace_strip**: If set, all namespace prefixes for the namespace specified are stripped from files and filenames
* **namespaced_org**: If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.
* **namespace_tokenize**: If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject

retrieve_src
==========================================

**Description:** Retrieves the packaged metadata into the src directory

**Class::** cumulusci.tasks.salesforce.RetrievePackaged

Options:
------------------------------------------

* **namespace_inject**: If set, the namespace tokens in files and filenames are replaced with the namespace's prefix
* **api_version**: Override the default api version for the retrieve. Defaults to project__package__api_version
* **path** *(required)*: The path to write the retrieved metadata **Default: src**
* **unmanaged**: If True, changes namespace_inject to replace tokens with a blank string
* **package** *(required)*: The package name to retrieve.  Defaults to project__package__name
* **namespace_strip**: If set, all namespace prefixes for the namespace specified are stripped from files and filenames
* **namespaced_org**: If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.
* **namespace_tokenize**: If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject

retrieve_unpackaged
==========================================

**Description:** Retrieve the contents of a package.xml file.

**Class::** cumulusci.tasks.salesforce.RetrieveUnpackaged

Options:
------------------------------------------

* **package_xml** *(required)*: The path to a package.xml manifest to use for the retrieve.
* **namespace_inject**: If set, the namespace tokens in files and filenames are replaced with the namespace's prefix
* **api_version**: Override the default api version for the retrieve. Defaults to project__package__api_version
* **path** *(required)*: The path to write the retrieved metadata
* **unmanaged**: If True, changes namespace_inject to replace tokens with a blank string
* **namespace_strip**: If set, all namespace prefixes for the namespace specified are stripped from files and filenames
* **namespaced_org**: If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.
* **namespace_tokenize**: If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject

revert_managed_src
==========================================

**Description:** Reverts the changes from create_managed_src

**Class::** cumulusci.tasks.metadata.managed_src.RevertManagedSrc

Options:
------------------------------------------

* **path** *(required)*: The path containing metadata to process for managed deployment **Default: src**
* **revert_path** *(required)*: The path to copy the original metadata to for the revert call **Default: src.orig**

revert_unmanaged_ee_src
==========================================

**Description:** Reverts the changes from create_unmanaged_ee_src

**Class::** cumulusci.tasks.metadata.ee_src.RevertUnmanagedEESrc

Options:
------------------------------------------

* **path** *(required)*: The path containing metadata to process for managed deployment **Default: src**
* **revert_path** *(required)*: The path to copy the original metadata to for the revert call **Default: src.orig**

run_tests
==========================================

**Description:** Runs all apex tests

**Class::** cumulusci.tasks.apex.testrunner.RunApexTests

Options:
------------------------------------------

* **test_name_exclude**: Query to find Apex test classes to exclude ("%" is wildcard).  Defaults to project__test__name_exclude
* **retries**: Number of retries (default=10)
* **junit_output**: File name for JUnit output.  Defaults to test_results.xml
* **managed**: If True, search for tests in the namespace only.  Defaults to False
* **json_output**: File name for json output.  Defaults to test_results.json
* **test_name_match** *(required)*: Query to find Apex test classes to run ("%" is wildcard).  Defaults to project__test__name_match
* **retry_interval_add**: Number of seconds to add before each retry (default=5),
* **poll_interval**: Seconds to wait between polling for Apex test results.  Defaults to 3
* **namespace**: Salesforce project namespace.  Defaults to project__package__namespace
* **retry_interval**: Number of seconds to wait before the next retry (default=5),

run_tests_debug
==========================================

**Description:** Runs all apex tests

**Class::** cumulusci.tasks.apex.testrunner.RunApexTests

Options:
------------------------------------------

* **test_name_exclude**: Query to find Apex test classes to exclude ("%" is wildcard).  Defaults to project__test__name_exclude
* **retries**: Number of retries (default=10)
* **junit_output**: File name for JUnit output.  Defaults to test_results.xml
* **managed**: If True, search for tests in the namespace only.  Defaults to False
* **json_output**: File name for json output.  Defaults to test_results.json
* **test_name_match** *(required)*: Query to find Apex test classes to run ("%" is wildcard).  Defaults to project__test__name_match
* **retry_interval_add**: Number of seconds to add before each retry (default=5),
* **poll_interval**: Seconds to wait between polling for Apex test results.  Defaults to 3
* **namespace**: Salesforce project namespace.  Defaults to project__package__namespace
* **retry_interval**: Number of seconds to wait before the next retry (default=5),

run_tests_managed
==========================================

**Description:** Runs all apex tests in the packaging org or a managed package subscriber org

**Class::** cumulusci.tasks.apex.testrunner.RunApexTests

Options:
------------------------------------------

* **test_name_exclude**: Query to find Apex test classes to exclude ("%" is wildcard).  Defaults to project__test__name_exclude
* **retries**: Number of retries (default=10)
* **junit_output**: File name for JUnit output.  Defaults to test_results.xml
* **managed**: If True, search for tests in the namespace only.  Defaults to False **Default: True**
* **json_output**: File name for json output.  Defaults to test_results.json
* **test_name_match** *(required)*: Query to find Apex test classes to run ("%" is wildcard).  Defaults to project__test__name_match
* **retry_interval_add**: Number of seconds to add before each retry (default=5),
* **poll_interval**: Seconds to wait between polling for Apex test results.  Defaults to 3
* **namespace**: Salesforce project namespace.  Defaults to project__package__namespace
* **retry_interval**: Number of seconds to wait before the next retry (default=5),

uninstall_managed
==========================================

**Description:** Uninstalls the managed version of the package

**Class::** cumulusci.tasks.salesforce.UninstallPackage

Options:
------------------------------------------

* **purge_on_delete** *(required)*: Sets the purgeOnDelete option for the deployment.  Defaults to True
* **namespace** *(required)*: The namespace of the package to uninstall.  Defaults to project__package__namespace

uninstall_packaged
==========================================

**Description:** Uninstalls all deleteable metadata in the package in the target org

**Class::** cumulusci.tasks.salesforce.UninstallPackaged

Options:
------------------------------------------

* **purge_on_delete** *(required)*: Sets the purgeOnDelete option for the deployment.  Defaults to True
* **package** *(required)*: The package name to uninstall.  All metadata from the package will be retrieved and a custom destructiveChanges.xml package will be constructed and deployed to delete all deleteable metadata from the package.  Defaults to project__package__name

uninstall_packaged_incremental
==========================================

**Description:** Deletes any metadata from the package in the target org not in the local workspace

**Class::** cumulusci.tasks.salesforce.UninstallPackagedIncremental

Options:
------------------------------------------

* **purge_on_delete** *(required)*: Sets the purgeOnDelete option for the deployment.  Defaults to True
* **path** *(required)*: The local path to compare to the retrieved packaged metadata from the org.  Defaults to src
* **package** *(required)*: The package name to uninstall.  All metadata from the package will be retrieved and a custom destructiveChanges.xml package will be constructed and deployed to delete all deleteable metadata from the package.  Defaults to project__package__name

uninstall_src
==========================================

**Description:** Uninstalls all metadata in the local src directory

**Class::** cumulusci.tasks.salesforce.UninstallLocal

Options:
------------------------------------------

* **purge_on_delete**: Sets the purgeOnDelete option for the deployment. Defaults to True
* **namespace_inject**: If set, the namespace tokens in files and filenames are replaced with the namespace's prefix
* **path** *(required)*: The path to the parent directory containing the metadata bundles directories **Default: src**
* **unmanaged**: If True, changes namespace_inject to replace tokens with a blank string
* **namespace_strip**: If set, all namespace prefixes for the namespace specified are stripped from files and filenames
* **namespaced_org**: If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.
* **namespace_tokenize**: If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject

uninstall_pre
==========================================

**Description:** Uninstalls the unpackaged/pre bundles

**Class::** cumulusci.tasks.salesforce.UninstallLocalBundles

Options:
------------------------------------------

* **purge_on_delete**: Sets the purgeOnDelete option for the deployment. Defaults to True
* **namespace_inject**: If set, the namespace tokens in files and filenames are replaced with the namespace's prefix
* **path** *(required)*: The path to the parent directory containing the metadata bundles directories **Default: unpackaged/pre**
* **unmanaged**: If True, changes namespace_inject to replace tokens with a blank string
* **namespace_strip**: If set, all namespace prefixes for the namespace specified are stripped from files and filenames
* **namespaced_org**: If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.
* **namespace_tokenize**: If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject

uninstall_post
==========================================

**Description:** Uninstalls the unpackaged/post bundles

**Class::** cumulusci.tasks.salesforce.UninstallLocalNamespacedBundles

Options:
------------------------------------------

* **purge_on_delete** *(required)*: Sets the purgeOnDelete option for the deployment.  Defaults to True
* **path** *(required)*: The path to a directory containing the metadata bundles (subdirectories) to uninstall **Default: unpackaged/post**
* **namespace**: The namespace to replace the token with if in managed mode. Defaults to project__package__namespace
* **managed**: If True, will insert the actual namespace prefix.  Defaults to False or no namespace
* **filename_token** *(required)*: The path to the parent directory containing the metadata bundles directories **Default: ___NAMESPACE___**

uninstall_post_managed
==========================================

**Description:** Uninstalls the unpackaged/post bundles

**Class::** cumulusci.tasks.salesforce.UninstallLocalNamespacedBundles

Options:
------------------------------------------

* **purge_on_delete** *(required)*: Sets the purgeOnDelete option for the deployment.  Defaults to True
* **path** *(required)*: The path to a directory containing the metadata bundles (subdirectories) to uninstall **Default: unpackaged/post**
* **namespace**: The namespace to replace the token with if in managed mode. Defaults to project__package__namespace
* **managed**: If True, will insert the actual namespace prefix.  Defaults to False or no namespace **Default: True**
* **filename_token** *(required)*: The path to the parent directory containing the metadata bundles directories **Default: ___NAMESPACE___**

unschedule_apex
==========================================

**Description:** Unschedule all scheduled apex jobs (CronTriggers).

**Class::** cumulusci.tasks.apex.anon.AnonymousApexTask

Options:
------------------------------------------

* **apex** *(required)*: The apex to run. **Default: for (CronTrigger t : [SELECT Id FROM CronTrigger]) { System.abortJob(t.Id); }**

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

Options:
------------------------------------------

* **purge_on_delete**: Sets the purgeOnDelete option for the deployment. Defaults to True
* **namespaced_org**: If True, the changes namespace token injection on any dependencies so tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.

update_package_xml
==========================================

**Description:** Updates src/package.xml with metadata in src/

**Class::** cumulusci.tasks.metadata.package.UpdatePackageXml

Options:
------------------------------------------

* **path** *(required)*: The path to a folder of metadata to build the package.xml from **Default: src**
* **delete**: If True, generate a package.xml for use as a destructiveChanges.xml file for deleting metadata
* **managed**: If True, generate a package.xml for deployment to the managed package packaging org
* **package_name**: If set, overrides the package name inserted into the <fullName> element
* **output**: The output file, defaults to <path>/package.xml

update_package_xml_managed
==========================================

**Description:** Updates src/package.xml with metadata in src/

**Class::** cumulusci.tasks.metadata.package.UpdatePackageXml

Options:
------------------------------------------

* **path** *(required)*: The path to a folder of metadata to build the package.xml from **Default: src**
* **delete**: If True, generate a package.xml for use as a destructiveChanges.xml file for deleting metadata
* **managed**: If True, generate a package.xml for deployment to the managed package packaging org **Default: True**
* **package_name**: If set, overrides the package name inserted into the <fullName> element
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

**Description:** Uploads a production release of the metadata currently in the packaging org

**Class::** cumulusci.tasks.salesforce.PackageUpload

Options:
------------------------------------------

* **name** *(required)*: The name of the package version.
* **namespace**: The namespace of the package.  Defaults to project__package__namespace
* **production**: If True, uploads a production release.  Defaults to uploading a beta **Default: True**
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

* **seconds** *(required)*: The number of seconds to sleep **Default: 5**

