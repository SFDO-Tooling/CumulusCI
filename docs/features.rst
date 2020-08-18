========
Features
========

This section provides more detail on some of the features of CumulusCI.

Org Keychain
============

CumulusCI uses OAuth connections to Salesforce orgs stored in a configurable keychain which by default stores in AES encrypted files in the user's home directory.  A few important things to note about CumulusCI's keychain:

* The keychain is specific to your local git repository.  Thus, there is no need to have orgs named ``ProjectA_dev`` since CumulusCI's keychain is already specific to ``ProjectA`` by being inside the local repo.  You can keep your org names simple like ``dev``.
* CumulusCI's keychain can handle both persistent orgs (Prod, Sandbox, Packaging, DE) and Salesforce DX Scratch Orgs.
* The keychain class is pluggable allowing different keychain implementations such as ``EnvironmentProjectKeychain``

Org List
--------

When inside a local project repository, you can see all the orgs you have configured:

.. code-block:: console

    $ cci org list

Logging into an Org
-------------------

You can log into any org in the keychain in a new browser tab:

.. code-block:: console

    $ cci org browser <org_name>

Persistent Orgs
---------------

The CumulusCI keychain can capture and store OAuth credentials to persistent orgs (Prod, Sandbox, Packaging, DE) using the ``cci org connect`` command:

.. code-block:: console

    $ cci org connect <org_name>

This command will open a browser window where you log into the org you want to connect as the org_name you specified.  Once you log in successfully, you'll get a blank browser window saying "Congratulations".  You can close the window.  At this point, your org is specified.

Specifying a Different Login URL
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In some cases, such as Sandboxes, you need to specify a different login url when connecting to the org.  You can use the ``--sandbox`` or ``--login-url`` options:

.. code-block:: console

    $ cci org connect <org_name> --sandbox

    OR

    $ cci org connect <org_name> --login-url https://test.salesforce.com

Global Orgs
^^^^^^^^^^^

Thus far we've talked about orgs being confined to an individual project's keychain.  However, in some use cases it is helpful to have an org defined globally for all projects to use under the same name.  You can connect a global org with:

.. code-block:: console

    $ cci org connect <org_name> --global

With the ``--global`` flag, the org is created in CumulusCI's global keychain and thus available to all projects under the same org_name.

Individual projects can also override the global org by defining a project org with the same org_name.


CumulusCI & Salesforce DX Scratch Orgs
--------------------------------------

CumulusCI takes a different approach to creating and using scratch orgs that aims to make the process easier and more portable.  In short, a scratch org in CumulusCI's keychain starts out as simply a lazy configuration to generate a scratch org with certain parameters.  The scratch org is only actually generated the first time you attempt to use the scratch org from CumulusCI's keychain.

Some other key differences between CumulusCI scratch orgs and orgs created directly via ``sfdx force:org:create``:

* CumulusCI created scratch orgs default to 1 day unless the scratch config used specifies a different default.  Our default dev config is set to 7 days expiration.  The goal is to help keep your active scratch org count as low as possible while still allowing flexibility to specify different scratch orgs.
* CumulusCI sets an alias on all scratch orgs created using the format ``ProjectName__org_name`` so the orgs can easily be used with the ``sfdx`` command.
* CumulusCI defaults to creating non-namespaced scratch orgs but individual scratch configs can specify that they want to be namespaced.  We've found this to be a better default than always having namespaced orgs which have issues, for example, when trying to install a managed version of the package.

Scratch Org Configs
^^^^^^^^^^^^^^^^^^^

Scratch org configs in CumulusCI are named configurations to create a scratch org with parameters useful to a particular dev/test use case for your particular project.  By default CumulusCI comes with 4 scratch configs:

* **dev**: Intended to be used for development work.  Defaults to a duration of 7 days
* **feature**: Intended to be used for testing a feature branch as unmanaged metadata.  Defaults to 1 day
* **beta**: Intended to be used for testing a beta managed package version.  Defaults to 1 day
* **release**: Intended to be used for testing a production managed package version.  Defaults to 1 day

You can define your own scratch org configs in your project's ``cumulusci.yml`` file:

.. code-block:: yaml

    orgs:
        scratch:
            test_env1:
                config_file: orgs/test_env1.json
                days: 3
                namespaced: True

In the example above, we've defined a new scratch org config named ``test_env1`` which points to a scratch org definition file located at ``orgs/test_env1.json`` in the project repository.  We've also overridden the default expiration days from 1 to 3 and specified that we want this org to have the project's namespace applied.

Auto-Created Scratch Org
^^^^^^^^^^^^^^^^^^^^^^^^

CumulusCI will automatically add all defined scratch org configs from your project to your project's keychain for you.  This does not cause any scratch orgs to be created, but it does make it a lot easier for you to use the scratch orgs configs defined on your project.  If you run ``cci org list`` in a CumulusCI project using only the default scratch configs, you'll see:

.. code-block:: console

    $ cci org list
    org        default  scratch  config_name  username
    ---------  -------  -------  -----------  ------------------------------------
    beta                *        beta
    dev                 *        dev
    feature             *        feature
    release             *        release

Note that the scratch orgs don't have a username.  This is because they're just lazy configs that haven't been used yet and thus haven't actually created a scratch org.

With the example above of defining the ``test_env1`` scratch config in our project's ``cumulusci.yml``, we should see the following by default in the org list:

.. code-block:: console

    $ cci org list
    org        default  scratch  config_name  username
    ---------  -------  -------  -----------  ------------------------------------
    beta                *        beta
    dev                 *        dev
    feature             *        feature
    release             *        release
    test_env1           *        test_env1


Adding a Scratch Org to the Keychain
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In most cases, you can just use the auto-created scratch orgs in the keychain.  However, sometimes it's helpful to define a different scratch org config in the keychain.  Some possible use cases:

* Create a scratch org in the keychain for a particular feature branch
* Create a scratch org in the keychain with a different expiration days value

Adding a new scratch org config to the keychain is easy:

.. code-block:: console

    $ cci org scratch feature feature-123

    $ cci org list
    org        default  scratch  config_name  username
    ---------  -------  -------  -----------  ------------------------------------
    beta                *        beta
    dev                 *        dev
    feature             *        feature
    feature-123         *        feature
    release             *        release

Now you can run any `cci` commands against the new `feature-123` org.  A few commands you could try:

.. code-block:: console

    $ cci org browser feature-123
    $ cci org info feature-123
    $ cci flow run dev_org --org feature-123

Deleting Scratch Orgs
^^^^^^^^^^^^^^^^^^^^^

If a scratch org in the keychain has actually created a scratch org, you can use ``cci org scratch_delete`` to delete the scratch org but leave the config to regenerate it in the keychain:

.. code-block:: console

    $ cci org scratch_delete feature-123

Using ``scratch_delete`` will not remove the feature-123 org from your org list.  This is the intended behavior allowing you to easily recreate scratch orgs from a stored config instead of searching your command history to remember how you last created the org.

If you want to permanently remove an org from the org list, you can use ``cci org remove`` which will completely remove the org from the list.  If the a scratch org has already been created from the config, an attempt to delete the scratch org will be made before removing the org from the keychain:

.. code-block:: console

    $ cci org remove feature-123

Expired Scratch Orgs
^^^^^^^^^^^^^^^^^^^^

Since CumulusCI wraps sfdx for generating scratch orgs, there is a possibility for things to get out of sync between the two keychains.  We try to detect when an org is expired and prompt you to attempt to recreate the org config and spin up a new scratch org.

If for some reason recreating the org doesn't work, you can resolve the issue with:

.. code-block:: console

    $ cci org remove <org_name>
    $ cci org scratch <config_name> <org_name>

Using a Different Dev Hub Org
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, CumulusCI will create scratch orgs using the Dev Hub org that is configured as the defaultdevhubusername in sfdx.
You can switch to a different Dev Hub org within a particular project by configuring the ``devhub`` service:

.. code-block: console

    $ cci service connect devhub --project
    Username: [type the Dev Hub username here]
    devhub is now configured for this project.


Managing Dependencies
=====================

From the beginning, CumulusCI was built to automate the complexities of dependency management for extension package projects.  CumulusCI currently handles three main types of dependencies for projects:

* **Managed Packages**: Require a certain version of a managed package
* **Unmanaged Metadata**: Require the deployment of unmanaged metadata
* **Github Repository**: Dynamically include the dependencies of another CumulusCI configured project

The ``update_dependencies`` task handles deploying the dependencies to the target org and is included in all flows designed to deploy or install to an org.  The task can also be run individually with ``cci task run update_dependencies``.

Managed Package Dependencies
----------------------------

Managed package dependencies are rather simple.  You need the namespace and the version number you want to require:

.. code-block:: yaml

    project:
        dependencies:
            - namespace: npe01
              version: 3.6

Automatic Install, Upgrade, or Uninstall/Install
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When the ``update_dependencies`` task runs, it first retrieves a list of all managed packages in the target org and creates a list of the installed packages and their version numbers.  With the example cumulusci.yml shown above, the following will happen depending on what if npe01 is currently installed:

* If npe01 is not installed, npe01 version 3.6 is installed
* If the org already has npe01 version 3.6 installed then nothing will be done
* If the org has an older version installed, it will be upgraded to version 3.6
* If the org has a newer version or a beta version installed, it will be uninstalled and then version 3.6 will be installed

Hierachical Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^

Managed Package dependencies can handle a hierarchy of dependencies between packages.  An example use case is Salesforce.org's Nonprofit Success Pack, an extension of 5 other managed packages and one of those packages (npo02) is an extension of another (npe01).  This is expressed in cumulusci.yml as:

.. code-block:: yaml

    project:
        dependencies:
            - namespace: npo02
              version: 3.8
              dependencies:
                  - namespace: npe01
                    version: 3.6
            - namespace: npe03
              version: 3.9
            - namespace: npe4
              version: 3.5
            - namespace: npe5
              version: 3.5

In the example above, the project requires npo02 version 3.8 which requires npe01 version 3.6.  By specifying the dependency hierarchy, the ``update_dependencies`` task is able to handle an edge case:  If the target org currently has npe01 version 3.7, npe01 needs to be uninstalled to downgrade to 3.6.  However, npo02 requires npe01 so uninstalling npe01 requires also uninstalling npo02.  In this scenario npe03, npe4, and npe5 do not have to be uninstalled to uninstall npe01.


Unmanaged Metadata Dependencies
-------------------------------

You can specify unmanaged metadata to be deployed by specifying a ``zip_url`` and optionally ``subfolder``, ``namespace_inject``, ``namespace_strip``, and ``unmanaged``:

.. code-block:: yaml

    project:
        dependencies:
            - zip_url: https://SOME_HOST/metadata.zip

When ``update_dependencies`` runs, it will download the zip file and deploy it via the Metadata API's Deploy method.  The zip file must contain valid metadata for use with a deploy including a package.xml file in the root.

Specifying a Subfolder of the Zip File
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can use the ``subfolder`` option to specify a subfolder of the zip file you want to use for the deployment.  This is particularly handy when referring to metadata stored in a Github repository:

.. code-block:: yaml

    project:
        dependencies:
            - zip_url: https://github.com/SalesforceFoundation/CumulusReports/archive/master.zip
              subfolder: CumulusReports-master/record_types

When ``update_dependencies`` runs, it will still download the zip from ``zip_url`` but it will then build a new zip containing only the content of ``subfolder`` starting inside ``subfolder`` as the zip's root.

Injecting Namespace Prefixes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

CumulusCI has support for tokenizing references to the namespace prefix in code.  When tokenized, all occurrences of the namespace prefix (i.e. ``npsp__``), will be replaced with ``%%%NAMESPACE%%%`` inside of files and ``___NAMESPACE___`` in file names.  If the metadata you are deploying has been tokenized, you can use the ``namespace_inject`` and ``unmanaged`` options to inject the namespace:

.. code-block:: yaml

    project:
        dependencies:
            - zip_url: https://github.com/SalesforceFoundation/EDA/archive/master.zip
              subfolder: EDA-master/dev_config/src/admin_config
              namespace_inject: hed

In the above example, the metadata in the zip contains the string tokens ``%%%NAMESPACE%%%`` and ``___NAMESPACE___`` which will be replaced with ``hed__`` before the metadata is deployed.

If you want to deploy tokenized metadata without any namespace references, you have to specify both ``namespace_inject`` and ``unmanaged``:

.. code-block:: yaml

    project:
        dependencies:
            - zip_url: https://github.com/SalesforceFoundation/EDA/archive/master.zip
              subfolder: EDA-master/dev_config/src/admin_config
              namespace_inject: hed
              unmanaged: True

In the above example, the namespace tokens would be replaced with an empty string instead of the namespace effectively stripping the tokens from the files and filenames.

Stripping Namespace Prefixes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If the metadata in the zip you want to deploy has references to a namespace prefix and you want to remove them, use the ``namespace_strip`` option:

.. code-block:: yaml

    project:
        dependencies:
            - zip_url: https://github.com/SalesforceFoundation/CumulusReports/archive/master.zip
              subfolder: CumulusReports-master/src
              namespace_strip: npsp

When ``update_dependencies`` runs, the zip will be retrieved and the string ``npsp__`` will be stripped from all files and filenames in the zip before deployment.  This is most useful if trying to set up an unmanaged development environment for an extension package which normally uses managed dependencies.  The example above takes the NPSP Reports & Dashboards project's unmanaged metadata and strips the references to ``npsp__`` so you could deploy it against an unmanaged version of NPSP.


Github Repository Dependencies
------------------------------

Github Repository dependencies create a dynamic dependency between the current project and another project on Github that uses CumulusCI to manage its dependencies:

.. code-block:: yaml

    project:
        dependencies:
            - github: https://github.com/SalesforceFoundation/EDA

When ``update_dependencies`` runs, the following is doing against the referenced repository:

* Look for cumulusci.yml and parse if found
* Determine if the project has subfolders under unpackaged/pre.  If found, deploys them first.
* Determine if the project specifies any dependencies in cumulusci.yml.  If found, deploys them next in the queue.
* Determine if the project has a namespace configured in cumulusci.yml. If found, treats the project as a managed package unless the unmanaged option is also True.
* If the project has a namespace and is not set for unmanaged, use the Github API to get the latest release and install it.
* If the project is an unmanaged dependency, the src directory is deployed.
* Determine if the project has subfolders under unpackaged/post.  If found, deploys them next.  Namespace tokens are replaced with ``namespace__`` or an empty string depending on if the dependency is considered managed or unmanaged.

Referencing Unmanaged Projects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If the referenced repository does not have a namespace configured or if the dependency specifies the ``unmanaged`` option as true (see example below), the repository is treated as an unmanaged repository:

.. code-block:: yaml

    project:
        dependencies:
            - github: https://github.com/SalesforceFoundation/EDA
              unmanaged: True

In the above example, the EDA repository is configured for a namespace but the dependency specifies ``unmanaged: True`` so the dependency would deploy unmanaged EDA and its dependencies.

Referencing a Specific Tag
^^^^^^^^^^^^^^^^^^^^^^^^^^

If you want to reference a version other than HEAD and the latest production release, you can use the ``tag`` option to specify a particular tag from the target repository.  This is most useful for testing against beta versions of underyling packages or recreating specific org environments for debugging:

.. code-block:: yaml

    project:
        dependencies:
            - github: https://github.com/SalesforceFoundation/EDA
              tag: beta/1.47-Beta_2

In the above example, the EDA repository's tag ``beta/1.47-Beta_2`` will be used instead of the latest production release of EDA (1.46 for this example).  This allows a build environment to use features in the next production release of EDA which are already merged but not yet included in a production release.

Skipping unpackaged/* in Reference Repositories
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If the repository you are referring to has dependency metadata under unpackaged/pre or unpackaged/post and you want to skip deploying that metadata with the dependency, use the **skip** option:

.. code-block:: yaml

    project:
        dependencies:
            - github: https://github.com/SalesforceFoundation/EDA
              skip: unpackaged/post/course_connection_record_types

Case Study: SalesforceFoundation/NPSP
-------------------------------------

The following will create a dependency against the open source repository for Salesforce.org's Nonprofit Success Pack:

.. code-block:: yaml

    project:
        dependencies:
            - github: https://github.com/SalesforceFoundation/NPSP

With this one simple line in the project's dependencies, the following dependencies are included:

* unpackaged/pre/account_record_types from SalesforceFoundation/NPSP
* unpackaged/pre/opportunity_record_types from SalesforceFoundation/NPSP
* npe01 3.6
* npo02 3.8
* npe03 3.8
* npe4 3.5
* npe5 3.5
* npsp 3.99
* unpackaged/post/first from SalesforceFoundation/NPSP with namespace tokens replaced with ``npsp__``

This happens because of the following from the cumulusci.yml in the the NPSP repository:

.. code-block:: yaml

    dependencies:
        # npo02 (includes npe01)
        - github: https://github.com/SalesforceFoundation/Households
        # npe03
        - github: https://github.com/SalesforceFoundation/Recurring_Donations
        # npe4
        - github: https://github.com/SalesforceFoundation/Relationships
        # npe5
        - github: https://github.com/SalesforceFoundation/Affiliations

Note that npo02 includes npe01.  This is because the dependencies for SaleforceFoundation/Households (npo02) contains the following:

.. code-block:: yaml

    dependencies:
        # npe01
        - github: https://github.com/SalesforceFoundation/Contacts_and_Organizations

As a result, npe01 is included because the repository for npo02 refers to npe01's repository as a dependency and NPSP refers to npo02's repository as a dependency.

You can see how complex a single repository dependency can be with the following command output from the single dependency reference to the NPSP repository:

.. code-block:: console

    $ cci task run update_dependencies
    2017-06-03 16:55:29: Getting scratch org info from Salesforce DX
    2017-06-03 16:55:31: Beginning task: UpdateDependencies
    ...
    2017-06-03 16:55:31: Retrieving list of packages from target org
    2017-06-03 16:55:31: Pending
    2017-06-03 16:55:33: [Done]
    2017-06-03 16:55:34: Dependencies:
    2017-06-03 16:55:34: Processing dependencies from Github repo https://github.com/SalesforceFoundation/NPSP
    2017-06-03 16:55:36: Processing dependencies from Github repo https://github.com/SalesforceFoundation/Households
    2017-06-03 16:55:37: Processing dependencies from Github repo https://github.com/SalesforceFoundation/Contacts_and_Organizations
    2017-06-03 16:55:39:     npe01: Install version 3.6
    2017-06-03 16:55:39:     npo02: Install version 3.8
    2017-06-03 16:55:39: Processing dependencies from Github repo https://github.com/SalesforceFoundation/Recurring_Donations
    2017-06-03 16:55:41:     npe03: Install version 3.9
    2017-06-03 16:55:41: Processing dependencies from Github repo https://github.com/SalesforceFoundation/Relationships
    2017-06-03 16:55:42:     npe4: Install version 3.5
    2017-06-03 16:55:42: Processing dependencies from Github repo https://github.com/SalesforceFoundation/Affiliations
    2017-06-03 16:55:43:     npe5: Install version 3.5
    2017-06-03 16:55:43:     npsp: Install version 3.99
    2017-06-03 16:55:43: Deploying unmanaged metadata from /NPSP-dev/unpackaged/pre/account_record_types of https://github.com/SalesforceFoundation/NPSP/archive/dev.zip
    2017-06-03 16:55:48: Pending
    2017-06-03 16:55:49: [InProgress]: Processing Type: CustomObject
    2017-06-03 16:55:50: [Done]
    2017-06-03 16:55:51: [Success]: Succeeded
    2017-06-03 16:55:51: Deploying unmanaged metadata from /NPSP-dev/unpackaged/pre/opportunity_record_types of https://github.com/SalesforceFoundation/NPSP/archive/dev.zip
    2017-06-03 16:55:56: Pending
    2017-06-03 16:55:57: [InProgress]: Processing Type: CustomObject
    2017-06-03 16:55:59: [Done]
    2017-06-03 16:56:00: [Success]: Succeeded
    2017-06-03 16:56:00: Installing npe01 version 3.6
    2017-06-03 16:56:00: Pending
    2017-06-03 16:56:01: [Pending]: next check in 1 seconds
    2017-06-03 16:56:03: [InProgress]: Processing Type: InstalledPackage
    ...
    2017-06-03 16:56:24: [Done]
    2017-06-03 16:56:25: [Success]: Succeeded
    2017-06-03 16:56:25: Installing npo02 version 3.8
    2017-06-03 16:56:25: Pending
    2017-06-03 16:56:26: [Pending]: next check in 1 seconds
    ...
    2017-06-03 16:56:35: [InProgress]: Processing Type: InstalledPackage
    ...
    2017-06-03 16:57:06: [Done]
    2017-06-03 16:57:07: [Success]: Succeeded
    2017-06-03 16:57:07: Installing npe03 version 3.9
    2017-06-03 16:57:07: Pending
    2017-06-03 16:57:08: [InProgress]: Processing Type: InstalledPackage
    ...
    2017-06-03 16:57:25: [Done]
    2017-06-03 16:57:26: [Success]: Succeeded
    2017-06-03 16:57:26: Installing npe4 version 3.5
    2017-06-03 16:57:26: Pending
    2017-06-03 16:57:27: [Pending]: next check in 1 seconds
    2017-06-03 16:57:29: [InProgress]: Processing Type: InstalledPackage
    ...
    2017-06-03 16:57:43: [Done]
    2017-06-03 16:57:44: [Success]: Succeeded
    2017-06-03 16:57:44: Installing npe5 version 3.5
    2017-06-03 16:57:44: Pending
    2017-06-03 16:57:45: [Pending]: next check in 1 seconds
    2017-06-03 16:57:47: [InProgress]: Processing Type: InstalledPackage
    ...
    2017-06-03 16:57:58: [Done]
    2017-06-03 16:57:59: [Success]: Succeeded
    2017-06-03 16:57:59: Installing npsp version 3.99
    2017-06-03 16:57:59: Pending
    2017-06-03 16:58:00: [Pending]: next check in 1 seconds
    2017-06-03 16:58:53: [InProgress]: Processing Type: InstalledPackage
    ...
    2017-06-03 17:01:53: [Done]
    2017-06-03 17:01:54: [Success]: Succeeded
    2017-06-03 17:01:54: Deploying unmanaged metadata from /NPSP-dev/unpackaged/post/first of https://github.com/SalesforceFoundation/NPSP/archive/dev.zip
    2017-06-03 17:01:58: Replacing namespace tokens with npsp__
    2017-06-03 17:01:58: Pending
    2017-06-03 17:01:59: [Pending]: next check in 1 seconds
    2017-06-03 17:02:01: [InProgress]: Processing Type: QuickAction
    2017-06-03 17:02:03: [Done]
    2017-06-03 17:02:04: [Success]: Succeeded

Automatic Cleaning of meta.xml files on Deploy
----------------------------------------------

In order to allow CumulusCI to fully manage the project's dependencies, the ``deploy`` task (and other tasks based on ``cumulusci.tasks.salesforce.Deploy`` or subclasses of it) will automatically remove the ``<packageVersion>`` element and its children from all meta.xml files in the deployed metadata.  This does not affect the files on the filesystem.

The reason for stripping ``<packageVersion>`` elements on deploy is that the target Salesforce org will automatically add them back using the installed version of the referenced namespace.  This allows CumulusCI to fully manage dependencies and avoids the need to rush a new commit of meta.xml files when a new underlying package version is available.

If the metadata being deployed references namespaced metadata that does not exist in the currently installed package, the deployment will still throw an error as expected.

The automatic cleaning of meta.xml files can be disabled using by setting the ``clean_meta_xml`` task option to ``False``.

Prior to the addition of this functionality, we often experienced unnecessary delays in our release cycle due to the need to create a new commit on ``main`` (and thus a feature branch, PR, code review, etc) just to update the meta.xml files.  CumulusCI's Github Dependency functionality already handles requiring a new production release so the only reason we needed to do this commit was the meta.xml files.  Automatically cleaning the meta.xml files on deploy eliminates the need for this commit.

One drawback of this approach is that there may be diffs in the meta.xml files that developers need to handle by either ignoring them or commiting them as part of their work in a feature branch.  The diffs come from a scenario of Package B which extends Package A.  When a new production release of Package A is published, the ``update_dependencies`` task for Package B will install the new version.  When metadata is then retrieved from the org, the meta.xml files will reference the new version while the repository's meta.xml files reference an older version.  The main difference between this situation and the previous situation without automatically cleaning the meta.xml is that avoiding the diffs in meta.xml files is a convenience for developers rather than a requirement for builds and releases.  Developers can also use the ``meta_xml_dependencies`` task to update the meta.xml files locally using the versions from CumulusCI's calculated project dependencies.

Using Tasks and Flows from a Different Project
----------------------------------------------

The dependency handling discussed above is used in a very specific context,
to install dependency packages or metadata bundles in the ``dependencies`` flow
which is a component of some other flows. It's also possible to use
arbitrary tasks and flows from another project. To do this, the other project
must be named in the ``sources`` section of cumulusci.yml:

.. code-block:: yaml

    sources:
      npsp:
        github: https://github.com/SalesforceFoundation/NPSP

This says that when tasks or flows are referenced using the `npsp` namespace,
CumulusCI should fetch the source from this GitHub repository. By default,
it will fetch the most recent release, or the default branch if there are no releases.
It's also possible to fetch a specific ``tag``:

.. code-block:: yaml

    sources:
      npsp:
        github: https://github.com/SalesforceFoundation/NPSP
        tag: rel/3.163

or a specific ``commit`` or ``branch``.

Now it's possible to run a flow from NPSP:

.. code-block:: console

    $ cci flow run npsp:install_prod

Or a task:

.. code-block:: console

    $ cci task run npsp:robot

Or even to create a new flow which uses a flow from NPSP:

.. code-block:: yaml

    flows:
      install_npsp:
        steps:
          1:
            flow: npsp:install_prod
          2:
            flow: dev_org

This flow will use NPSP's ``install_prod`` flow to install NPSP as a managed package,
and then run this project's own ``dev_org`` flow.

Source Tracking
===============

The ``list_changes`` and ``retrieve_changes`` tasks can be used to help find and retrieve metadata for components that have been changed in an org in Setup through clicks not code. This functionality relies on Salesforce's source tracking feature, so it is only available in scratch orgs.

Setting up the Capture Scratch Org
----------------------------------

When you are ready to start making changes in an org that you want to capture, start by creating a snapshot, which will effectively set the source tracking to treat all current changes as already handled.  This will allow the ``list_changes`` and ``retrieve_changes`` tasks to detect any new metadata but ignore any prior changes.

.. code-block:: console

    cci task run snapshot_changes --org dev

A number of the standard CumulusCI flows include the ``snapshot_changes`` as the final step. So if you have just set up a scratch org by running the ``dev_org``, ``dev_org_namespaced``, ``qa_org``, ``regression_org``, ``install_beta`` or ``install_prod`` flows, then you don't need to run ``snapshot_changes`` again.

To check to make sure the snapshot was created correctly, you should see no changes listed when you run the ``list_changes`` task:

.. code-block:: console

    cci task run list_changes --org dev

Listing Changes
---------------

Now, go make the changes in the org you want to capture as part of the dev config.
You can check what components have changed with the ``list_changes`` command:

.. code-block:: console

    cci task run list_changes --org dev

You can also include/exclude components from the list using the include/exclude options:

.. code-block:: console

    cci task run list_changes --org dev -o include "test.*,another_regex" -o exclude "something_to_exclude"

The ``include`` and ``exclude`` patterns will be matched against both the metadata type and name of the component.

You can also include all changed components of specific types:

    cci task run list_changes --org dev -o types "CustomObject,CustomField"

Retrieving Changes
------------------

When you are ready to capture the changes returned from ``list_changes``, run the ``retrieve_changes`` task::

.. code-block:: console

    cci task run retrieve_changes --org dev

It accepts the same ``include``, ``exclude``, and ``types`` options for filtering the list of changed components, in case you don't want to retrieve everything.

After the metadata has been retrieved, the snapshot will be updated so that the retrieved components will no longer be included in ``list_changes``. You can avoid this by setting the ``snapshot`` option to False.

By default changes are retrieved into the ``src`` directory when using metadata source format,
or the default sfdx package directory when using sfdx source format. You can retrieve into a different
location using the ``path`` option:

    cci task run retrieve_changes --org dev -o path unpackaged/config/qa

Creating custom Retrieve Tasks
------------------------------

If you will be retrieving changes into a directory repeatedly,
consider creating a custom task with the correct options
so that you don't need to specify them on the command line each time.

To do this, add YAML like this to your project's ``cumulusci.yml``:

.. code-block:: yaml

    tasks:
        retrieve_config_dev:
            description: Retrieves the current changes in the scratch org into unpackaged/config/dev
            class_path: cumulusci.tasks.salesforce.sourcetracking.RetrieveChanges
            options:
                path: unpackaged/config/dev
                namespace_tokenize: $project_config.project__package__namespace

(If you're capturing post-install metadata that will remain unpackaged, it is best to do so starting with a managed installation of your package. This makes it possible to convert references to the package namespace into CumulusCI's namespace token strings, so that the retrieved metadata can be deployed on top of either managed installations or unmanaged deployments of the package. To set up an org with the latest managed beta release, use the ``install_beta`` flow.)


Source Code Formats
===================

CumulusCI supports two different formats for storing the source code for a package:

1. The `metadata package format <https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/file_based_zip_file.htm>`_ used by the Metadata API, Force.com IDE, and Ant Migration Tool. This format is optimized for deploying directly to a packaging org without modification. CumulusCI always deploys this format using the Metadata API.
2. The `Salesforce DX source format <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_source_file_format.htm>`_. It is optimized for developer usability with tools such as the Salesforce CLI (sfdx) and Salesforce Extensions for VS Code. When deploying a DX-format package to a scratch org, CumulusCI will do so using the ``sfdx force:source:push`` command. For orgs that do not support source tracking, such as a Developer Edition packaging org, it will convert the package to metadata format and then deploy using the Metadata API.

By default, CumulusCI assumes your source code is in the metadata format.
Tell it to use DX format instead in cumulusci.yml:

.. code-block:: yaml

    project:
        source_format: sfdx

Converting a project to DX format
---------------------------------

Assuming you have existing metadata-format source code in the ``src`` directory,
follow these steps to convert your project to store DX format source code in the ``force-app`` directory:

1. Make sure sfdx-project.json specifies a path for the default package directory:

.. code-block:: yaml

    {
        "packageDirectories": [
            {
                "path": "force-app",
                "default": true
            }
        ],
        "sourceApiVersion": "46.0”
    }

2. Add ``source_format: sfdx`` to the project section of ``cumulusci.yml``.
3. Convert the source by running ``sfdx force:mdapi:convert -r src``
4. Remove the ``src`` directory.

Now when you set up a new scratch org (for example by running the dev_org flow),
the source should get pushed successfully from the ``force-app`` directory.

Caveats:

* It’s possible there may be some minor errors in the automatic conversion that need special attention in order to deploy successfully.
* See `this link <https://ntotten.com/2018/05/11/convert-metadata-to-source-format-while-maintain-git-history/>`_ for some tips on preserving git history while converting your source format.


Working with Errors
===================

Log Files
---------
CumulusCI creates a log file every time a cci command besides ``gist`` is run. Log files are stored under ``~/.cumulusci/logs``.

Viewing Stacktraces
-------------------
If you encounter an error and want more information on what went wrong, you can use ``cci error info`` to display the last *n* lines (30, by default) of the stacktrace (if present) from the last command you executed in CumulusCI.

You can include the option ``max_lines`` argument if you want to customize how much of the stacktrace you see.

Reporting Error Logs 
--------------------
Use the ``cci error gist`` command to send the log of your last ``cci`` command to a GitHub gist so you can submit it for support if needed.

For this feature to work you will need to ensure that your `github service is setup with the proper scopes <https://cumulusci.readthedocs.io/en/latest/tutorial.html#github-service>`_.

The gist command creates a gist comprised of:
    * The current version of ``cci``
    * The current python version
    * The path to the python executable
    * The ``sysname`` of the host (e.g. Darwin)
    * The machine name of the host (e.g. x86_64)
    * The most recent logfile (cci.log) that CumulusCI has created.

The URL for the gist is displayed on the terminal of the user as output, and a web browser will automatically open a tab to the gist.

Seeing Stack Traces Automatically
---------------------------------
If you would like to investigate bugs in CumulusCI when you find
them, you can set the config option `show_stacktraces` to `True`
in the `cli` section of `~/.cumulusci/cumulusci.yml` and stacktraces
will no longer be suppressed when they are thrown within CumulusCI.
Usage Errors (wrong command line arguments, missing files, etc.)
will not show you exception tracebacks because they are seldom
helpful in that case.

CumulusCI also has a `--debug` command line argument that may help you investigate bugs.
