The ``cci`` Command Line
========================



Basic Operation
---------------

Once CumulusCI is installed, use the ``cci`` command in your terminal or command prompt to interact with it. On a macOS, access the terminal via Terminal.app. On Windows, open cmd.exe.

If you are new to working with command line interfaces, CumulusCI has a `trailhead module <https://trailhead.salesforce.com/content/learn/modules/cumulusci-setup/review-base-requirements-install-visual-studio-code?trail_id=build-applications-with-cumulusci>`_ that covers installing and opening a terminal window in Visual Studio Code.

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

To get information on a specific command listed above, type ``cci <command>``. 

    For example, if you would like more information on the ``task`` command, type ``cci task``:

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

There are even more subcommands available under ``cci task``.



Getting ``--help``
------------------

If you want help running a task, type ``cci task run --help``. If you're not certain about what a specific command does, use the ``--help`` option to get more information. 

.. code-block:: console

    $ cci task run --help
    Usage: cci task run [OPTIONS] TASK_NAME

    Runs a task

    Options:
    --org TEXT      Specify the target org.  By default, runs against the
                    current default org

    -o TEXT...      Pass task specific options for the task as '-o option
                    value'.  You can specify more than one option by using -o
                    more than once.

    --debug         Drops into pdb, the Python debugger, on an exception
    --debug-before  Drops into the Python debugger right before task start.
    --debug-after   Drops into the Python debugger at task completion.
    --no-prompt     Disables all prompts.  Set for non-interactive mode use such
                    as calling from scripts or CI systems

    --help          Show this message and exit.    

This gives us a clear usage statement, description, and a list of all options available for use with the command.



Working with Tasks and Flows
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you're just getting started with CumulusCI, don't worry if you aren't sure which of the many tasks and flows to use. We'll show you specific tasks and flows in later sections of the documentation. 


Listing Tasks and Flows
***********************

``cci`` ships with many standard tasks and flows. There are two commmands for listing them:

.. code-block:: console

    $ cci task list
    $ cci flow list

The tasks and flows listed are specific to the project you're currently in. If you have a custom flow defined in your ``cumulusci.yml`` file for Project A, it will only show if you run ``cci flow list`` in Project A's repository directory.

Tasks and flows are listed by their ``group`` attribute as specified in the ``cumulusci.yml`` file. This means it's easy to edit these groups as you see fit! Any changes made will be reflected in the commands.


Running Tasks and Flows
***********************
Once you know the specific task or flow you want to run, execute it with the ``run`` command:

.. code-block:: console

    $ cci task run <name> --org <org> [options]
    $ cci flow run <name> --org <org> 

This runs the respective task or flow ``<name>`` against the org ``<org>``. (You can see a list of available orgs by running ``cci org list``.)

    Example: The ``run_tests`` task executes Apex unit tests. If you have an org called ``dev``, you can run this task against it with the command ``cci task run run_tests --org dev``.

Tasks usually require additional options to be passed when using the ``cci task run`` command.


Task Info & Options
*******************

For additional information on tasks:

    $ cci task info <name>

where ``<name>`` is the name of a specific task.

Information about specific tasks includes:

* A description of what the task does.
* The particular Python class associated with this task.
* The syntax for running the command.
* Any options for the task.

Information about specific task options includes:

* The syntax for the option (``-o <name> value``).
* If the option is required or optional.
* A description of what the option does.

An example of a task's information and options:

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

For additional information on flows:

    $ cci flow info <name>

where ``<name>`` is the name of a specific flow.

Information about specific flows includes:

* A description of the flow.
* The ordered steps (and substeps) of a flow.

Example output looks like this:

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



Troubleshooting Errors
----------------------

Errors happen! That's why our team strives to provide our users with options for efficiently solving them when they occur.


Reporting Error Logs 
^^^^^^^^^^^^^^^^^^^^

Use the ``cci error gist`` command to send the most recent log file to a `GitHub gist <https://docs.github.com/en/github/writing-on-github/creating-gists>`_ so you can quickly and easily share logs with others. For this feature to work you will need to ensure that your `github service is set up with the proper scopes <https://cumulusci.readthedocs.io/en/latest/tutorial.html#github-service>`_.

The following information is included in the gist:
    * The current version of ``cci``
    * The current Python version
    * The path to the Python executable
    * The ``sysname`` of the host (e.g., Darwin)
    * The machine name of the host (e.g., x86_64)
    * The most recent log file (cci.log) that CumulusCI has created.

The URL for the gist is displayed on the user terminal as output, and a web browser will automatically open a tab to the gist.


The ``--debug`` Option
^^^^^^^^^^^^^^^^^^^^^^

All CumulusCI commands can be passed the ``--debug`` option. When this is used, the following occurs:

* Any calls to CumulusCI's logger at the debug level are shown.
* Outgoing HTTP requests are logged.
* If an error is present, the corresponding stacktrace is shown, and the user is dropped into a `post-mortem debugging <https://docs.python.org/3/library/pdb.html#pdb.post_mortem>`_ session.
    * To exit a debugging session type the command ``quit`` or ``exit``.


Log Files
^^^^^^^^^

CumulusCI creates a log file every time a cci command runs. There are six rotating log files (``cci.log, cci.log1...5``) with ``cci.log`` being the most recent. Log files are stored under ``~/.cumulusci/logs``. By default, log files document the following:
    * The last command that was entered by the user.
    * All output from the command (including debug information).
    * If a Python-level exception occurs, the corresponding stacktrace is included.

    .. note:: If you want debug information regarding the ``requests`` module to be documented in a log file, you must explicitly run the command with the ``--debug`` option.


Viewing Stacktraces
^^^^^^^^^^^^^^^^^^^

If you encounter an error and want more information on what caused it, use ``cci error info`` to display the last ``n`` lines of the stacktrace (if present) from the last command executed in CumulusCI. (Note that this a Python stacktrace showing where CumulusCI encountered an error.)

.. code-block:: console 

    $ cci error info

Additionally, there is a ``--max-lines`` option to limit the number of lines of stacktrace shown.


Seeing Stacktraces Automatically
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you would like to investigate bugs in CumulusCI when you find them, you can set the config option ``show_stacktraces`` to ``True`` in the ``cli`` section of ``~/.cumulusci/cumulusci.yml``, and stacktraces will no longer be suppressed when they are thrown within CumulusCI.
Usage Errors (wrong command line arguments, missing files, etc.) will not show exception tracebacks because they are seldom helpful in that case.

If you need further assistance troubleshooting errors or stacktraces, reach out to our team on the `CumulusCI Trailblazer Community Group <https://trailblazers.salesforce.com/_ui/core/chatter/groups/GroupProfilePage?g=0F9300000009M9Z>`_.