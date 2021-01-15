The ``cci`` Command Line
========================



Basic Operation
---------------

.. tip:: 
    
    If you are new to working with command line interfaces, the `Install Visual Studio Code <https://trailhead.salesforce.com/content/learn/modules/cumulusci-setup/review-base-requirements-install-visual-studio-code?trail_id=build-applications-with-cumulusci>`_ 
    module covers installing and opening a terminal window in Visual Studio Code.

After installing CumulusCI, use the ``cci`` command in your terminal or command prompt to interact with it.

On a macOS, access the terminal via Terminal.app. On Windows, open cmd.exe.

To see all available commands, type ``cci`` in your terminal:

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

Each of the commands listed in the output have even more (sub) commands that exist underneath them.
This can seem overwhelming at first, but exploring the commands that are available is quite easy.

To get information on a specific command listed above, type ``cci <command_name>``. 

For example, if you want to know more about the ``task`` command, type ``cci task``.

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

This tells us that under the ``cci task`` command there are four more commands available: ``doc``, ``info``, ``list``, and ``run``.
If we want additional information 


Getting ``--help``
------------------

When working with the ``cci`` CLI you can pass the ``--help`` flag to *any* cci command to get additional info about that command.

For top-level commands (those commands that don't do anything on their own but
have additional sub-commands underneath them) this output will be the same with or without the ``--help`` flag.

For example, the following commands will produce the same output.

.. code-block::

    $ cci task
    
    $ cci task --help

This will output any sub-commands available under this particular top-level command

.. code-block:: console

    $ cci task --help
    Usage: cci task [OPTIONS] COMMAND [ARGS]...

    Commands for finding and running tasks for a project

    Options:
    --help  Show this message and exit.

    Commands:
    doc   Exports RST format documentation for all tasks
    info  Displays information for a task
    list  List available tasks for the current context
    run   Runs a task



When the ``--help`` flag is specified for a fully realized command (one that is executable) (TODO: what is correct word here?)
the output will display:

#. A usage statement for the syntax with which the command can be executed
#. The list of available options for use with the command 




Working with Tasks and Flows
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

CumulusCI comes with *many* standard tasks and flows. If you're just starting out with CumulusCI, and feeling overwhelmed, don't worry.
We have a `cheat sheet <TODO>`_ for examples of the most commonly used commands as well as reference sections for both `tasks <TODO>`_ and `flows <TODO>`_.


Listing Tasks and Flows
***********************

Use the ``cci task list`` and ``cci flow list`` commands to see a list of available tasks and flows respectively.

The tasks and flows listed are specific to the project directory that you're currently in.
For example, if you have a custom flow defined in your ``cumulusci.yml`` file for Project A, it will only show if you run ``cci flow list`` in Project A's root directory.

Tasks and flows are listed by their ``group`` attribute as specified in the ``cumulusci.yml`` file.
You can edit the ``group`` attribute of tasks and flows as you see fit!
Any changes made to ``groups`` are reflected in the output of the ``list`` commands.

Task and Flow Options  
*********************
Many tasks (and some flows) have options that need to be specified when executed.
To see a list of available task options use either of the following commands:

TODO: make ``cci task run --help`` mirror output from ``cci task info``

.. code-block:: console

    $ cci task info <task_name>
    $ cci task run <task_name> --help

Information about specific tasks includes:

* A description of what the task does.
* The particular Python class associated with this task.
* The syntax for running the command.
* Any options for the task.

For each option available for a given task we also list:

* The syntax for the option (``--name value``).
* If the option is required or optional.
* A description of what the option does.

Here's an example where we get information on the ``util_sleep`` method:

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

You can use either of the following commands for more informaiton on a specific flow:

TODO: Make sure these outputs are the same

.. code-block:: console

    $ cci flow info <flow_name>
    $ cci flow run --help

Information about specific flows includes:

* A description of the flow.
* The ordered steps (and substeps) of a flow.

An example of a flow's information and options:

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



Running Tasks and Flows
***********************
When you know the specific task or flow you want to run, execute it with the ``run`` command.

.. code-block:: console

    $ cci task run <name> --org <org> [options]
    $ cci flow run <name> --org <org> [options]

This runs the respective task or flow ``<name>`` against the org ``<org>``. (You can see a list of available orgs by running ``cci org list``.)

Example: The ``run_tests`` task executes Apex unit tests. Assuming there exists an org named ``dev``,
you can run this task against it with the command ``cci task run run_tests --org dev``.




Troubleshooting Errors
----------------------

Errors happen! That's why our team strives to provide our users with options for efficiently solving them when they occur.


Reporting Error Logs 
^^^^^^^^^^^^^^^^^^^^

The ``cci error gist`` command sends the most recent log file to a `GitHub gist <https://docs.github.com/en/github/writing-on-github/creating-gists>`_ so you can quickly and easily share logs with others. For this feature to work you need to ensure that your `github service is set up with the proper scopes <https://cumulusci.readthedocs.io/en/latest/tutorial.html#github-service>`_.

Information included in the gist:

* The current version of ``cci``
* The current Python version
* The path to the Python executable
* The ``sysname`` of the host (such as Darwin)
* The machine name of the host (such as x86_64)
* The most recent log file (cci.log) that CumulusCI has created.

The URL for the gist is displayed on the user terminal as output, and a web browser automatically opens a tab to the gist.


The ``--debug`` Option
^^^^^^^^^^^^^^^^^^^^^^

All CumulusCI commands can be passed the ``--debug`` option. When the option is used:

* Any calls to CumulusCI's logger at the debug level are shown.
* Outgoing HTTP requests are logged.
* If an error is present, the corresponding stacktrace is shown, and the user is dropped into a `post-mortem debugging <https://docs.python.org/3/library/pdb.html#pdb.post_mortem>`_ session.

.. note:: To exit a debugging session type the command ``quit`` or ``exit``.


Log Files
^^^^^^^^^

CumulusCI creates a log file every time a cci command runs. There are six rotating log files (``cci.log, cci.log1...5``) with ``cci.log`` being the most recent. Log files are stored under ``~/.cumulusci/logs``.

By default, log files document:

* The last command that was entered by the user.
* All output from the command (including debug information).
* If a Python-level exception occurs, the corresponding stacktrace is included.

.. note:: If you want debug information regarding the ``requests`` module to be documented in a log file, you must explicitly run the command with the ``--debug`` option.


Viewing Stacktraces
^^^^^^^^^^^^^^^^^^^

If you encounter an error and want more information on what caused it, the ``cci error info`` command displays the last ``n`` lines of the stacktrace (if present) from the last command executed in CumulusCI. (Note that this a Python stacktrace showing where CumulusCI encountered an error.)

Additionally, there is a ``--max-lines`` option to limit the number of lines of stacktrace shown.


Seeing Stacktraces Automatically
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you would like to investigate bugs in CumulusCI when you find them, set the config option ``show_stacktraces`` to ``True`` in the ``cli`` section of ``~/.cumulusci/cumulusci.yml``. Afterward, stacktraces are no longer suppressed when they are thrown within CumulusCI.

Usage Errors (wrong command line arguments, missing files, and so on) don't show exception tracebacks because they are seldom helpful in that case.

If you need further assistance troubleshooting errors or stacktraces, reach out to our team on the `CumulusCI Trailblazer Community Group <https://trailblazers.salesforce.com/_ui/core/chatter/groups/GroupProfilePage?g=0F9300000009M9Z>`_.