==========================================
Tasks Reference
==========================================

activate_flow
==========================================

**Description:** Activates Flows identified by a given list of Developer Names

**Class::** cumulusci.tasks.salesforce.activate_flow.ActivateFlow

Options:
------------------------------------------

* **developer_names** *(required)*: List of DeveloperNames to query in SOQL

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

**Example Command-line Usage::** cci task run command -o command "echo 'Hello command task!'"

**Example Task to Run Command::**
hello_world:
    description: Says hello world
    class_path: cumulusci.tasks.command.Command
    options:
    command: echo 'Hello World!'


Options:
------------------------------------------

* **command** *(required)*: The command to execute
* **dir**: If provided, the directory where the command should be run from.
* **env**: Environment variables to set for command. Must be flat dict, either as python dict from YAML or as JSON string.
* **pass_env** *(required)*: If False, the current environment variables will not be passed to the child process. Defaults to True
* **interactive**: If True, the command will use stderr, stdout, and stdin of the main process.Defaults to False.

connected_app
==========================================

**Description:** Creates the Connected App needed to use persistent orgs in the CumulusCI keychain

**Class::** cumulusci.tasks.connectedapp.CreateConnectedApp

Options:
------------------------------------------

* **label** *(required)*: The label for the connected app.  Must contain only alphanumeric and underscores **Default: CumulusCI**
* **email**: The email address to associate with the connected app.  Defaults to email address from the github service if configured.
* **username**: Create the connected app in a different org.  Defaults to the defaultdevhubusername configured in sfdx.
* **connect**: If True, the created connected app will be stored as the CumulusCI connected_app service in the keychain. **Default: True**
* **overwrite**: If True, any existing connected_app service in the CumulusCI keychain will be overwritten.  Has no effect if the connect option is False.

create_community
==========================================

**Description:** Creates a Community in the target org using the Connect API

**Class::** cumulusci.tasks.salesforce.CreateCommunity

Create a Salesforce Community via the Connect API.
Specify the `template` "VF Template" for Visualforce Tabs community,
or the name for a specific desired template


Options:
------------------------------------------

* **template** *(required)*: Name of the template for the community.
* **name** *(required)*: Name of the community.
* **description**: Description of the community.
* **url_path_prefix**: URL prefix for the community.
* **timeout**: Time to wait, in seconds, for the community to be created

create_package
==========================================

**Description:** Creates a package in the target org with the default package name for the project

**Class::** cumulusci.tasks.salesforce.CreatePackage

Options:
------------------------------------------

* **package** *(required)*: The name of the package to create.  Defaults to project__package__name
* **api_version** *(required)*: The api version to use when creating the package.  Defaults to project__package__api_version

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

* **path** *(required)*: The path to the parent directory containing the metadata bundles directories **Default: src**
* **unmanaged**: If True, changes namespace_inject to replace tokens with a blank string
* **namespace_inject**: If set, the namespace tokens in files and filenames are replaced with the namespace's prefix
* **namespace_strip**: If set, all namespace prefixes for the namespace specified are stripped from files and filenames
* **namespace_tokenize**: If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject
* **check_only**: If True, performs a test deployment (validation) of components without saving the components in the target org
* **test_level**: Specifies which tests are run as part of a deployment. Valid values: NoTestRun, RunLocalTests, RunAllTestsInOrg, RunSpecifiedTests.
* **specified_tests**: Comma-separated list of test classes to run upon deployment. Applies only with test_level set to RunSpecifiedTests.
* **static_resource_path**: The path where decompressed static resources are stored.  Any subdirectories found will be zipped and added to the staticresources directory of the build.
* **namespaced_org**: If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.
* **clean_meta_xml**: Defaults to True which strips the <packageVersions/> element from all meta.xml files.  The packageVersion element gets added automatically by the target org and is set to whatever version is installed in the org.  To disable this, set this option to False

deploy_pre
==========================================

**Description:** Deploys all metadata bundles under unpackaged/pre/

**Class::** cumulusci.tasks.salesforce.DeployBundles

Options:
------------------------------------------

* **path** *(required)*: The path to the parent directory containing the metadata bundles directories **Default: unpackaged/pre**
* **unmanaged**: If True, changes namespace_inject to replace tokens with a blank string
* **namespace_inject**: If set, the namespace tokens in files and filenames are replaced with the namespace's prefix
* **namespace_strip**: If set, all namespace prefixes for the namespace specified are stripped from files and filenames
* **namespace_tokenize**: If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject
* **check_only**: If True, performs a test deployment (validation) of components without saving the components in the target org
* **test_level**: Specifies which tests are run as part of a deployment. Valid values: NoTestRun, RunLocalTests, RunAllTestsInOrg, RunSpecifiedTests.
* **specified_tests**: Comma-separated list of test classes to run upon deployment. Applies only with test_level set to RunSpecifiedTests.
* **static_resource_path**: The path where decompressed static resources are stored.  Any subdirectories found will be zipped and added to the staticresources directory of the build.
* **namespaced_org**: If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.
* **clean_meta_xml**: Defaults to True which strips the <packageVersions/> element from all meta.xml files.  The packageVersion element gets added automatically by the target org and is set to whatever version is installed in the org.  To disable this, set this option to False

deploy_post
==========================================

**Description:** Deploys all metadata bundles under unpackaged/post/

**Class::** cumulusci.tasks.salesforce.DeployBundles

Options:
------------------------------------------

* **path** *(required)*: The path to the parent directory containing the metadata bundles directories **Default: unpackaged/post**
* **unmanaged**: If True, changes namespace_inject to replace tokens with a blank string **Default: True**
* **namespace_inject**: If set, the namespace tokens in files and filenames are replaced with the namespace's prefix **Default: $project_config.project__package__namespace**
* **namespace_strip**: If set, all namespace prefixes for the namespace specified are stripped from files and filenames
* **namespace_tokenize**: If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject
* **check_only**: If True, performs a test deployment (validation) of components without saving the components in the target org
* **test_level**: Specifies which tests are run as part of a deployment. Valid values: NoTestRun, RunLocalTests, RunAllTestsInOrg, RunSpecifiedTests.
* **specified_tests**: Comma-separated list of test classes to run upon deployment. Applies only with test_level set to RunSpecifiedTests.
* **static_resource_path**: The path where decompressed static resources are stored.  Any subdirectories found will be zipped and added to the staticresources directory of the build.
* **namespaced_org**: If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.
* **clean_meta_xml**: Defaults to True which strips the <packageVersions/> element from all meta.xml files.  The packageVersion element gets added automatically by the target org and is set to whatever version is installed in the org.  To disable this, set this option to False

deploy_qa_config
==========================================

**Description:** Deploys configuration for QA.

**Class::** cumulusci.tasks.salesforce.Deploy

Options:
------------------------------------------

* **path** *(required)*: The path to the parent directory containing the metadata bundles directories **Default: unpackaged/config/qa**
* **unmanaged**: If True, changes namespace_inject to replace tokens with a blank string **Default: True**
* **namespace_inject**: If set, the namespace tokens in files and filenames are replaced with the namespace's prefix **Default: $project_config.project__package__namespace**
* **namespace_strip**: If set, all namespace prefixes for the namespace specified are stripped from files and filenames
* **namespace_tokenize**: If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject
* **check_only**: If True, performs a test deployment (validation) of components without saving the components in the target org
* **test_level**: Specifies which tests are run as part of a deployment. Valid values: NoTestRun, RunLocalTests, RunAllTestsInOrg, RunSpecifiedTests.
* **specified_tests**: Comma-separated list of test classes to run upon deployment. Applies only with test_level set to RunSpecifiedTests.
* **static_resource_path**: The path where decompressed static resources are stored.  Any subdirectories found will be zipped and added to the staticresources directory of the build.
* **namespaced_org**: If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.
* **clean_meta_xml**: Defaults to True which strips the <packageVersions/> element from all meta.xml files.  The packageVersion element gets added automatically by the target org and is set to whatever version is installed in the org.  To disable this, set this option to False

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

* **command** *(required)*: The full command to run with the sfdx cli. **Default: force:source:convert -d src**
* **extra**: Append additional options to the command

dx_pull
==========================================

**Description:** Uses sfdx to pull from a scratch org into the force-app directory

**Class::** cumulusci.tasks.sfdx.SFDXOrgTask

Options:
------------------------------------------

* **command** *(required)*: The full command to run with the sfdx cli. **Default: force:source:pull**
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

**Description:** Execute anonymous apex via the tooling api.

**Class::** cumulusci.tasks.apex.anon.AnonymousApexTask

Use the `apex` option to run a string of anonymous Apex.
Use the `path` option to run anonymous Apex from a file.
Or use both to concatenate the string to the file contents.


Options:
------------------------------------------

* **path**: The path to an Apex file to run.
* **apex**: A string of Apex to run (after the file, if specified).
* **managed**: If True, will insert the project's namespace prefix.  Defaults to False or no namespace.
* **namespaced**: If True, the tokens %%%NAMESPACED_RT%%% and %%%namespaced%%% will get replaced with the namespace prefix for Record Types.

generate_data_dictionary
==========================================

**Description:** Create a data dictionary for the project in CSV format.

**Class::** cumulusci.tasks.datadictionary.GenerateDataDictionary

Generate a data dictionary for the project by walking all GitHub releases.
The data dictionary is output as two CSV files.
One, in `object_path`, includes the Object Name, Object Label, and Version Introduced,
with one row per packaged object.
The other, in `field_path`, includes Object Name, Field Name, Field Label, Field Type,
Picklist Values (if any), Version Introduced.
Both MDAPI and SFDX format releases are supported. However, only force-app/main/default
is processed for SFDX projects.


Options:
------------------------------------------

* **object_path**: Path to a CSV file to contain an sObject-level data dictionary.
* **field_path**: Path to a CSV file to contain an field-level data dictionary.
* **release_prefix** *(required)*: The tag prefix used for releases. **Default: $project_config.project__git__prefix_release**

get_installed_packages
==========================================

**Description:** Retrieves a list of the currently installed managed package namespaces and their versions

**Class::** cumulusci.tasks.salesforce.GetInstalledPackages


github_parent_pr_notes
==========================================

**Description:** Merges the description of a child pull request to the respective parent's pull request (if one exists).

**Class::** cumulusci.tasks.release_notes.task.ParentPullRequestNotes

Aggregate change notes from child pull request(s) to its corresponding
parent's pull request.

When given the branch_name option, this task will: (1) check if the base branch
of the corresponding pull request starts with the feature branch prefix and if so (2) attempt
to query for a pull request corresponding to this parent feature branch. (3) if a pull request
isn't found, the task exits and no actions are taken.

If the build_notes_label is present on the pull request, then all notes from the
child pull request are aggregated into the parent pull request. if the build_notes_label
is not detected on the parent pull request then a link to the child pull request
is placed under the "Unaggregated Pull Requests" header.

When given the parent_branch_name option, this task will query for a corresponding pull request.
If a pull request is not found, the task exits. If a pull request is found, then all notes
from child pull requests are re-aggregated and the body of the parent is replaced entirely.


Options:
------------------------------------------

* **branch_name** *(required)*: Name of branch to check for parent status, and if so, reaggregate change notes from child branches.
* **build_notes_label** *(required)*: Name of the label that indicates that change notes on parent pull requests should be reaggregated when a child branch pull request is created.
* **force**: force rebuilding of change notes from child branches in the given branch.

github_clone_tag
==========================================

**Description:** Clones a github tag under a new name.

**Class::** cumulusci.tasks.github.CloneTag

Options:
------------------------------------------

* **src_tag** *(required)*: The source tag to clone.  Ex: beta/1.0-Beta_2
* **tag** *(required)*: The new tag to create by cloning the src tag.  Ex: release/1.0

github_master_to_feature
==========================================

**Description:** Merges the latest commit on the master branch into all open feature branches

**Class::** cumulusci.tasks.github.MergeBranch

Options:
------------------------------------------

* **commit**: The commit to merge into feature branches.  Defaults to the current head commit.
* **source_branch**: The source branch to merge from.  Defaults to project__git__default_branch.
* **branch_prefix**: The prefix of branches that should receive the merge.  Defaults to project__git__prefix_feature
* **children_only**: If True, merge will only be done to child branches.  This assumes source branch is a parent feature branch.  Defaults to False

github_parent_to_children
==========================================

**Description:** Merges the latest commit on a parent feature branch into all child feature branches

**Class::** cumulusci.tasks.github.MergeBranch

Options:
------------------------------------------

* **commit**: The commit to merge into feature branches.  Defaults to the current head commit.
* **source_branch**: The source branch to merge from.  Defaults to project__git__default_branch. **Default: $project_config.repo_branch**
* **branch_prefix**: The prefix of branches that should receive the merge.  Defaults to project__git__prefix_feature
* **children_only**: If True, merge will only be done to child branches.  This assumes source branch is a parent feature branch.  Defaults to False **Default: True**

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

* **version** *(required)*: The managed package version number.  Ex: 1.2
* **message**: The message to attach to the created git tag
* **dependencies**: List of dependencies to record in the tag message.
* **commit**: Override the commit used to create the release. Defaults to the current local HEAD commit

github_release_notes
==========================================

**Description:** Generates release notes by parsing pull request bodies of merged pull requests between two tags

**Class::** cumulusci.tasks.release_notes.task.GithubReleaseNotes

Options:
------------------------------------------

* **tag** *(required)*: The tag to generate release notes for. Ex: release/1.2
* **last_tag**: Override the last release tag. This is useful to generate release notes if you skipped one or more releases.
* **link_pr**: If True, insert link to source pull request at end of each line.
* **publish**: Publish to GitHub release if True (default=False)
* **include_empty**: If True, include links to PRs that have no release notes (default=False)

github_release_report
==========================================

**Description:** Parses GitHub release notes to report various info

**Class::** cumulusci.tasks.github.ReleaseReport

Options:
------------------------------------------

* **date_start**: Filter out releases created before this date (YYYY-MM-DD)
* **date_end**: Filter out releases created after this date (YYYY-MM-DD)
* **include_beta**: Include beta releases in report [default=False]
* **print**: Print info to screen as JSON [default=False]

install_managed
==========================================

**Description:** Install the latest managed production release

**Class::** cumulusci.tasks.salesforce.InstallPackageVersion

Options:
------------------------------------------

* **name**: The name of the package to install.  Defaults to project__package__name_managed
* **namespace** *(required)*: The namespace of the package to install.  Defaults to project__package__namespace
* **version** *(required)*: The version of the package to install.  "latest" and "latest_beta" can be used to trigger lookup via Github Releases on the repository. **Default: latest**
* **activateRSS**: If True, preserve the isActive state of Remote Site Settings and Content Security Policy in the package. Default: False. **Default: True**
* **password**: The package password. Optional.
* **retries**: Number of retries (default=5)
* **retry_interval**: Number of seconds to wait before the next retry (default=5),
* **retry_interval_add**: Number of seconds to add before each retry (default=30),

install_managed_beta
==========================================

**Description:** Installs the latest managed beta release

**Class::** cumulusci.tasks.salesforce.InstallPackageVersion

Options:
------------------------------------------

* **name**: The name of the package to install.  Defaults to project__package__name_managed
* **namespace** *(required)*: The namespace of the package to install.  Defaults to project__package__namespace
* **version** *(required)*: The version of the package to install.  "latest" and "latest_beta" can be used to trigger lookup via Github Releases on the repository. **Default: latest_beta**
* **activateRSS**: If True, preserve the isActive state of Remote Site Settings and Content Security Policy in the package. Default: False. **Default: True**
* **password**: The package password. Optional.
* **retries**: Number of retries (default=5)
* **retry_interval**: Number of seconds to wait before the next retry (default=5),
* **retry_interval_add**: Number of seconds to add before each retry (default=30),

list_communities
==========================================

**Description:** Lists Communities for the current org using the Connect API.

**Class::** cumulusci.tasks.salesforce.ListCommunities

Lists Communities for the current org via the Connect API.



list_community_templates
==========================================

**Description:** Prints the Community Templates available to the current org

**Class::** cumulusci.tasks.salesforce.ListCommunityTemplates

Lists Salesforce Community templates available for the current org via the Connect API.



list_metadata_types
==========================================

**Description:** Prints the metadata types in a project

**Class::** cumulusci.tasks.util.ListMetadataTypes

Options:
------------------------------------------

* **package_xml**: The project package.xml file. Defaults to <project_root>/src/package.xml

meta_xml_apiversion
==========================================

**Description:** Set the API version in ``*meta.xml`` files

**Class::** cumulusci.tasks.metaxml.UpdateApi

Options:
------------------------------------------

* **dir**: Base directory to search for ``*-meta.xml`` files
* **version** *(required)*: API version number e.g. 37.0

meta_xml_dependencies
==========================================

**Description:** Set the version for dependent packages

**Class::** cumulusci.tasks.metaxml.UpdateDependencies

Options:
------------------------------------------

* **dir**: Base directory to search for ``*-meta.xml`` files

metadeploy_publish
==========================================

**Description:** Publish a release to the MetaDeploy web installer

**Class::** cumulusci.tasks.metadeploy.Publish

Options:
------------------------------------------

* **tag**: Name of the git tag to publish
* **commit**: Commit hash to publish
* **plan**: Name of the plan(s) to publish. This refers to the `plans` section of cumulusci.yml. By default, all plans will be published.
* **dry_run**: If True, print steps without publishing.
* **publish**: If True, set is_listed to True on the version. Default: False

org_settings
==========================================

**Description:** Apply org settings from a scratch org definition file

**Class::** cumulusci.tasks.salesforce.org_settings.DeployOrgSettings

Options:
------------------------------------------

* **definition_file**: sfdx scratch org definition file
* **api_version**: API version used to deploy the settings

publish_community
==========================================

**Description:** Publishes a Community in the target org using the Connect API

**Class::** cumulusci.tasks.salesforce.PublishCommunity

Publish a Salesforce Community via the Connect API. Warning: This does not work with the Community Template 'VF Template' due to an existing bug in the API.


Options:
------------------------------------------

* **name**: The name of the Community to publish.
* **community_id**: The id of the Community to publish.

push_all
==========================================

**Description:** Schedules a push upgrade of a package version to all subscribers

**Class::** cumulusci.tasks.push.tasks.SchedulePushOrgQuery

Options:
------------------------------------------

* **version** *(required)*: The managed package version to push
* **subscriber_where**: A SOQL style WHERE clause for filtering PackageSubscriber objects. Ex: OrgType = 'Sandbox'
* **min_version**: If set, no subscriber with a version lower than min_version will be selected for push
* **namespace**: The managed package namespace to push. Defaults to project__package__namespace.
* **start_time**: Set the start time (UTC) to queue a future push. Ex: 2016-10-19T10:00

push_list
==========================================

**Description:** Schedules a push upgrade of a package version to all orgs listed in the specified file

**Class::** cumulusci.tasks.push.tasks.SchedulePushOrgList

Options:
------------------------------------------

* **orgs** *(required)*: The path to a file containing one OrgID per line.
* **version** *(required)*: The managed package version to push
* **namespace**: The managed package namespace to push. Defaults to project__package__namespace.
* **start_time**: Set the start time (UTC) to queue a future push. Ex: 2016-10-19T10:00
* **batch_size**: Break pull requests into batches of this many orgs. Defaults to 200.

push_qa
==========================================

**Description:** Schedules a push upgrade of a package version to all orgs listed in push/orgs_qa.txt

**Class::** cumulusci.tasks.push.tasks.SchedulePushOrgList

Options:
------------------------------------------

* **orgs** *(required)*: The path to a file containing one OrgID per line. **Default: push/orgs_qa.txt**
* **version** *(required)*: The managed package version to push
* **namespace**: The managed package namespace to push. Defaults to project__package__namespace.
* **start_time**: Set the start time (UTC) to queue a future push. Ex: 2016-10-19T10:00
* **batch_size**: Break pull requests into batches of this many orgs. Defaults to 200.

push_sandbox
==========================================

**Description:** Schedules a push upgrade of a package version to all subscribers

**Class::** cumulusci.tasks.push.tasks.SchedulePushOrgQuery

Options:
------------------------------------------

* **version** *(required)*: The managed package version to push
* **subscriber_where**: A SOQL style WHERE clause for filtering PackageSubscriber objects. Ex: OrgType = 'Sandbox' **Default: OrgType = 'Sandbox'**
* **min_version**: If set, no subscriber with a version lower than min_version will be selected for push
* **namespace**: The managed package namespace to push. Defaults to project__package__namespace.
* **start_time**: Set the start time (UTC) to queue a future push. Ex: 2016-10-19T10:00

push_trial
==========================================

**Description:** Schedules a push upgrade of a package version to Trialforce Template orgs listed in push/orgs_trial.txt

**Class::** cumulusci.tasks.push.tasks.SchedulePushOrgList

Options:
------------------------------------------

* **orgs** *(required)*: The path to a file containing one OrgID per line. **Default: push/orgs_trial.txt**
* **version** *(required)*: The managed package version to push
* **namespace**: The managed package namespace to push. Defaults to project__package__namespace.
* **start_time**: Set the start time (UTC) to queue a future push. Ex: 2016-10-19T10:00
* **batch_size**: Break pull requests into batches of this many orgs. Defaults to 200.

push_failure_report
==========================================

**Description:** Produce a CSV report of the failed and otherwise anomalous push jobs.

**Class::** cumulusci.tasks.push.pushfails.ReportPushFailures

Options:
------------------------------------------

* **request_id** *(required)*: PackagePushRequest ID for the request you need to report on.
* **result_file**: Path to write a CSV file with the results. Defaults to 'push_fails.csv'.
* **ignore_errors**: List of ErrorTitle and ErrorType values to omit from the report **Default: ['Salesforce Subscription Expired', 'Package Uninstalled']**

query
==========================================

**Description:** Queries the connected org

**Class::** cumulusci.tasks.salesforce.SOQLQuery

Options:
------------------------------------------

* **object** *(required)*: The object to query
* **query** *(required)*: A valid bulk SOQL query for the object
* **result_file** *(required)*: The name of the csv file to write the results to

retrieve_packaged
==========================================

**Description:** Retrieves the packaged metadata from the org

**Class::** cumulusci.tasks.salesforce.RetrievePackaged

Options:
------------------------------------------

* **path** *(required)*: The path to write the retrieved metadata **Default: packaged**
* **unmanaged**: If True, changes namespace_inject to replace tokens with a blank string
* **namespace_inject**: If set, the namespace tokens in files and filenames are replaced with the namespace's prefix
* **namespace_strip**: If set, all namespace prefixes for the namespace specified are stripped from files and filenames
* **namespace_tokenize**: If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject
* **namespaced_org**: If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.
* **package** *(required)*: The package name to retrieve.  Defaults to project__package__name
* **api_version**: Override the default api version for the retrieve. Defaults to project__package__api_version

retrieve_src
==========================================

**Description:** Retrieves the packaged metadata into the src directory

**Class::** cumulusci.tasks.salesforce.RetrievePackaged

Options:
------------------------------------------

* **path** *(required)*: The path to write the retrieved metadata **Default: src**
* **unmanaged**: If True, changes namespace_inject to replace tokens with a blank string
* **namespace_inject**: If set, the namespace tokens in files and filenames are replaced with the namespace's prefix
* **namespace_strip**: If set, all namespace prefixes for the namespace specified are stripped from files and filenames
* **namespace_tokenize**: If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject
* **namespaced_org**: If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.
* **package** *(required)*: The package name to retrieve.  Defaults to project__package__name
* **api_version**: Override the default api version for the retrieve. Defaults to project__package__api_version

retrieve_unpackaged
==========================================

**Description:** Retrieve the contents of a package.xml file.

**Class::** cumulusci.tasks.salesforce.RetrieveUnpackaged

Options:
------------------------------------------

* **path** *(required)*: The path to write the retrieved metadata
* **unmanaged**: If True, changes namespace_inject to replace tokens with a blank string
* **namespace_inject**: If set, the namespace tokens in files and filenames are replaced with the namespace's prefix
* **namespace_strip**: If set, all namespace prefixes for the namespace specified are stripped from files and filenames
* **namespace_tokenize**: If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject
* **namespaced_org**: If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.
* **package_xml** *(required)*: The path to a package.xml manifest to use for the retrieve.
* **api_version**: Override the default api version for the retrieve. Defaults to project__package__api_version

list_changes
==========================================

**Description:** List the changes from a scratch org

**Class::** cumulusci.tasks.salesforce.sourcetracking.ListChanges

Options:
------------------------------------------

* **include**: A comma-separated list of strings. Components will be included if one of these strings is part of either the metadata type or name. Example: ``-o include CustomField,Admin`` matches both ``CustomField: Favorite_Color__c`` and ``Profile: Admin``
* **types**: A comma-separated list of metadata types to include.
* **exclude**: Exclude changed components matching this string.
* **snapshot**: If True, all matching items will be set to be ignored at their current revision number.  This will exclude them from the results unless a new edit is made.

retrieve_changes
==========================================

**Description:** Retrieve changed components from a scratch org

**Class::** cumulusci.tasks.salesforce.sourcetracking.RetrieveChanges

Options:
------------------------------------------

* **include**: A comma-separated list of strings. Components will be included if one of these strings is part of either the metadata type or name. Example: ``-o include CustomField,Admin`` matches both ``CustomField: Favorite_Color__c`` and ``Profile: Admin``
* **types**: A comma-separated list of metadata types to include.
* **exclude**: Exclude changed components matching this string.
* **snapshot**: If True, all matching items will be set to be ignored at their current revision number.  This will exclude them from the results unless a new edit is made.
* **path**: The path to write the retrieved metadata
* **api_version**: Override the default api version for the retrieve. Defaults to project__package__api_version
* **namespace_tokenize**: If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject

retrieve_qa_config
==========================================

**Description:** Retrieves the current changes in the scratch org into unpackaged/config/qa

**Class::** cumulusci.tasks.salesforce.sourcetracking.RetrieveChanges

Options:
------------------------------------------

* **include**: A comma-separated list of strings. Components will be included if one of these strings is part of either the metadata type or name. Example: ``-o include CustomField,Admin`` matches both ``CustomField: Favorite_Color__c`` and ``Profile: Admin``
* **types**: A comma-separated list of metadata types to include.
* **exclude**: Exclude changed components matching this string.
* **snapshot**: If True, all matching items will be set to be ignored at their current revision number.  This will exclude them from the results unless a new edit is made.
* **path**: The path to write the retrieved metadata **Default: unpackaged/config/qa**
* **api_version**: Override the default api version for the retrieve. Defaults to project__package__api_version
* **namespace_tokenize**: If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject **Default: $project_config.project__package__namespace**

snapshot_changes
==========================================

**Description:** Tell SFDX source tracking to ignore previous changes in a scratch org

**Class::** cumulusci.tasks.salesforce.sourcetracking.SnapshotChanges


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

robot
==========================================

**Description:** Runs a Robot Framework test from a .robot file

**Class::** cumulusci.tasks.robotframework.Robot

Options:
------------------------------------------

* **suites** *(required)*: Paths to test case files/directories to be executed similarly as when running the robot command on the command line.  Defaults to "tests" to run all tests in the tests directory **Default: tests**
* **test**: Run only tests matching name patterns.  Can be comma separated and use robot wildcards like *
* **include**: Includes tests with a given tag
* **exclude**: Excludes tests with a given tag
* **vars**: Pass values to override variables in the format VAR1:foo,VAR2:bar
* **xunit**: Set an XUnit format output file for test results
* **options**: A dictionary of options to robot.run method.  See docs here for format.  NOTE: There is no cci CLI support for this option since it requires a dictionary.  Use this option in the cumulusci.yml when defining custom tasks where you can easily create a dictionary in yaml.
* **name**: Sets the name of the top level test suite
* **pdb**: If true, run the Python debugger when tests fail.
* **verbose**: If true, log each keyword as it runs.
* **debug**: If true, enable the `breakpoint` keyword to enable the robot debugger

robot_libdoc
==========================================

**Description:** Generates documentation for project keyword files

**Class::** cumulusci.tasks.robotframework.RobotLibDoc

Options:
------------------------------------------

* **path** *(required)*: The path to one or more keyword libraries to be documented. The path can be single a python file, a .robot file, a python module (eg: cumulusci.robotframework.Salesforce) or a comma separated list of any of those. Glob patterns are supported for filenames (eg: robot/SAL/doc/*PageObject.py). The order of the files will be preserved in the generated documentation. The result of pattern expansion will be sorted
* **output** *(required)*: The output file where the documentation will be written **Default: Keywords.html**
* **title**: A string to use as the title of the generated output **Default: $project_config.project__package__name**

robot_lint
==========================================

**Description:** Static analysis tool for robot framework files

**Class::** cumulusci.tasks.robotframework.RobotLint

The robot_lint task performs static analysis on one or more .robot
and .resource files. Each line is parsed, and the result passed through
a series of rules. Rules can issue warnings or errors about each line.

If any errors are reported, the task will exit with a non-zero status.

When a rule has been violated, a line will appear on the output in
the following format:

*<severity>*: *<line>*, *<character>*: *<description>* (*<name>*)

- *<severity>* will be either W for warning or E for error
- *<line>* is the line number where the rule was triggered
- *<character>* is the character where the rule was triggered,
  or 0 if the rule applies to the whole line
- *<description>* is a short description of the issue
- *<name>* is the name of the rule that raised the issue

Note: the rule name can be used with the ignore, warning, error,
and configure options.

Some rules are configurable, and can be configured with the
`configure` option. This option takes a list of values in the form
*<rule>*:*<value>*,*<rule>*:*<value>*,etc.  For example, to set
the line length for the LineTooLong rule you can use '-o configure
LineTooLong:80'. If a rule is configurable, it will show the
configuration options in the documentation for that rule

The filename will be printed once before any errors or warnings
for that file. The filename is preceeded by `+`

Example Output::

    + example.robot
    W: 2, 0: No suite documentation (RequireSuiteDocumentation)
    E: 30, 0: No testcase documentation (RequireTestDocumentation)

To see a list of all configured options, set the 'list' option to True:

    cci task run robot_list -o list True



Options:
------------------------------------------

* **configure**: List of rule configuration values, in the form of rule:args.
* **ignore**: List of rules to ignore. Use 'all' to ignore all rules
* **error**: List of rules to treat as errors. Use 'all' to affect all rules.
* **warning**: List of rules to treat as warnings. Use 'all' to affect all rules.
* **list**: If option is True, print a list of known rules instead of processing files.
* **path**: The path to one or more files or folders. If the path includes wildcard characters, they will be expanded. If not provided, the default will be to process all files under robot/<project name>

robot_testdoc
==========================================

**Description:** Generates html documentation of your Robot test suite and writes to tests/test_suite.

**Class::** cumulusci.tasks.robotframework.RobotTestDoc

Options:
------------------------------------------

* **path** *(required)*: The path containing .robot test files **Default: tests**
* **output** *(required)*: The output html file where the documentation will be written **Default: tests/test_suites.html**

run_tests
==========================================

**Description:** Runs all apex tests

**Class::** cumulusci.tasks.apex.testrunner.RunApexTests

Options:
------------------------------------------

* **test_name_match** *(required)*: Query to find Apex test classes to run ("%" is wildcard).  Defaults to project__test__name_match
* **test_name_exclude**: Query to find Apex test classes to exclude ("%" is wildcard).  Defaults to project__test__name_exclude
* **namespace**: Salesforce project namespace.  Defaults to project__package__namespace
* **managed**: If True, search for tests in the namespace only.  Defaults to False
* **poll_interval**: Seconds to wait between polling for Apex test results.
* **junit_output**: File name for JUnit output.  Defaults to test_results.xml
* **json_output**: File name for json output.  Defaults to test_results.json
* **retry_failures**: A list of regular expression patterns to match against test failures. If failures match, the failing tests are retried in serial mode.
* **retry_always**: By default, all failures must match retry_failures to perform a retry. Set retry_always to True to retry all failed tests if any failure matches.

uninstall_managed
==========================================

**Description:** Uninstalls the managed version of the package

**Class::** cumulusci.tasks.salesforce.UninstallPackage

Options:
------------------------------------------

* **namespace** *(required)*: The namespace of the package to uninstall.  Defaults to project__package__namespace
* **purge_on_delete** *(required)*: Sets the purgeOnDelete option for the deployment.  Defaults to True

uninstall_packaged
==========================================

**Description:** Uninstalls all deleteable metadata in the package in the target org

**Class::** cumulusci.tasks.salesforce.UninstallPackaged

Options:
------------------------------------------

* **package** *(required)*: The package name to uninstall.  All metadata from the package will be retrieved and a custom destructiveChanges.xml package will be constructed and deployed to delete all deleteable metadata from the package.  Defaults to project__package__name
* **purge_on_delete** *(required)*: Sets the purgeOnDelete option for the deployment.  Defaults to True

uninstall_packaged_incremental
==========================================

**Description:** Deletes any metadata from the package in the target org not in the local workspace

**Class::** cumulusci.tasks.salesforce.UninstallPackagedIncremental

Options:
------------------------------------------

* **path** *(required)*: The local path to compare to the retrieved packaged metadata from the org.  Defaults to src
* **package** *(required)*: The package name to uninstall.  All metadata from the package will be retrieved and a custom destructiveChanges.xml package will be constructed and deployed to delete all deleteable metadata from the package.  Defaults to project__package__name
* **purge_on_delete** *(required)*: Sets the purgeOnDelete option for the deployment.  Defaults to True
* **ignore**: Components to ignore in the org and not try to delete. Mapping of component type to a list of member names.

uninstall_src
==========================================

**Description:** Uninstalls all metadata in the local src directory

**Class::** cumulusci.tasks.salesforce.UninstallLocal

Options:
------------------------------------------

* **path** *(required)*: The path to the parent directory containing the metadata bundles directories **Default: src**
* **unmanaged**: If True, changes namespace_inject to replace tokens with a blank string
* **namespace_inject**: If set, the namespace tokens in files and filenames are replaced with the namespace's prefix
* **namespace_strip**: If set, all namespace prefixes for the namespace specified are stripped from files and filenames
* **namespace_tokenize**: If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject
* **check_only**: If True, performs a test deployment (validation) of components without saving the components in the target org
* **test_level**: Specifies which tests are run as part of a deployment. Valid values: NoTestRun, RunLocalTests, RunAllTestsInOrg, RunSpecifiedTests.
* **specified_tests**: Comma-separated list of test classes to run upon deployment. Applies only with test_level set to RunSpecifiedTests.
* **static_resource_path**: The path where decompressed static resources are stored.  Any subdirectories found will be zipped and added to the staticresources directory of the build.
* **namespaced_org**: If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.
* **clean_meta_xml**: Defaults to True which strips the <packageVersions/> element from all meta.xml files.  The packageVersion element gets added automatically by the target org and is set to whatever version is installed in the org.  To disable this, set this option to False
* **purge_on_delete**: Sets the purgeOnDelete option for the deployment. Defaults to True

uninstall_pre
==========================================

**Description:** Uninstalls the unpackaged/pre bundles

**Class::** cumulusci.tasks.salesforce.UninstallLocalBundles

Options:
------------------------------------------

* **path** *(required)*: The path to the parent directory containing the metadata bundles directories **Default: unpackaged/pre**
* **unmanaged**: If True, changes namespace_inject to replace tokens with a blank string
* **namespace_inject**: If set, the namespace tokens in files and filenames are replaced with the namespace's prefix
* **namespace_strip**: If set, all namespace prefixes for the namespace specified are stripped from files and filenames
* **namespace_tokenize**: If set, all namespace prefixes for the namespace specified are replaced with tokens for use with namespace_inject
* **check_only**: If True, performs a test deployment (validation) of components without saving the components in the target org
* **test_level**: Specifies which tests are run as part of a deployment. Valid values: NoTestRun, RunLocalTests, RunAllTestsInOrg, RunSpecifiedTests.
* **specified_tests**: Comma-separated list of test classes to run upon deployment. Applies only with test_level set to RunSpecifiedTests.
* **static_resource_path**: The path where decompressed static resources are stored.  Any subdirectories found will be zipped and added to the staticresources directory of the build.
* **namespaced_org**: If True, the tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.
* **clean_meta_xml**: Defaults to True which strips the <packageVersions/> element from all meta.xml files.  The packageVersion element gets added automatically by the target org and is set to whatever version is installed in the org.  To disable this, set this option to False
* **purge_on_delete**: Sets the purgeOnDelete option for the deployment. Defaults to True

uninstall_post
==========================================

**Description:** Uninstalls the unpackaged/post bundles

**Class::** cumulusci.tasks.salesforce.UninstallLocalNamespacedBundles

Options:
------------------------------------------

* **path** *(required)*: The path to a directory containing the metadata bundles (subdirectories) to uninstall **Default: unpackaged/post**
* **managed**: If True, will insert the actual namespace prefix.  Defaults to False or no namespace
* **namespace**: The namespace to replace the token with if in managed mode. Defaults to project__package__namespace
* **filename_token** *(required)*: The path to the parent directory containing the metadata bundles directories **Default: ___NAMESPACE___**
* **purge_on_delete** *(required)*: Sets the purgeOnDelete option for the deployment.  Defaults to True

unschedule_apex
==========================================

**Description:** Unschedule all scheduled apex jobs (CronTriggers).

**Class::** cumulusci.tasks.apex.anon.AnonymousApexTask

Use the `apex` option to run a string of anonymous Apex.
Use the `path` option to run anonymous Apex from a file.
Or use both to concatenate the string to the file contents.


Options:
------------------------------------------

* **path**: The path to an Apex file to run.
* **apex**: A string of Apex to run (after the file, if specified). **Default: for (CronTrigger t : [SELECT Id FROM CronTrigger]) { System.abortJob(t.Id); }**
* **managed**: If True, will insert the project's namespace prefix.  Defaults to False or no namespace.
* **namespaced**: If True, the tokens %%%NAMESPACED_RT%%% and %%%namespaced%%% will get replaced with the namespace prefix for Record Types.

update_admin_profile
==========================================

**Description:** Retrieves, edits, and redeploys the Admin.profile with full FLS perms for all objects/fields

**Class::** cumulusci.tasks.salesforce.UpdateAdminProfile

Options:
------------------------------------------

* **package_xml**: Override the default package.xml file for retrieving the Admin.profile and all objects and classes that need to be included by providing a path to your custom package.xml
* **record_types**: A list of dictionaries containing the required key `record_type` with a value specifying the record type in format <object>.<developer_name>.  Record type names can use the token strings {managed} and {namespaced_org} for namespace prefix injection as needed.  By default, all listed record types will be set to visible and not default.  Use the additional keys `visible`, `default`, and `person_account_default` set to true/false to override.  NOTE: Setting record_types is only supported in cumulusci.yml, command line override is not supported.
* **managed**: If True, uses the namespace prefix where appropriate.  Use if running against an org with the managed package installed.  Defaults to False
* **namespaced_org**: If True, attempts to prefix all unmanaged metadata references with the namespace prefix for deployment to the packaging org or a namespaced scratch org.  Defaults to False

update_dependencies
==========================================

**Description:** Installs all dependencies in project__dependencies into the target org

**Class::** cumulusci.tasks.salesforce.UpdateDependencies

Options:
------------------------------------------

* **dependencies**: List of dependencies to update. Defaults to project__dependencies. Each dependency is a dict with either 'github' set to a github repository URL or 'namespace' set to a Salesforce package namespace. Github dependencies may include 'tag' to install a particular git ref. Package dependencies may include 'version' to install a particular version.
* **namespaced_org**: If True, the changes namespace token injection on any dependencies so tokens %%%NAMESPACED_ORG%%% and ___NAMESPACED_ORG___ will get replaced with the namespace.  The default is false causing those tokens to get stripped and replaced with an empty string.  Set this if deploying to a namespaced scratch org or packaging org.
* **purge_on_delete**: Sets the purgeOnDelete option for the deployment. Defaults to True
* **include_beta**: Install the most recent release, even if beta. Defaults to False.
* **allow_newer**: If the org already has a newer release, use it. Defaults to True.
* **allow_uninstalls**: Allow uninstalling a beta release or newer final release in order to install the requested version. Defaults to False. Warning: Enabling this may destroy data.

update_package_xml
==========================================

**Description:** Updates src/package.xml with metadata in src/

**Class::** cumulusci.tasks.metadata.package.UpdatePackageXml

Options:
------------------------------------------

* **path** *(required)*: The path to a folder of metadata to build the package.xml from **Default: src**
* **output**: The output file, defaults to <path>/package.xml
* **package_name**: If set, overrides the package name inserted into the <fullName> element
* **managed**: If True, generate a package.xml for deployment to the managed package packaging org
* **delete**: If True, generate a package.xml for use as a destructiveChanges.xml file for deleting metadata

upload_beta
==========================================

**Description:** Uploads a beta release of the metadata currently in the packaging org

**Class::** cumulusci.tasks.salesforce.PackageUpload

Options:
------------------------------------------

* **name** *(required)*: The name of the package version.
* **production**: If True, uploads a production release.  Defaults to uploading a beta
* **description**: A description of the package and what this version contains.
* **password**: An optional password for sharing the package privately with anyone who has the password. Don't enter a password if you want to make the package available to anyone on AppExchange and share your package publicly.
* **post_install_url**: The fully-qualified URL of the post-installation instructions. Instructions are shown as a link after installation and are available from the package detail view.
* **release_notes_url**: The fully-qualified URL of the package release notes. Release notes are shown as a link during the installation process and are available from the package detail view after installation.
* **namespace**: The namespace of the package.  Defaults to project__package__namespace

upload_production
==========================================

**Description:** Uploads a production release of the metadata currently in the packaging org

**Class::** cumulusci.tasks.salesforce.PackageUpload

Options:
------------------------------------------

* **name** *(required)*: The name of the package version. **Default: Release**
* **production**: If True, uploads a production release.  Defaults to uploading a beta **Default: True**
* **description**: A description of the package and what this version contains.
* **password**: An optional password for sharing the package privately with anyone who has the password. Don't enter a password if you want to make the package available to anyone on AppExchange and share your package publicly.
* **post_install_url**: The fully-qualified URL of the post-installation instructions. Instructions are shown as a link after installation and are available from the package detail view.
* **release_notes_url**: The fully-qualified URL of the package release notes. Release notes are shown as a link during the installation process and are available from the package detail view after installation.
* **namespace**: The namespace of the package.  Defaults to project__package__namespace

util_sleep
==========================================

**Description:** Sleeps for N seconds

**Class::** cumulusci.tasks.util.Sleep

Options:
------------------------------------------

* **seconds** *(required)*: The number of seconds to sleep **Default: 5**

log
==========================================

**Description:** Log a line at the info level.

**Class::** cumulusci.tasks.util.LogLine

Options:
------------------------------------------

* **level** *(required)*: The logger level to use **Default: info**
* **line** *(required)*: A formatstring like line to log
* **format_vars**: A Dict of format vars

generate_dataset_mapping
==========================================

**Description:** Create a mapping for extracting data from an org.

**Class::** cumulusci.tasks.bulkdata.GenerateMapping

Generate a mapping file for use with the `extract_dataset` and `load_dataset` tasks.
This task will examine the schema in the specified org and attempt to infer a
mapping suitable for extracting data in packaged and custom objects as well as
customized standard objects.

Mappings must be serializable, and hence must resolve reference cycles - situations
where Object A refers to B, and B also refers to A. Mapping generation will stop
and request user input to resolve such cycles by identifying the correct load order.
Alternately, specify the `ignore` option with the name of one of the
lookup fields to suppress it and break the cycle. `ignore` can be specified as a list in
`cumulusci.yml` or as a comma-separated string at the command line.

In most cases, the mapping generated will need minor tweaking by the user. Note
that the mapping omits features that are not currently well supported by the
`extract_dataset` and `load_dataset` tasks, such as references to
the `User` object.


Options:
------------------------------------------

* **path** *(required)*: Location to write the mapping file **Default: datasets/mapping.yml**
* **namespace_prefix**: The namespace prefix to use **Default: $project_config.project__package__namespace**
* **ignore**: Object API names, or fields in Object.Field format, to ignore

extract_dataset
==========================================

**Description:** Extract a sample dataset using the bulk API.

**Class::** cumulusci.tasks.bulkdata.ExtractData

Options:
------------------------------------------

* **database_url**: A DATABASE_URL where the query output should be written
* **mapping** *(required)*: The path to a yaml file containing mappings of the database fields to Salesforce object fields **Default: datasets/mapping.yml**
* **sql_path**: If set, an SQL script will be generated at the path provided This is useful for keeping data in the repository and allowing diffs. **Default: datasets/sample.sql**

load_dataset
==========================================

**Description:** Load a sample dataset using the bulk API.

**Class::** cumulusci.tasks.bulkdata.LoadData

Options:
------------------------------------------

* **database_url**: The database url to a database containing the test data to load
* **mapping** *(required)*: The path to a yaml file containing mappings of the database fields to Salesforce object fields **Default: datasets/mapping.yml**
* **start_step**: If specified, skip steps before this one in the mapping
* **sql_path**: If specified, a database will be created from an SQL script at the provided path **Default: datasets/sample.sql**
* **ignore_row_errors**: If True, allow the load to continue even if individual rows fail to load.
* **reset_oids**: If True (the default), and the _sf_ids tables exist, reset them before continuing.
* **bulk_mode**: Set to Serial to force serial mode on all jobs. Parallel is the default.

load_custom_settings
==========================================

**Description:** Load Custom Settings specified in a YAML file to the target org

**Class::** cumulusci.tasks.salesforce.LoadCustomSettings

Options:
------------------------------------------

* **settings_path** *(required)*: The path to a YAML settings file

remove_metadata_xml_elements
==========================================

**Description:** Remove specified XML elements from one or more metadata files

**Class::** cumulusci.tasks.metadata.modify.RemoveElementsXPath

Options:
------------------------------------------

* **xpath**: An XPath specification of elements to remove. Supports the re: regexp function namespace. As in re:match(text(), '.*__c')Use ns: to refer to the Salesforce namespace for metadata elements.for example: ./ns:Layout/ns:relatedLists (one-level) or //ns:relatedLists (recursive)Many advanced examples are available here: https://github.com/SalesforceFoundation/NPSP/blob/26b585409720e2004f5b7785a56e57498796619f/cumulusci.yml#L342
* **path**: A path to the files to change. Supports wildcards including ** for directory recursion. More info on the details: https://www.poftut.com/python-glob-function-to-match-path-directory-file-names-with-examples/ https://www.tutorialspoint.com/How-to-use-Glob-function-to-find-files-recursively-in-Python 
* **elements**: A list of dictionaries containing path and xpath keys. Multiple dictionaries can be passed in the list to run multiple removal queries in the same task. This parameter is intended for usages invoked as part of a cumulusci.yml .
* **chdir**: Change the current directory before running the replace

disable_tdtm_trigger_handlers
==========================================

**Description:** Disable specified TDTM trigger handlers

**Class::** cumulusci.tasks.salesforce.trigger_handlers.SetTDTMHandlerStatus

Options:
------------------------------------------

* **handlers**: List of Trigger Handlers (by Class, Object, or 'Class:Object') to affect (defaults to all handlers).
* **namespace**: The namespace of the Trigger Handler object ('eda' or 'npsp'). The task will apply the namespace if needed.
* **active**: True or False to activate or deactivate trigger handlers.
* **restore_file**: Path to the state file to store the current trigger handler state. **Default: trigger_status.yml**
* **restore**: If True, restore the state of Trigger Handlers to that stored in the restore file.

restore_tdtm_trigger_handlers
==========================================

**Description:** Restore status of TDTM trigger handlers

**Class::** cumulusci.tasks.salesforce.trigger_handlers.SetTDTMHandlerStatus

Options:
------------------------------------------

* **handlers**: List of Trigger Handlers (by Class, Object, or 'Class:Object') to affect (defaults to all handlers).
* **namespace**: The namespace of the Trigger Handler object ('eda' or 'npsp'). The task will apply the namespace if needed.
* **active**: True or False to activate or deactivate trigger handlers.
* **restore_file**: Path to the state file to store the current trigger handler state. **Default: trigger_status.yml**
* **restore**: If True, restore the state of Trigger Handlers to that stored in the restore file. **Default: True**

