Release a Managed Package
=========================
This section outlines how to release a first generation (1GP) Salesforce managed package project.
Salesforce.org's Release Engineering team practices :doc:`CumulusCI Flow <cumulusci_flow>`, which incorporates all of these steps.



Prerequisites
-------------
This section assumes:

* :doc:`CumulusCI is installed <get_started>` on your computer.
* A Salesforce managed package :ref:`project has been configured <Work On an Existing CumulusCI Project>` for use with CumulusCI.
* A packaging org :doc:`is connected <connected_orgs>` to CumulusCI under the name of ``packaging``.

To verify this setup and display information about the connected packaging org:

.. code-block:: console

    $ cci org info packaging
    
.. note:: 

    The packaging org can be listed under an alias. For a complete list of orgs connected to CumulusCI, run ``cci org list``.

If your project has been configured for use with CumulusCI, ``cci org info`` lists the project's namespace under ``package__namespace`` in the output.


Create a Managed Package Project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you haven't created a managed package project, follow these steps:

* Create a Developer Edition Org. (`Sign up for one here. <https://developer.salesforce.com/signup>`_)
* `Create a managed package <https://developer.salesforce.com/docs/atlas.en-us.packagingGuide.meta/packagingGuide/packaging_uploading.htm>`_.
* `Assign a namespace <https://developer.salesforce.com/docs/atlas.en-us.packagingGuide.meta/packagingGuide/isv2_3_quickstart.htm>`_.
* Configure the namespace in CumulusCI.



Deploy to a Packaging Org
-------------------------

CumulusCI deploys metadata to a ``packaging`` org with the ``ci_master`` flow.

.. warning::

    The ``ci_master`` flow runs the :ref:`uninstall_packaged_incremental` task, which deletes any metadata from the package in the target org that's not in the repository.

.. code-block:: console

    $ cci flow run ci_master --org packaging

The ``ci_master`` flow executes these tasks in the target org.

* Updates any project dependencies
* Deploys any unpackaged metadata located in the ``pre`` directory
* Deploys packaged metadata
* Deploys destructive changes to remove metadata in the target org that is no longer in the local repository
* Runs the ``config_packaging`` flow, which by default consists only of the :ref:`update_admin_profile` task.

.. tip:: 

    To list each step in the ``ci_master`` flow, run ``cci flow info ci_master``.

CumulusCI separates uploading metadata to the packaging org and releasing a beta version of the package into the ``ci_master`` and ``release_beta`` flows, respectively. This separation offers discretion to run additional checks against the org, if necessary, between deploy and release steps.



Create a Beta Version
---------------------

The ``release_beta`` flow groups the common tasks that must be executed for the release of a new beta version of a project.

.. code-block:: console

    $ cci flow run release_beta --org packaging

This flow *always* runs against the project's ``packaging`` org, where it:

* Uploads a new beta version of the managed package.
* Creates a new GitHub release tag for the new beta version. Extension packages that also use CumulusCI require this release tag to find the latest version when this repository is listed as a dependency.
* :ref:`Generates Release Notes <github_release_notes>`.
* Syncs feature branches with the ``main`` branch, which automatically integrates the latest changes from ``main``. For more information see :ref:`auto merging`.

.. important::
    
    This flow assumes that the package contents were already deployed using the ``ci_master`` flow. It does *not* include a step to deploy them.

To create a new beta version for your project without the bells and whistles, use the ``upload_beta`` task:

.. code-block:: console

    $ cci task run upload_beta --org packaging --name package_version 



Test a Beta Version
-------------------

The ``ci_beta`` flow installs the latest beta version of the project in a scratch org, and runs Apex tests against it.

.. code-block:: console

    $ cci flow run ci_beta --org beta 

This flow is intended to be run whenever a beta release is created.



Generate Release Notes
----------------------

The ``github_release_notes`` task fetches the text from Pull Requests that were merged between two given tags. The task then searches for specific titles (Critical Changes, Changes, Issues Closed, New Metadata, Installation Info, and so on) in the Pull Request bodies, and aggregates the text together under those titles in the GitHub tag description.

To see what the release notes look like without publishing them to GitHub:

.. code-block::

    $ cci task run github_release_notes --tag release/1.2

.. note:: The ``--tag`` option indicates which release's change notes are aggregated. The previous command aggregates all change notes between the `1.2` release and the `1.1` release.

To see where each line in the release notes comes from, use the ``--link_pr True`` option.

.. code-block::

    $ cci task run github_release_notes --tag release/1.2 --link_pr True

To publish the release notes to a release tag in GitHub, use the ``--publish True`` option:

.. code-block::

    $ cci task run github_release_notes --tag release/1.2 --publish True

To use additional headings, add new ones (as parsers) under the ``project__git__release_notes`` section of the ``cumulusci.yml`` file.

.. code-block::

    release_notes:
        parsers:
            7: class_path: cumulusci.tasks.release_notes.parser.GithubLinesParser

.. note:: The new parser is listed with the number ``7`` because the first six are the `default parsers <https://github.com/SFDO-Tooling/CumulusCI/blob/671a0e88cef79e9aeefe1e2b835816cd8141bdbb/cumulusci/cumulusci.yml#L1154>`_ that come with CumulusCI.
        


Upload and Test a Final Version
-------------------------------

To upload a production release of your managed package project:

.. code-block::

    $ cci flow run release_production --org packaging 

Similar to ``release_beta``, this task uploads a new production version of your package, creates a release tag in GitHub, and aggregates release notes for the new version.

.. important::

    This flow assumes that the package contents have previously been deployed using the ``ci_master`` flow.

To upload the new production version without creating the GitHub tag and generating release notes:

.. code-block::

    $ cci task run upload_production --name v1.2.1

To test the new package version:

.. code-block::

    $ cci flow run ci_release --org release

The ``ci_release`` flow installs the latest production release version, and runs the Apex tests from the managed package on a scratch org.



Manage Push Upgrades
--------------------
If your packaging org is enabled to use push upgrades, CumulusCI can schedule push upgrades with the ``push_sandbox`` and ``push_all`` tasks. 

.. warning::

    ``push_all`` schedules push upgrades to *all* customers' production orgs. Please confirm that this action is essential before executing the task.

.. code-block:: console

    $ cci task run push_all --version <version> --org packaging

Replace ``<version>`` with the version of the managed package to be pushed.

By default, push upgrades are scheduled to run immediately.

To schedule the push upgrades to occur at a specific time, use the ``--start_time`` option with a time value in UTC. 

.. code-block:: console

    $ cci task run push_all --version <version> --start_time 2020-10-19T10:00 --org packaging

There are additional tasks related to push upgrades in the CumulusCI standard library.

* :ref:`push_failure_report`: Produces a ``csv`` report of the failed and otherwise anomalous push jobs.
* :ref:`push_list`: Schedules a push upgrade of a package version to all orgs listed in a specified file.
* :ref:`push_qa`: Schedules a push upgrade of a package version to all orgs listed in ``push/orgs_qa.txt``.
* :ref:`push_sandbox`: Schedules a push upgrade of a package version to all subscribers' sandboxes.
* :ref:`push_trial`: Schedules a push upgrade of a package version to Trialforce Template orgs listed in ``push/orgs_trial.txt``.