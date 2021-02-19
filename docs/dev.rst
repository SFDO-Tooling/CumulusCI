Develop a Project
=================

A general overview on how to develop a Salesforce project with CumulusCI.



Set Up a Dev Org
----------------

The ``dev_org`` flow creates an org to develop on by moving all metadata (managed and unmanaged) into the org, and configuring it to be ready for development.

.. note:: Run ``cci flow info dev_org`` for a full list of the ``dev_org`` flow steps.

To run the ``dev_org`` flow against the project's `default org<TODO>`_:

.. code-block:: console

    $ cci flow run dev_org

To run the ``dev_org`` flow against a specific org, use the ``--org`` option:

    Example: Run the ``dev_org`` flow against the org currently defined as ``dev`` in CumulusCI.

.. code-block:: console

    $ cci flow run dev_org --org dev

..

    Open the new ``dev`` org to begin development.

.. code-block:: console

    $ cci org browser dev



List Changes
------------

To see what components have changed in a target org:

.. code-block:: console

    $ cci task run list_changes --org dev

.. note::
    
    This functionality relies on Salesforce's source tracking feature, which is currently available only in Scratch Orgs, Developer Sandboxes, and Developer Pro Sandboxes.

For more information, see `List and Retrieve Options`_.



Retrieve Changes
----------------

The ``retrieve_changes`` task supports both Salesforce DX- and Metadata API-format source code. It utilizes the `SourceMember <https://developer.salesforce.com/docs/atlas.en-us.api_tooling.meta/api_tooling/tooling_api_objects_sourcemember.htm>`_
``sObject`` to detect what has changed in an org, and also gives you discretion regarding which components are retrieved when compared to the ``dx_pull`` task.

Manual tracking of component versions also offers the possibility of retrieving changes into one directory, and then running the task again to retrieve other changes into a different directory.
 
To retrieve all changes in an org:

.. code-block:: console

    $ cci task run retrieve_changes --org dev

For more information, see `List and Retrieve Options`_.



List and Retrieve Options 
-------------------------

When developing in an org, the changes you're most interested in are sometimes mixed with other changes that aren't relevant to what you're doing.

    Example: Changing schema like Custom Objects and Custom Fields often results in changes to Page Layouts and Profiles that you don't wish to review or retrieve.

It's a common workflow in CumulusCI to use the ``list_changes`` task, combined with the options featured in this subsection, to narrow the scope of changes in the org to the exact elements you desire to retrieve in your project. When the correct set of metadata is listed, run the ``retrieve_changes`` task to bring those changes into the repository.



``--include`` & ``--exclude``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When retrieving metadata from an org, CumulusCI represents each component name as the combination of its type (such as a ``Profile``, ``CustomObject``, or ``ApexClass``) and its API name: ``MemberType: MemberName``. 

    Example: An ``ApexClass`` named ``MyTestClass`` would be represented as ``ApexClass: MyTestClass``.

The ``--include`` and ``--exclude`` options lets you pass multiple `regular expressions <https://en.wikipedia.org/wiki/Regular_expression>`_ to match against the names of changed components. This metadata is either included or excluded depending on which option the regular expression is passed. Multiple regular expressions can be passed in a comma-separated list.

    Example: List all modified metadata that ends in "Test" and "Data" in the default org.

.. code-block:: console

    $ cci task run list_changes --include "Test$,Data$"

..

    Since the metadata string that CumulusCI processes also includes the ``MemberType``, use exclusions and inclusions that filter whole types of metadata.
    
        Example: Exclude ``Profile`` type.

.. code-block:: console

    $ cci task run list_changes --exclude "^Profile: "


``--types``
^^^^^^^^^^^

To list or retrieve changed metadata of the same type, use the ``--types`` option along with the `SourceMember.MemberType <https://developer.salesforce.com/docs/atlas.en-us.api_tooling.meta/api_tooling/tooling_api_objects_sourcemember.htm>`_ metadata to retrieve.

    Example: Retrieve all changed ``ApexClasses`` and ``ApexComponents`` in the default org.

.. code-block:: console

    $ cci task run retrieve_changes --types ApexClass,ApexComponent


``--path``
^^^^^^^^^^

.. important:: This option only works with the ``retrieve_changes`` task.

By default, changes are retrieved into the ``src`` directory when using Metadata API source format, or the default  package directory (``force-app``) when using Salesforce DX source format.

To retrieve metadata into a different location using the ``--path`` option:

.. code-block:: console

    $ cci task run retrieve_changes --org dev --path your/unique/path



Push Changes
------------

Developers often use an editor or IDE like Visual Studio Code to modify code and metadata stored in the repository. After making changes in an editor, push these changes from your project's local repository to the target org.

If your project uses the Salesforce DX source format, use the ``dx_push`` task.

.. code-block:: console

    $ cci task run dx_push

If your project uses the Metadata API source format, use the ``deploy`` task:

.. code-block:: console

    $ cci task run deploy 

The ``deploy`` task has *many* options for handling a number of different scenarios. For a comprehensive list of options, see `deploy tasks <TODO>`_.



Run Apex Tests
--------------

CumulusCI executes Apex tests in an org and can optionally report on test outcomes and code coverage. CumulusCI can also retry failed tests automatically.

.. code-block:: console

    $ cci task run run_tests --org <org_name>

The ``run_tests`` task has *many* options for running tests. For a comprehensive list of options and examples, see `run_tests <TODO>`_.



Set Up a QA Org
---------------

The ``qa_org`` flow sets up org environments where quality engineers test features quickly and easily. ``qa_org`` runs the specialized ``config_qa`` flow after deploying the project's (unmanaged) metadata to the org.

    Example: Run the ``qa_org`` flow against the ``qa`` org.

.. code-block:: console

    $ cci flow run qa_org --org qa


Create QA Configurations
^^^^^^^^^^^^^^^^^^^^^^^^

For the most part ``config_dev`` and ``config_qa`` flows are the same. Many teams have a requirement for additional configurations to be deployed when performing QA, but not when developing a new feature.

    Example: Salesforce.org teams often modify the ``config_qa`` flow to deploy configurations that pertain to large optional features in a package. These configurations are subsequently tested by the product's Robot Framework test suites.

To retrieve your own QA configurations, spin up a new org...

.. code-block::

    $ cci flow run qa_org

Make the necessary changes, and run:

.. code-block::

    $ cci task run retrieve_qa_config

This task defaults to retrieving this metadata under ``unpackaged/config/qa``.

.. note:: The configuration metadata can also be stored in a different location by using the ``--path`` option.

..

To delete the org...

.. code-block:: console

    $ cci org remove qa

Then re-create it...

.. code-block:: console

    $ cci flow run qa_org --org qa

Then run the ``deploy_qa_config`` to deploy the previously retrieved configurations to the org.

.. code-block:: console

    $ cci task run deploy_qa_config --org qa

To require that the ``qa_org`` flow always runs this task, add a ``deploy_qa_config`` task step under the ``flows__qa_config`` section of the ``cumulusci.yml`` file.

.. code-block:: yaml

    qa_config:
        steps:
            3:
                task: deploy_qa_config

So now ``qa_config`` (which is included in the ``qa_org`` flow) executes the ``deploy_qa_config`` task as the third step in the flow.



Manage Dependencies
-------------------

CumulusCI is built to automate the complexities of dependency management for projects that extend and implement managed packages. CumulusCI currently handles these main types of dependencies for projects.

* **GitHub Repository**: Dynamically resolve a product release, and its own dependencies, from a CumulusCI project on GitHub
* **Managed Packages**: Require a certain version of a managed package
* **Unmanaged Metadata**: Require the deployment of unmanaged metadata

The ``update_dependencies`` task handles deploying dependencies to a target org, and is included in all flows designed to deploy or install to an org. 

To run the ``update_dependencies`` task: 

.. code-block:: console

    $ cci task run update_dependencies

    

GitHub Repository Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

GitHub repository dependencies create a dynamic dependency between the current project and another CumulusCI project on GitHub.

    Example: Salesforce EDA

.. code-block:: yaml
 
    project:
        dependencies:
            - github: https://github.com/SalesforceFoundation/EDA

When ``update_dependencies`` runs, these steps are taken against the referenced repository.

* Look for the ``cumulusci.yml`` file and parse if found.
* Determine if the project has subfolders under ``unpackaged/pre``.  If found, deploy them first.
* Determine if the project specifies any dependencies in the ``cumulusci.yml`` file.  If found, recursively resolve those dependencies and any dependencies belonging to them.
* Determine whether to install the project as as a managed package or unmanaged metadata:
    * If the project has a namespace configured in the ``cumulusci.yml`` file, treat the project as a managed package unless the unmanaged option is ``True``.
    * If the project has a namespace and is *not* configured as unmanaged, use the GitHub API to locate the latest managed release of the project and install it.
* If the project is an unmanaged dependency, the ``src`` or ``force-app`` directory is deployed.
* Determine if the project has subfolders under ``unpackaged/post``. If found, deploy them next. Namespace tokens are replaced with ``namespace__`` if the project is being installed as a managed package, or an empty string otherwise.



Reference Unmanaged Projects
****************************

If the referenced repository does not have a namespace configured, or if the dependency specifies the ``unmanaged`` option as ``True``, the repository is treated as unmanaged.

    Example: Salesforce EDA

.. code-block:: yaml

    project:
        dependencies:
            - github: https://github.com/SalesforceFoundation/EDA
              unmanaged: True

..

    The EDA repository is configured for a namespace, but the dependency  specifies ``unmanaged: True``, so EDA and its dependencies deploy as unmanaged metadata.



Reference a Specific Tag
************************

To reference a specific version of the product other than the most recent commit on the main branch (for unmanaged projects) or the most recent production release (for managed packages), use the ``tag`` option to specify a tag from the target repository. This option is most useful for testing against beta versions of underlying packages, or recreating specific org environments for debugging.

    Example: Salesforce EDA

.. code-block:: yaml

    project:
        dependencies:
            - github: https://github.com/SalesforceFoundation/EDA
              tag: beta/1.47-Beta_2

..

    The EDA repository's tag, ``beta/1.47-Beta_2``, is used instead of the latest production release of EDA (1.46, for this example). This tag lets a build environment use features in the next production release of EDA that are already merged but not yet included in a production release.



Skip ``unpackaged/*`` in Reference Repositories
***********************************************

If the referenced repository has dependency metadata under ``unpackaged/pre`` or ``unpackaged/post``, use the ``skip`` option to skip deploying that metadata with the dependency.

    Example: Salesforce EDA

.. code-block:: yaml

    project:
        dependencies:
            - github: https://github.com/SalesforceFoundation/EDA
              skip: unpackaged/post/course_connection_record_types



Managed Package Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Managed package dependencies are rather simple. Under the ``project__dependencies`` section of the ``cumulusci.yml`` file, specify the namespace of the target package, and the required version number.

    Example: ``npe01 version 3.6``

.. code-block:: yaml

    project:
        dependencies:
            - namespace: npe01
              version: 3.6



Automatic Install, Upgrade, or Uninstall/Install
************************************************

When the ``update_dependencies`` task runs, it retrieves a list of all managed packages in the target org, and creates a list of the installed packages and their version numbers.

    Example: ``npe01 version 3.6``
    
.. code-block:: yaml

    project:
        dependencies:
            - namespace: npe01
              version: 3.6
    
..    
    
    Depending on whether or not the package with namespace ``npe01`` is installed, the ``update_dependencies`` task runs these steps. 

    * If ``npe01`` is not installed, ``npe01 version 3.6`` is installed.
    * If the org already has ``npe01 version 3.6`` installed, no changes take place.
    * If the org has an older version installed, it's upgraded to ``version 3.6``.
    * If the org has a newer version or a beta version installed, it's uninstalled and ``version 3.6`` is installed.



Hierarchical Dependencies
*************************

Managed package dependencies can handle a hierarchy of dependencies between packages.

    Example: Salesforce.org's Nonprofit Success Pack (NPSP), an extension of five other managed packages, one of which (Households) is an extension of another (Contacts & Organizations).

    These dependencies are listed under the ``project`` section of the ``cumulusci.yml`` file.

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

..

    The project requires ``npo02 version 3.8``, which itself requires ``npe01 version 3.6``. By specifying the dependency hierarchy, the ``update_dependencies`` task is capable of uninstalling and upgrading packages intelligently.

    So if the target org currently has ``npe01 version 3.7``, ``npe01`` needs to be uninstalled to downgrade to ``3.6``. However, ``npo02`` requires ``npe01``, so uninstalling ``npe01`` also requires uninstalling ``npo02``. (In this scenario ``npe03``, ``npe04``, and ``npe05`` do not have to be uninstalled to uninstall ``npe01``.)



Unmanaged Metadata Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Specify unmanaged metadata to be deployed by specifying a ``zip_url`` and, optionally, ``subfolder``, ``namespace_inject``, ``namespace_strip``, and ``unmanaged`` under the ``project__dependencies`` section of the cumulusci.yml file.

.. code-block:: yaml

    project:
        dependencies:
            - zip_url: https://SOME_HOST/metadata.zip

When the ``update_dependencies`` task runs, it downloads the zip file and deploys it via the Metadata API. The zip file must contain valid metadata for use with a deploy, including a ``package.xml`` file in the root.



Specify a Subfolder of the Zip File
***********************************

Use the ``subfolder`` option to specify a subfolder of the zip file to use for the deployment. 

.. note:: This option is handy when referring to metadata stored in a GitHub repository.

    Example: ``subfolder: CumulusReports-master/record_types``

.. code-block:: yaml

    project:
        dependencies:
            - zip_url: https://github.com/SalesforceFoundation/CumulusReports/archive/master.zip
              subfolder: CumulusReports-master/record_types

When ``update_dependencies`` runs, it still downloads the zip from ``zip_url``, but then builds a new zip containing only the content of ``subfolder``, starting inside ``subfolder`` as the zip's root.



Inject Namespace Prefixes
*************************

CumulusCI has support for tokenizing references to the namespace prefix in code. When tokenized, all occurrences of the namespace prefix (for example, ``npsp__``), is replaced with ``%%%NAMESPACE%%%`` inside of files and ``___NAMESPACE___`` in file names.

If the metadata you are deploying has been tokenized, use the ``namespace_inject`` and ``unmanaged`` options to inject the namespace.

    Example: ``namespace_inject: hed``

.. code-block:: yaml

    project:
        dependencies:
            - zip_url: https://github.com/SalesforceFoundation/EDA/archive/master.zip
              subfolder: EDA-master/dev_config/src/admin_config
              namespace_inject: hed

..

    The metadata in the zip contains the string tokens ``%%%NAMESPACE%%%`` and ``___NAMESPACE___`` which is replaced with ``hed__`` before the metadata is deployed.

To deploy tokenized metadata without any namespace references, specify both ``namespace_inject`` and ``unmanaged``.

    Example: ``namespace_inject: hed`` and ``unmanaged: True``

.. code-block:: yaml

    project:
        dependencies:
            - zip_url: https://github.com/SalesforceFoundation/EDA/archive/master.zip
              subfolder: EDA-master/dev_config/src/admin_config
              namespace_inject: hed
              unmanaged: True


..

    The namespace tokens are replaced with an empty string instead of the namespace, effectively stripping the tokens from the files and filenames.



Strip Namespace Prefixes
************************

If the metadata in the zip to be deployed has references to a namespace prefix, use the ``namespace_strip`` option to remove them.

    Example: ``namespace_strip: npsp``

.. code-block:: yaml

    project:
        dependencies:
            - zip_url: https://github.com/SalesforceFoundation/CumulusReports/archive/main.zip
              subfolder: CumulusReports-main/src
              namespace_strip: npsp

..

    When ``update_dependencies`` runs, the zip is retrieved and the string ``npsp__`` is stripped from all files and filenames in the zip before deployment.  This option is most useful when setting up an unmanaged development environment for an extension package that normally uses managed dependencies.
    
    This example takes the NPSP Reports & Dashboards project's unmanaged metadata and strips the references to ``npsp__`` to deploy it against an unmanaged version of NPSP.



Automatic Cleaning of ``meta.xml`` Files on Deploy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To let CumulusCI fully manage the project's dependencies, the ``deploy`` task (and other tasks based on ``cumulusci.tasks.salesforce.Deploy``, or subclasses of it) automatically removes the ``<packageVersion>`` element and its children from all ``meta.xml`` files in the deployed metadata. Removing these elements does not affect the files on the filesystem.

This feature supports CumulusCI's automatic dependency resolution by avoiding a need for projects to manually update XML files to reflect current dependency package versions.

.. note:: If the metadata being deployed references namespaced metadata that does not exist in the currently installed package, the deployment throws an error as expected.

.. tip:: The automatic cleaning of ``meta.xml`` files can be disabled by setting the ``clean_meta_xml`` option to ``False``.

One drawback of this approach is that developers need to handle the diffs in the ``meta.xml`` files by either ignoring them, or committing them as part of their work in a feature branch. 

    Example: The diffs come from a scenario of Package B, which extends Package A. When a new production release of Package A is published, the ``update_dependencies`` task for Package B installs the new version. When metadata is then retrieved from the org, the ``meta.xml`` files reference the new version while the repository's ``meta.xml`` files reference an older version.

    The main difference between this situation and one where the ``meta.xml`` file is automatically cleaned is that avoiding the diffs in ``meta.xml`` files is a convenience for developers rather than a requirement for builds and releases. 
    
Developers can also use the ``meta_xml_dependencies`` task to update the ``meta.xml`` files locally using the versions from CumulusCI's calculated project dependencies.



Use Tasks and Flows from a Different Project
--------------------------------------------

Dependency handling is used in a very specific context: to install dependency packages or metadata bundles in a ``dependencies`` flow that is a component of some other flows.

CumulusCI also makes it possible to use automation (tasks and flows) from another CumulusCI project. This feature supports many use cases, including:

* Applying configuration from a dependency project, rather than just installing the package.
* Running Robot Framework tests that are defined in a dependency.

For more information, see `configure cross-project tasks and flows<TODO>`_.
