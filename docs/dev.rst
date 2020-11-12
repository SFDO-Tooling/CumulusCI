Develop a Project
=================
This is a general overview of the aspects involved
with developing a Salesforce project with CumulusCI.



Set Up a Dev Org
----------------
You first need an org that you can develop on.
The ``dev_org`` flow is suitable for doing just this.
The flow takes care of moving all Metadata (managed and unmanaged)
into the org and configuring it so that it's ready for development.

.. note::

    For a full list of steps for the ``dev_org`` flow, use: ``cci flow info dev_org``

.. code-block:: console

    $ cci flow run dev_org

This will run the ``dev_org`` flow against the project's `default org <TODO>`.

You can explicitly list the org you want to use with the ``--org`` option.

.. code-block:: console

    $ cci flow run dev_org --org dev

The above runs the ``dev_org`` flow against the org currently defined as ``dev`` in CumulusCI.

You can now open up your new ``dev`` org to begin development.

.. code-block:: console

    $ cci org browser dev



Setting the Capture State
^^^^^^^^^^^^^^^^^^^^^^^^^
When you are ready to start making changes that you want to capture in an org, start by creating a snapshot.
This tells the Salesforce CLI source tracking to set the org's current state as a baseline for changes to be made against.

.. note::

    If you have just set up a scratch org by running the ``dev_org``, ``dev_org_namespaced``,
    ``qa_org``, ``regression_org``, ``install_beta`` or ``install_prod`` flows, you do not need to run ``snapshot_changes``.
    These flows all run ``snapshot_changes`` as their last step.

.. code-block:: console

    $ cci task run snapshot_changes --org dev

This will allow the ``list_changes`` and ``retrieve_changes`` tasks to detect any new metadata but ignore any prior changes.
A number of the standard CumulusCI flows, include the ``snapshot_changes`` as the final step.

Check that the snapshot was created successfully:

.. code-block:: console

    $ cci task run list_changes --org dev

This should list no changes to the org.



List Changes
------------
You can check what components you have changed in a target org with the ``list_changes`` command:

.. code-block:: console

    $ cci task run list_changes --org dev

.. note::
    
    This functionality relies on Salesforce's source tracking feature, so it is only available in scratch orgs.

You can also include/exclude components from the list using the include/exclude options:

.. code-block:: console

    $ cci task run list_changes --org dev --include "test.*,another_regex" --exclude "something_to_exclude"

The ``include`` and ``exclude`` patterns are matched against both the metadata type and name of the component.

You can also include all changed components of specific types:

.. code-block:: console

    $ cci task run list_changes --org dev --types "CustomObject,CustomField"



Retrieve Changes
----------------
The ``retrieve_changes`` task supports both ``sfdx`` and ``mdapi`` formatted source code. 
It also utilizes the `SourceMember <TODO>`_ sObject to detect what has changed in an org,
but allows you to be more selective regarding which components to retrieve when compared to the ``dx_pull`` task. 
Manual tracking of component versions also allows for the possibility of retrieving some changes into one directory,
and then running the task again to retrieve other changes into a different directory.
 
.. note::

    CumulusCI has multiple tasks for retrieving Metadata from an org environment.
    For a comprehensive list, see the `retrieve changes`_ section of the cheat sheet.

When you are ready to capture changes in an org, run the ``retrieve_changes`` task:

.. code-block:: console

    $ cci task run retrieve_changes --org dev

The task accepts ``include``, ``exclude``, and ``types`` options for filtering the
list of changed components, for scenarios where you don't want to retrieve all changed components.

After the metadata has been retrieved, the org snapshot will be updated so 
that the retrieved components will no longer be included in ``list_changes``.
You can avoid this by setting the ``snapshot`` option to False.

By default, changes are retrieved into the ``src`` directory when using Metadata source format,
or the default ``sfdx`` package directory (``force-app``) when using ``sfdx`` source format.
You can retrieve into a different location using the ``path`` option:

.. code-block:: console

    $ cci task run retrieve_changes --org dev --path unpackaged/config/qa



Push Changes
------------
Developers rarely edit code directly in an org environment, but instead use an editor or IDE like VSCode or IntelliJ.
After code (or other Metadata) in an editor you will need to push these changes from your project's local repository to the target org.

If your project uses the ``sfdx`` source format then you can use the ``dx_push`` task:

.. code-block:: console

    $ cci task run dx_push

If you project uses the Metadata source format you can use the ``deploy`` task:

.. code-block:: console

    $ cci task run deploy 

.. note::
   
   The ``deploy`` task has *many* options for handling a number of different scenarios.
   For a complete list see the reference documentation for the `deploy task <TODO>`_.



Run Apex Tests
--------------
CumulusCI allows you to easily execute Apex tests in an org:

.. code-block:: console

    $ cci task run run_tests --org <org_name>

.. note::

    This task has many options for running tests in a variety of ways.
    For more information on options and examples see the reference documentation for `run_tests <TODO>`_.



Set Up a QA Org
---------------
There is flow named ``qa_org`` that is specific to setting up
org environments that allow quality engineers to test features quickly, and easily.
The ``qa_org`` runs the specialized ``config_qa`` task after deploying the projects
(unmanaged) Metadata to the org.

.. code-block:: console

    $ cci flow run qa_org --org qa

This runs the ``qa_org`` flow against the ``qa`` org.


Create QA Configurations
^^^^^^^^^^^^^^^^^^^^^^^^
Out-of-the-box, the ``config_dev`` and ``config_qa`` flows are the same.
We've found that many teams have a requirement for additional configurations to be deployed when
performing QA but not when developing a new feature.

For example, at Salesforce.org our teams often modify the ``config_qa`` flow to deploy configurations that pertain to large
optional features in a package. These configurations are subsequently tested by the product's robot test suites.

To capture your own QA configurations you can spin up a new org with ``cci flow run qa_org``, make the necessary changes, and run the following:

.. code-block::

    $ cci task run retrieve_qa_config

This task defaults to capturing this Metadata under ``unpackaged/config/qa``.
You can store the configuration Metadata in a different location by using the ``--path`` option.

You can now delete the org with:

.. code-block:: console

    $ cci org remove qa

Then re-create it with:

.. code-block:: console

    $ cci flow run qa_org --org qa

Then run the ``deploy_qa_config`` to deploy the previously captured configurations to the org:

.. code-block:: console

    $ cci task run deploy_qa_config --org qa

If you would like the ``qa_org`` flow to always run this task for you then you can add
the following in your project's ``cumulusci.yml`` file under the ``flows`` section:

.. code-block:: yaml

    qa_config:
        steps:
            3:
                task: deploy_qa_config

This tells CumulusCI whenever it runs the flow ``qa_config`` (which is included in the ``qa_org`` flow)
to execute the ``deploy_qa_config`` task as the third (last) step in the flow.



Manage Dependencies
-------------------
Since the beginning, CumulusCI has been built to automate the complexities of dependency management for extension package projects.
CumulusCI currently handles three main types of dependencies for projects:

* **Managed Packages**: Require a certain version of a managed package
* **Unmanaged Metadata**: Require the deployment of unmanaged metadata
* **Github Repository**: Dynamically include the dependencies of another CumulusCI configured project

The ``update_dependencies`` task handles deploying dependencies to a target org and is
included in all flows designed to deploy or install to an org.
The task can also be run explicitly with ``cci task run update_dependencies``.



Managed Package Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Managed package dependencies are rather simple.
Under the ``project``-->``dependencies`` section of your project's ``cumulusci.yml`` file you
need the namespace of the target package and the version number you want to require:

.. code-block:: yaml

    project:
        dependencies:
            - namespace: npe01
              version: 3.6



Automatic Install, Upgrade, or Uninstall/Install
************************************************************
When the ``update_dependencies`` task runs, it first retrieves a list of all managed packages in the target
org and creates a list of the installed packages and their version numbers.
With the example ``cumulusci.yml`` shown above, the following will happen, depending on whether the package with namespace ``npe01`` is currently installed:

* If ``npe01`` is not installed, ``npe01`` version 3.6 is installed
* If the org already has ``npe01`` version 3.6 installed, nothing will be done
* If the org has an older version installed, it will be upgraded to version 3.6
* If the org has a newer version or a beta version installed, it will be uninstalled and then version 3.6 will be installed



Hierarchical Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^
Managed Package dependencies can handle a hierarchy of dependencies between packages.
An example use case is Salesforce.org's Nonprofit Success Pack, an extension of 5 other
managed packages and one of those packages (npo02) is an extension of another (npe01).
This is expressed in ``cumulusci.yml`` as:

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

In the example above, the project requires npo02 version 3.8, which requires npe01 version 3.6.
By specifying the dependency hierarchy, the ``update_dependencies`` task is capable of uninstalling and upgrading packages intelligently.

Consider the following scenario:  If the target org currently has npe01 version 3.7, npe01 needs to be uninstalled to downgrade to 3.6.
However, npo02 requires npe01, so uninstalling npe01 requires also uninstalling npo02.  In this scenario npe03, npe4, and npe5 do not have to be uninstalled to uninstall npe01.


Unmanaged Metadata Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
You can specify unmanaged metadata to be deployed by specifying a ``zip_url`` and optionally ``subfolder``, ``namespace_inject``, ``namespace_strip``, and ``unmanaged``:

.. code-block:: yaml

    project:
        dependencies:
            - zip_url: https://SOME_HOST/metadata.zip

When ``update_dependencies`` runs, it will download the zip file and deploy it via the Metadata API's Deploy method.
The zip file must contain valid metadata for use with a deploy including a package.xml file in the root.

Specifying a Subfolder of the Zip File
******************************************

You can use the ``subfolder`` option to specify a subfolder of the zip file you want to use for the deployment.
This is particularly handy when referring to metadata stored in a Github repository:

.. code-block:: yaml

    project:
        dependencies:
            - zip_url: https://github.com/SalesforceFoundation/CumulusReports/archive/master.zip
              subfolder: CumulusReports-master/record_types

When ``update_dependencies`` runs, it will still download the zip from ``zip_url``
but it will then build a new zip containing only the content of ``subfolder`` starting inside ``subfolder`` as the zip's root.



Injecting Namespace Prefixes
************************************
CumulusCI has support for tokenizing references to the namespace prefix in code.
When tokenized, all occurrences of the namespace prefix (i.e. ``npsp__``), will be replaced with ``%%%NAMESPACE%%%`` inside of files and ``___NAMESPACE___`` in file names.
If the metadata you are deploying has been tokenized, you can use the ``namespace_inject`` and ``unmanaged`` options to inject the namespace:

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
************************************
If the metadata in the zip you want to deploy has references to a namespace prefix and you want to remove them, use the ``namespace_strip`` option:

.. code-block:: yaml

    project:
        dependencies:
            - zip_url: https://github.com/SalesforceFoundation/CumulusReports/archive/master.zip
              subfolder: CumulusReports-master/src
              namespace_strip: npsp

When ``update_dependencies`` runs, the zip will be retrieved and the string ``npsp__`` will be stripped from all files and filenames in the zip before deployment.  This is most useful if trying to set up an unmanaged development environment for an extension package which normally uses managed dependencies.  The example above takes the NPSP Reports & Dashboards project's unmanaged metadata and strips the references to ``npsp__`` so you could deploy it against an unmanaged version of NPSP.



Github Repository Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Github Repository dependencies create a dynamic dependency between the current project and
another project on Github that uses CumulusCI to manage its dependencies:

.. code-block:: yaml

    project:
        dependencies:
            - github: https://github.com/SalesforceFoundation/EDA

When ``update_dependencies`` runs, the following happens against the referenced repository:

* Look for ``cumulusci.yml`` and parse if found
* Determine if the project has subfolders under unpackaged/pre.  If found, deploys them first.
* Determine if the project specifies any dependencies in ``cumulusci.yml``.  If found, deploys them next in the queue.
* Determine if the project has a namespace configured in ``cumulusci.yml``. If found, treats the project as a managed package unless the unmanaged option is also True.
* If the project has a namespace and is not set for unmanaged, use the Github API to get the latest release and install it.
* If the project is an unmanaged dependency, the ``src`` or ``force-app`` directory is deployed.
* Determine if the project has subfolders under unpackaged/post.  If found, deploys them next.  Namespace tokens are replaced with ``namespace__`` or an empty string depending on if the dependency is considered managed or unmanaged.



Referencing Unmanaged Projects
************************************
If the referenced repository does not have a namespace configured or if the dependency
 specifies the ``unmanaged`` option as true (see example below), the repository is treated as an unmanaged repository:

.. code-block:: yaml

    project:
        dependencies:
            - github: https://github.com/SalesforceFoundation/EDA
              unmanaged: True

In the above example, the EDA repository is configured for a namespace but the dependency
 specifies ``unmanaged: True`` so the dependency would deploy unmanaged EDA and its dependencies.



Referencing a Specific Tag
*********************************
If you want to reference a version other than HEAD and the latest production release,
you can use the ``tag`` option to specify a particular tag from the target repository.
This is most useful for testing against beta versions of underlying packages or 
recreating specific org environments for debugging:

.. code-block:: yaml

    project:
        dependencies:
            - github: https://github.com/SalesforceFoundation/EDA
              tag: beta/1.47-Beta_2

In the above example, the EDA repository's tag ``beta/1.47-Beta_2`` will be used instead 
of the latest production release of EDA (1.46 for this example).  This allows a build
environment to use features in the next production release of EDA which are already
merged but not yet included in a production release.



Skipping ``unpackaged/*`` in Reference Repositories
********************************************************
If the repository you are referring to has dependency metadata under unpackaged/pre or unpackaged/post
and you want to skip deploying that metadata with the dependency, use the **skip** option:

.. code-block:: yaml

    project:
        dependencies:
            - github: https://github.com/SalesforceFoundation/EDA
              skip: unpackaged/post/course_connection_record_types



Automatic Cleaning of ``meta.xml`` Files on Deploy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In order to allow CumulusCI to fully manage the project's dependencies, 
the ``deploy`` task (and other tasks based on ``cumulusci.tasks.salesforce.Deploy`` 
or subclasses of it) will automatically remove the ``<packageVersion>`` element 
and its children from all ``meta.xml`` files in the deployed metadata.
This does not affect the files on the filesystem.

The reason for stripping ``<packageVersion>`` elements on deploy is that the target 
Salesforce org will automatically add them back using the installed version of the referenced namespace.
This allows CumulusCI to fully manage dependencies and avoids the need to rush a 
new commit of ``meta.xml`` files when a new underlying package version is available.

If the metadata being deployed references namespaced metadata that does not exist in 
the currently installed package, the deployment will still throw an error as expected.

The automatic cleaning of ``meta.xml`` files can be disabled using by setting the ``clean_meta_xml`` task option to ``False``.

Prior to the addition of this functionality, we often experienced unnecessary delays in
our release cycle due to the need to create a new commit on ``main`` (and thus a feature
branch, PR, code review, etc) just to update the ``meta.xml`` files.
CumulusCI's Github Dependency functionality already handles requiring a new production 
release so the only reason we needed to do this commit was the ``meta.xml`` files.
Automatically cleaning the meta.xml files on deploy eliminates the need for this commit.

One drawback of this approach is that there may be diffs in the ``meta.xml`` files that
developers need to handle by either ignoring them or committing them as part of their work in a feature branch.
The diffs come from a scenario of Package B which extends Package A.
When a new production release of Package A is published, the ``update_dependencies`` task 
for Package B will install the new version. When metadata is then retrieved from the org, the 
``meta.xml`` files will reference the new version while the repository's ``meta.xml`` files reference an older version.
The main difference between this situation and the previous situation without automatically 
cleaning the meta.xml is that avoiding the diffs in meta.xml files is a convenience for
developers rather than a requirement for builds and releases. Developers can also use the 
``meta_xml_dependencies`` task to update the meta.xml files locally using the versions from
CumulusCI's calculated project dependencies.



Using Tasks and Flows from a Different Project
----------------------------------------------
The dependency handling discussed above is used in a very specific context:
to install dependency packages or metadata bundles in the ``dependencies`` flow
which is a component of some other flows. 

Common use cases for using tasks and flows from another CumulusCI project include:

* Setting up a dependency when you want to include configuration, rather than just installing the package.
* Running robot tests that are defined in a dependency.

For information on configuring cross-project tasks and flows see `configuring cross-project tasks and flows <TODO>`_.
