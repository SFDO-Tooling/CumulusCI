The ``cci`` Command Line
========================



Basic Operation
---------------

.. tip::

    If you're new to working with command line interfaces, the `Install Visual Studio Code <https://trailhead.salesforce.com/content/learn/modules/cumulusci-setup/review-base-requirements-install-visual-studio-code?trail_id=build-applications-with-cumulusci>`_ Trailhead module covers installing and opening a terminal window in Visual Studio Code.

After :doc:`installing CumulusCI <get_started>`, use the ``cci`` command in your terminal or command prompt to interact with it.

On any platform, you can use the integrated terminal in Visual Studio Code.
Alternately, on macOS, access the terminal via ``Terminal.app``; on Windows, open ``cmd.exe``; or on Linux, use your preferred terminal application.

To see all available commands, type ``cci`` in your terminal.

.. code-block:: console

    $ cci
    Usage: cci [OPTIONS] COMMAND [ARGS]...

    Options:
    --help  Show this message and exit.

    Commands:
    error    Get or share information about an error
    flow     Commands for finding and running flows for a project
    org      Commands for connecting and interacting with Salesforce orgs
    project  Commands for interacting with project repository configurations
    service  Commands for connecting services to the keychain
    shell    Drop into a Python shell
    task     Commands for finding and running tasks for a project
    version  Print the current version of CumulusCI

To retrieve information on a specific command, type ``cci <command>``.

Let's examine the ``cci task`` command:

.. code-block:: console

    $ cci task
    Usage: cci task [OPTIONS] COMMAND [ARGS]...

    Commands for finding and running tasks for a project

    Options:
    --help  Show this message and exit.

    Commands:
    doc   Exports RST format documentation for all tasks
    info  Displays information for a task
    list  List available tasks for the current context
    run   Runs a task

We can see that the ``cci task`` command has many useful subcommands, such as ``cci task info``.



List Tasks and Flows
--------------------

CumulusCI ships with many standard tasks and flows. The following commands list all available tasks and flows for a project:

.. code-block:: console

    $ cci task list
    $ cci flow list

The tasks and flows listed are specific to the project directory that you're in when you run the command.
For example, if you have a custom flow defined in your ``cumulusci.yml`` file for Project A, it will only be listed if you run ``cci flow list`` in Project A's root directory.

Tasks and flows are listed by their ``group`` attribute as specified in the ``cumulusci.yml`` file.
It's easy to edit these groups as you see fit! Any modifications will be reflected in the ``list`` commands.




Task Info and Options
---------------------

For additional information on task ``<name>``, run either command:

.. code-block:: console

    $ cci task info <name>
    $ cci task run <name> --help

Information about specific tasks includes:

* A description of the task.
* The Python class associated with this task.
* The syntax for running the command.
* Any options accepted or required by the task.

Each option available for a given task also lists:

* The syntax for the option (``--<name> value``).
* Whether the option is required or optional.
* A description of the option.
   
Let's examine the ``util_sleep`` task:

.. code-block:: console

    $ cci task info util_sleep
    util_sleep

    Description: Sleeps for N seconds

    Class: cumulusci.tasks.util.Sleep

    Command Syntax

        $ cci task run util_sleep

    Options

        --seconds SECONDS
        Required
        The number of seconds to sleep
        Default: 5



Flow Info and Options
---------------------

For additional information on flow ``<name>``, run either command:

.. code-block:: console

    $ cci flow info <name>
    $ cci flow run --help

Information about specific flows includes:

* A description of the flow.
* The ordered steps (and substeps) of a flow.

For example, listing the info for the ``dev_org`` flow shows that it's composed of three subflows: ``dependencies``, ``deploy_unmanaged``, and ``config_dev``, and one task: ``snapshot_changes``.
The tasks and flows making up the three subflows are also listed.

.. code-block:: console

    $ cci flow info dev_org
    Description: Set up an org as a development environment for unmanaged metadata
    1) flow: dependencies [from current folder]
        1) task: update_dependencies
        2) task: deploy_pre
    2) flow: deploy_unmanaged
        0) task: dx_convert_from
        when: project_config.project__source_format == "sfdx" and not org_config.scratch
        1) task: unschedule_apex
        2) task: update_package_xml
        when: project_config.project__source_format != "sfdx" or not org_config.scratch
        3) task: deploy
        when: project_config.project__source_format != "sfdx" or not org_config.scratch
        3.1) task: dx_push
        when: project_config.project__source_format == "sfdx" and org_config.scratch
        4) task: uninstall_packaged_incremental
        when: project_config.project__source_format != "sfdx" or not org_config.scratch
    3) flow: config_dev
        1) task: deploy_post
        2) task: update_admin_profile
    4) task: snapshot_changes



Run Tasks and Flows
-------------------

Execute a specific task or flow with the ``run`` command.

.. code-block:: console

    $ cci task run <name> --org <org> [options]
    $ cci flow run <name> --org <org> [options]

This command runs the task or flow ``<name>`` against the org ``<org>``. 

.. tip::

    You can see a list of available orgs by running ``cci org list``.

For example, the ``run_tests`` task executes Apex unit tests in a given org.
Assuming there exists an org named ``dev``, you can run this task against it with the command ``cci task run run_tests --org dev``.



Get Help Running Tasks
**********************

If you're not certain about what a specific command does, use the ``--help`` flag to get more information. 

.. code-block::

    $ cci task info <name> --help

When the ``--help`` flag is specified for a command, the output includes:

* A usage statement featuring the syntax that executes the command.
* A description of the command.
* The list of available options for use with the command.

.. code-block:: console

    $ cci task --help
    Usage: cci task [OPTIONS] COMMAND [ARGS]...

    Options:
    --help  Show this message and exit.

    Commands:
    doc   Exports RST format documentation for all tasks
    info  Displays information for a task
    list  List available tasks for the current context
    run   Runs a task

If you're just getting started with CumulusCI and aren't sure which of the many tasks and flows to use, don't worry. We show you specific tasks and flows in later sections of the documentation. 



Specify Task Options When Running Flows
***************************************
When executing a flow with ``cci flow run``, you can specify
options on specific tasks in the flow with the following syntax:

.. code-block::

    $ cci flow run <flow_name> -o <task_name>__<option_name> <value>

``<flow_name>`` is the name of the flow to execute, <task_name> is the name
of the task you wish to specify an option for, <option_name> is the option on the
task you want to specify, and <value> is the actual value you want to assign to the task option.

For example, in the above output from ``cci flow info dev_org`` if we wanted to set the ``allow_newer``
option on the ``update_dependencies`` to ``True``, we would use the following:

.. code-block::

    $ cci flow run dev_org --org dev -o update_dependencies__allow_newer True

.. note:: 

    If the specified task executes more than once in the flow,
    it uses the given option value *each time it executes*.

If you want to configure specific task options on flows without explicitly
listing them see :ref:`Configure Options on Tasks in Flows`.



Access and Manage Orgs
----------------------

CumulusCI makes it easy to create, connect, and manage orgs. The ``cci org`` top-level command helps you work with orgs.

To learn about working with orgs in detail, read :doc:`Manage Scratch Orgs <scratch_orgs>`
and :doc:`Connect Persistent Orgs <connected_orgs>`.



Manage Services 
---------------
Services represent external resources used by CumulusCI automation, such as access to a GitHub account or a MetaDeploy instance.

List Services
*************
You can have CumulusCI show you a list of all possible services supported.
Services that are not currently configured will be displayed in a dimmed row.

.. code-block:: console

    $ cci service list

Connect A Service
*****************
To connect a service to the global keychain (which we recommend for almost all situations) you can use:

.. code-block:: console

    $ cci service connect <service_type> <service_name>

If you wanted to connect to your personal GitHub account as a service you could use:

.. code-block:: console

    $ cci service connect github personal 

CumulusCI will prompt you for the required information for the given service type.

If you want a service to onlye be available to a given project you can pass the ``--project`` flag.

.. code-block:: console

    $ cci service connect <service_type> <service_name> --project 


Set a Default Service
*********************
The first service connected for a given service type is automatically set as the default service for that type.
If you have multiple services connected for a given type and would like to set a new default use:

.. code-block:: console

    $ cci service default <service_type> <service_name> 

Rename a Service
****************
To rename a service use:

.. code-block:: console

    $ cci service rename <service_type> <old_name> <new_name>

Remove a Service
****************
To remove a service use:

.. code-block:: console

    $ cci service remove <service_type> <service_name>

Troubleshoot Errors
-------------------

Errors happen! That's why ``cci`` provides tools to extract error details so that they can be reported and triaged.



Report Error Logs
*****************

The ``cci error gist`` command sends the most recent log file to a `GitHub gist <https://docs.github.com/en/github/writing-on-github/creating-gists>`_ so you can quickly and easily share logs with others. For this feature to work you need to make sure that your `GitHub  service is set up with the proper scopes <https://cumu:lusci.readthedocs.io/en/latest/tutorial.html#github-service>`_.

The gist includes:

* The current version of ``cci``
* The current Python version
* The path to the Python executable
* ``sysname`` of the host (such as Darwin)
* The machine name of the host (such as x86_64)
* The most recent log file (cci.log) that CumulusCI has created.

The URL for the gist is displayed in the terminal as output, and a web browser automatically opens a tab to the gist.



View Stack Traces
*****************

If you encounter an error and want more information on what caused it, the ``cci error info`` command displays the  stack trace (if present) from the last command executed in CumulusCI. 

.. note:: The stack trace displayed is a *Python* stacktrace. This is helpful for locating where CumulusCI encountered an error in the source code.



See Stack Traces Automatically
******************************

If you'd like to investigate bugs in CumulusCI, set the config option ``show_stacktraces`` to ``True`` under the ``cli`` section of ``~/.cumulusci/cumulusci.yml``. It turns off suppression of stack traces.

Usage errors (such as incorrect command line arguments, missing files, and so on) don't show exception tracebacks because they are seldom helpful in that case.

For help with troubleshooting errors or stack traces, reach out to the CumulusCI team on the `CumulusCI Trailblazer Community Group <https://trailblazers.salesforce.com/_ui/core/chatter/groups/GroupProfilePage?g=0F9300000009M9Z>`_.



The ``--debug`` Flag
********************

All CumulusCI commands can be passed the ``--debug`` flag, so that:

* Any calls to CumulusCI's logger at the debug level are shown.
* Outgoing HTTP requests are logged.
* If an error is present, the corresponding stack trace is shown, and the user is dropped into a `post-mortem debugging <https://docs.python.org/3/library/pdb.html#pdb.post_mortem>`_ session.

.. note:: To exit a debugging session, type the command ``quit`` or ``exit``.



Log Files
*********

CumulusCI creates a log file every time a cci command runs. There are six rotating log files (``cci.log, cci.log1...5``) with ``cci.log`` being the most recent. Log files are stored under ``~/.cumulusci/logs`` for Mac and Linux users, and ``C:\Users\<Your User>\.cumulusci\logs`` for Windows users.

By default, log files document:

* The last command that was entered by the user.
* All output from the command (including debug information).
* If a Python-level exception occurs, the corresponding stack trace.

If you want debug information regarding HTTP calls made during execution, you must explicitly run the command with the ``--debug`` flag set.

.. code-block:: console

    $ cci task run <name> --org <org> --debug
    $ cci flow run <name> --org <org> --debug


