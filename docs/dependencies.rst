=====================
Managing Dependencies
=====================

From the beginning, CumulusCI was built to automate the complexities of dependency management for extension package projects.  CumulusCI currently handles three main types of dependencies for projects:

* **Managed Packages**: Require a certain version of a managed package
* **Unmanaged Metadata**: Require the deployment of unmanaged metadata
* **Github Repository**: Dynamically include the dependencies of another CumulusCI configured project

The `update_dependencies` task handles deploying the dependencies to the target org and is included in all flows designed to deploy or install to an org.  The task can also be run individually with `cci task run update_dependencies`.

Managed Package Dependencies
============================

Managed package dependencies are rather simple.  You need the namespace and the version number you want to require::

    project:
        dependencies:
            - namespace: npe01
              version: 3.6

Automatic Install, Upgrade, or Uninstall/Install
------------------------------------------------

When the `update_dependencies` task runs, it first retrieves a list of all managed packages in the target org and creates a list of the installed packages and their version numbers.  With the example cumulusci.yml shown above, the following will happen depending on what if npe01 is currently installed:

* If npe01 is not installed, npe01 version 3.6 is installed
* If the org already has npe01 version 3.6 installed then nothing will be done
* If the org has an older version installed, it will be upgraded to version 3.6
* If the org has a newer version or a beta version installed, it will be uninstalled and then version 3.6 will be installed

Hierachical Dependencies
------------------------

Managed Package dependencies can handle a hierarchy of dependencies between packages.  An example use case is Salesforce.org's Nonprofit Success Pack, an extension of 5 other managed packages and one of those packages (npo02) is an extension of another (npe01).  This is expressed in cumulusci.yml as::

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

In the example above, the project requires npo02 version 3.8 which requires npe01 version 3.6.  By specifying the dependency hierarchy, the `update_dependencies` task is able to handle an edge case:  If the target org currently has npe01 version 3.7, npe01 needs to be uninstalled to downgrade to 3.6.  However, npo02 requires npe01 so uninstalling npe01 requires also uninstalling npo02.  In this scenario npe03, npe4, and npe5 do not have to be uninstalled to uninstall npe01.


Unmanaged Metadata Dependencies
===============================

You can specify unmanaged metadata to be deployed by specifying a `zip_url` and optionally `subfolder`, `namespace_inject`, `namespace_strip`, and `unmanaged`::

    project:
        dependencies:
            - zip_url: https://SOME_HOST/metadata.zip

When `update_dependencies` runs, it will download the zip file and deploy it via the Metadata API's Deploy method.  The zip file must contain valid metadata for use with a deploy including a package.xml file in the root.

Specifying a Subfolder of the Zip File
--------------------------------------

You can use the `subfolder` option to specify a subfolder of the zip file you want to use for the deployment.  This is particularly handy when referring to metadata stored in a Github repository::

    project:
        dependencies:
            - zip_url: https://github.com/SalesforceFoundation/CumulusReports/archive/master.zip
              subfolder: CumulusReports-master/record_types

When `update_dependencies` runs, it will still download the zip from `zip_url` but it will then build a new zip containing only the content of `subfolder` starting inside `subfolder` as the zip's root.

Injecting Namespace Prefixes
----------------------------

CumulusCI has support for tokenizing references to the namespace prefix in code.  When tokenized, all occurrences of the namespace prefix (i.e. npsp__), will be replaced with `%%%NAMESPACE%%%` inside of files and `___NAMESPACE___` in file names.  If the metadata you are deploying has been tokenized, you can use the `namespace_inject` and `unmanaged` options to inject the namespace::

    project:
        dependencies:
            - zip_url: https://github.com/SalesforceFoundation/HEDAP/archive/master.zip
              subfolder: HEDAP-master/dev_config/src/admin_config
              namespace_inject: hed

In the above example, the metadata in the zip contains the string tokens `%%%NAMESPACE%%%` and `___NAMESPACE___` which will be replaced with `hed__` before the metadata is deployed.

If you want to deploy tokenized metadata without any namespace references, you have to specify both `namespace_inject` and `unmanaged`::

    project:
        dependencies:
            - zip_url: https://github.com/SalesforceFoundation/HEDAP/archive/master.zip
              subfolder: HEDAP-master/dev_config/src/admin_config
              namespace_inject: hed
              unmanaged: True

In the above example, the namespace tokens would be replaced with an empty string instead of the namespace effectively stripping the tokens from the files and filenames.

Stripping Namespace Prefixes
----------------------------

If the metadata in the zip you want to deploy has references to a namespace prefix and you want to remove them, use the `namespace_strip` option::

    project:
        dependencies:
            - zip_url: https://github.com/SalesforceFoundation/CumulusReports/archive/master.zip
              subfolder: CumulusReports-master/src
              namespace_strip: npsp

When `update_dependencies` runs, the zip will be retrieved and the string `npsp__` will be stripped from all files and filenames in the zip before deployment.  This is most useful if trying to set up an unmanaged development environment for an extension package which normally uses managed dependencies.  The example above takes the NPSP Reports & Dashboards project's unmanaged metadata and strips the references to `npsp__` so you could deploy it against an unmanaged version of NPSP.


Github Repository Dependencies
==============================

Github Repository dependencies create a dynamic dependency between the current project and another project on Github that uses CumulusCI to manage its dependencies::

    project:
        dependencies:
            - github: https://github.com/SalesforceFoundation/HEDAP

When `update_dependencies` runs, the following is doing against the referenced repository:

* Look for cumulusci.yml and parse if found
* Determine if the project has subfolders under unpackaged/pre.  If found, deploys them first.
* Determine if the project specifies any dependencies in cumulusci.yml.  If found, deploys them next in the queue.
* Determine if the project has a namespace configured in cumulusci.yml. If found, treats the project as a managed package unless the unmanaged option is also True.
* If the project has a namespace and is not set for unmanaged, use the Github API to get the latest release and install it.
* If the project is an unmanaged dependency, the src directory is deployed.
* Determine if the project has subfolders under unpackaged/post.  If found, deploys them next.  Namespace tokens are replaced with namespace__ or an empty string depending on if the dependency is considered managed or unmanaged.

Referencing Unmanaged Projects
------------------------------

If the referenced repository does not have a namespace configured or if the dependency specifies the `unmanaged` option as true (see example below), the repository is treated as an unmanaged repository::

    project:
        dependencies:
            - github: https://github.com/SalesforceFoundation/HEDAP
              unmanaged: True

In the above example, the HEDAP repository is configured for a namespace but the dependency specifies `unmanaged: True` so the dependency would deploy unmanaged HEDAP and its dependencies. 

Case Study: SalesforceFoundation/Cumulus
----------------------------------------

The following will create a dependency against the open source repository for Salesforce.org's Nonprofit Success Pack::

    project:
        dependencies:
            - github: https://github.com/SalesforceFoundation/Cumulus

With this one simple line in the project's dependencies, the following dependencies are included:

* unpackaged/pre/account_record_types from SalesforceFoundation/Cumulus
* unpackaged/pre/opportunity_record_types from SalesforceFoundation/Cumulus
* npe01 3.6
* npo02 3.8
* npe03 3.8
* npe4 3.5
* npe5 3.5
* npsp 3.99
* unpackaged/post/first from SalesforceFoundation/Cumulus with namespace tokens replaced with `npsp__`

This happens because of the following from the cumulusci.yml in the the Cumulus (npsp) repository::

    dependencies:
        # npo02 (includes npe01)
        - github: https://github.com/SalesforceFoundation/Households
        # npe03
        - github: https://github.com/SalesforceFoundation/Recurring_Donations
        # npe4
        - github: https://github.com/SalesforceFoundation/Relationships
        # npe5
        - github: https://github.com/SalesforceFoundation/Affiliations

Note that npo02 includes npe01.  This is because the dependencies for SaleforceFoundation/Households (npo02) contains the following::

    dependencies:
        # npe01
        - github: https://github.com/SalesforceFoundation/Contacts_and_Organizations

As a result, npe01 is included because the repository for npo02 refers to npe01's repository as a dependency and Cumulus refers to npo02's repository as a dependency.

You can see how complex a single repository dependency can be with the following command output from the single depedency reference to the Cumulus repository::

    $ cci task run update_dependencies
    2017-06-03 16:55:29: Getting scratch org info from Salesforce DX
    2017-06-03 16:55:31: Beginning task: UpdateDependencies
    ...
    2017-06-03 16:55:31: Retrieving list of packages from target org
    2017-06-03 16:55:31: Pending
    2017-06-03 16:55:33: [Done]
    2017-06-03 16:55:34: Dependencies:
    2017-06-03 16:55:34: Processing dependencies from Github repo https://github.com/SalesforceFoundation/Cumulus
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
    2017-06-03 16:55:43: Deploying unmanaged metadata from /Cumulus-dev/unpackaged/pre/account_record_types of https://github.com/SalesforceFoundation/Cumulus/archive/dev.zip
    2017-06-03 16:55:48: Pending
    2017-06-03 16:55:49: [InProgress]: Processing Type: CustomObject
    2017-06-03 16:55:50: [Done]
    2017-06-03 16:55:51: [Success]: Succeeded
    2017-06-03 16:55:51: Deploying unmanaged metadata from /Cumulus-dev/unpackaged/pre/opportunity_record_types of https://github.com/SalesforceFoundation/Cumulus/archive/dev.zip
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
    2017-06-03 17:01:54: Deploying unmanaged metadata from /Cumulus-dev/unpackaged/post/first of https://github.com/SalesforceFoundation/Cumulus/archive/dev.zip
    2017-06-03 17:01:58: Replacing namespace tokens with npsp__
    2017-06-03 17:01:58: Pending
    2017-06-03 17:01:59: [Pending]: next check in 1 seconds
    2017-06-03 17:02:01: [InProgress]: Processing Type: QuickAction
    2017-06-03 17:02:03: [Done]
    2017-06-03 17:02:04: [Success]: Succeeded

