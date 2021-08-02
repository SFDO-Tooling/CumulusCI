Manage Push Upgrades
--------------------
If your packaging org (for first-generation packages) or Dev Hub (for second-generation packages) is enabled to use push upgrades,
CumulusCI can schedule push upgrades with the ``push_sandbox`` and ``push_all`` tasks. 

.. warning::

    ``push_all`` schedules push upgrades to *all* customers' production and sandbox orgs. Please confirm that this action is desired before executing the task.

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