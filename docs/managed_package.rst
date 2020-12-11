Release a Managed Package
=========================
This section outlines the various steps involved in releasing a first generation (1GP) Salesforce Managed Package project.
Salesforce.org's Release Engineering team practices `CumulusCI Flow<TODO link>` which incorporates all of these steps.

Prerequisites
-------------
This section assumes:

* CumulusCI is installed on your computer.
* There exists Salesforce Managed Package project configured for use with CumulusCI.
* You have connected your packaging org to CumulusCI under the name of ``packaging``.



Deploy to a Packaging Org
-------------------------
CumulusCI easily enables you to easily deploy to your packaging org:

.. warning::

    The ``ci_master`` flow runs the `uninstall_packaged_incremental <TODO>` task.
    This task deploys destructive changes to the target org.

.. code-block:: console

    $ cci flow run ci_master --org packaging


.. note::

    This flow is `source format agnostic <TODO>`.

The ``ci_master`` flow does the following in the target org:

#. Update any project dependencies
#. Deploy any unpackaged metadata located in the ``pre/`` directory.
#. Deploy package metadata
#. Deploy destructive changes to remove metadata in the target org that is no longer in the local workspace.



Create a Beta Version
---------------------
The ``release_beta`` flow exists to group the common tasks that we want
to execute when we release a new beta version of a project.

.. code-block:: console

    $ cci flow run release_beta --org packaging

The ``release_beta`` flow does the following: 

* Upload a new beta version to the packaging org
* Create a new GitHub release tag for the new beta version
* `Generate Release Notes`_
* Sync feature branches with the ``main/`` branch.

If you just want to create a new beta version for your project,
you can use the ``upload_beta`` task:

.. code-block:: console

    $ cci task run upload_beta --name package_version 



Test a Beta Version
-------------------
Test your latest new Beta version with:

.. code-block:: console

    $ cci flow run ci_beta --org <TODO> 

This flow installs the latest beta version of the project into a scratch org, and executes tests against it.
This flow is intended to be run every time a beta release is created.



Generate Release Notes
----------------------
The ``github_release_notes`` task fetches the text from pull requests that
were merged between two given tags. The task then searches for specific titles
(Critical Changes, Changes, Issues Closed, New Metadata, Installation Info) in
the pull request bodies and aggregates the text together under those titles in
a single pul 


If you want to just view the output of what this would look like you can use:

.. code-block::

    $ cci task run github_release_notes --tag release/1.2

This would aggregate text from pull requests between releases 1.2 and next most recent release.
You can also see where each line in the aggregated result came from by using the ``--link_pr True`` option.

If you want to publish these release notes to a release tag in GitHub use the ``--publish`` option:

.. code-block::

    $ cci task run github_release_notes --tag release/1.2 --publish True


If your team wants to use additional headings you can add new ones by
putting the following under the ``project`` -> ``git`` section of your ``cumulusci.yml`` file:

.. code-block::

    release_notes:
        parsers:
            7: class_path: cumulusci.tasks.release_notes.parser.GithubLinesParser

.. note::

    The new parser is listed with the number ``7`` because the first six are the
    `default parsers <https://github.com/SFDO-Tooling/CumulusCI/blob/671a0e88cef79e9aeefe1e2b835816cd8141bdbb/cumulusci/cumulusci.yml#L1154>`_ that come with CumulusCI.

        


Upload and Test a Final Version
-------------------------------




Publish an Install Plan to MetaDeploy
-------------------------------------



Manage Push Upgrades
--------------------

