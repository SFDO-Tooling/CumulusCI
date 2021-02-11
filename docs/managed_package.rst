Release a Managed Package
=========================

This section outlines how to release a first generation (1GP) Salesforce Managed Package project. Salesforce.org's Release Engineering team practices `CumulusCI Flow<TODO link>`_, which incorporates all of these steps.

Prerequisites
-------------
This section assumes:

* CumulusCI is installed on your computer.
* A Salesforce Managed Package project has been configured for use with CumulusCI.
* Your packaging org is connected to CumulusCI under the name of ``packaging``.



Deploy to a Packaging Org
-------------------------
CumulusCI enables you to deploy to your packaging org.

.. warning::

    The ``ci_master`` flow runs the `uninstall_packaged_incremental<TODO>`_ task.
    This task deploys destructive changes to the target org.

.. code-block:: console

    $ cci flow run ci_master --org packaging


.. note::

    This flow is `source format agnostic<TODO>`_.

The ``ci_master`` flow executes these tasks in the target org.

* Updates any project dependencies
* Deploys any unpackaged metadata located in the ``pre/`` directory
* Deploys package metadata
* Deploys destructive changes to remove metadata in the target org that is no longer in the local workspace



Create a Beta Version
---------------------

The ``release_beta`` flow groups the common tasks that must be executed for the release of a new beta version of a project.

.. code-block:: console

    $ cci flow run release_beta --org packaging

This flow typically runs against the project's packaging org where it:

* Uploads new beta version to the packaging org
* Creates a new GitHub release tag for the new beta version
* `Generates Release Notes`_
* Syncs feature branches with the ``main/`` branch

If you just want to create a new beta version for your project,
without the bells and whistles, you can just use the ``upload_beta`` task:

.. code-block:: console

    $ cci task run upload_beta --name package_version 



Test a Beta Version
-------------------

The ``ci_beta`` flow installs the latest beta version of the project into a scratch org, and executes tests against it.

.. code-block:: console

    $ cci flow run ci_beta --org <TODO> 

This flow is intended to be run every time a beta release is created.



Generate Release Notes
----------------------

The ``github_release_notes`` task fetches the text from pull requests that were merged between two given tags. The task then searches for specific titles (Critical Changes, Changes, Issues Closed, New Metadata, Installation Info, and so on) in the pull request bodies, and aggregates the text together under those titles in in the description of a GitHub tag.

To view what the release notes look like without publishing them to GitHub:

.. code-block::

    $ cci task run github_release_notes --tag release/1.2

This command aggregates text from pull requests between releases 1.2 and the next most recent release. You can also see where each line in the release notes comes from by using the ``--link_pr True`` option.

To publish these release notes to a release tag in GitHub, use the ``--publish`` option:

.. code-block::

    $ cci task run github_release_notes --tag release/1.2 --publish True


If your team wants to use additional headings, add new ones under the ``project__git__release_notes__parsers`` section of your ``cumulusci.yml`` file.

.. code-block::

    release_notes:
        parsers:
            7: class_path: cumulusci.tasks.release_notes.parser.GithubLinesParser

.. note:: The new parser is listed with the number ``7`` because the first six are the `default parsers <https://github.com/SFDO-Tooling/CumulusCI/blob/671a0e88cef79e9aeefe1e2b835816cd8141bdbb/cumulusci/cumulusci.yml#L1154>`_ that come with CumulusCI.
        


Upload and Test a Final Version
-------------------------------

When you're ready to upload a production release of your Managed Package project, use the ``--production True`` option.

.. code-block::

    $ cci flow run release_production --org packaging 

Similar to ``release_beta``, this task uploads a new production version of your package, creates a release tag in GitHub, and aggregates release notes for the new version.

To upload the new production version without creating the GitHub tag and generating release notes:

.. code-block::

    $ cci task run upload_beta --name v1.2.1 --production True

To test the new package version:

.. code-block::

    $ cci flow run ci_release

This flow installs the latest production release version, and runs the tests from the managed package in a scratch org.



Publish an Install Plan to MetaDeploy
-------------------------------------



Manage Push Upgrades
--------------------

