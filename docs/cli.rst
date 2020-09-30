The ``cci`` Command Line
========================

Basic Operation
---------------
Once CumulusCI is installed, the primary way you will interact with it is using the ``cci`` command in your terminal or command prompt.
On a macOS this would be Terminal.app, on a Windows machine this would be cmd.exe.

If you are new to working with command line interfaces, CumulusCI has a `trailhead module <https://trailhead.salesforce.com/content/learn/modules/cumulusci-setup/review-base-requirements-install-visual-studio-code?trail_id=build-applications-with-cumulusci>`_ the covers installing and opening a terminal window in Visual Studio Code.

To see the available commands, you can simply type ``cci``:

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

To get information on a specific command listed above, you can type ``cci <command>``.
For example, if you woule like more information on the ``task`` command just type ``cci task``:

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

We see that there are even more subcommands available under ``cci task``.

Getting ``--help``
------------------
If we want help with running a task you could type ``cci task run --help``:
If you aren't sure what a specific command does you can always utilize the ``--help`` option.

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

This gives us a clear usage statement, description, and shows all options available for use with the command.


Working with Tasks and Flows
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If you're just getting started with CumulusCI, don't worry if you aren't sure which of the many tasks and flows to use.
We'll show you specific tasks and flows in later sections of the documentation. 

Listing Tasks and Flows
****************************
``cci`` ships with many standard tasks and flows.
``cci`` has two commands for listing available tasks and flows:

.. code-block:: console

    $ cci task list
    $ cci flow list

The tasks and flows listed are *specific to the project* you're running the command int.
If you have a custom flow defined in your ``cumulusci.yml`` file for ProjectA, it will only show if you run ``cci flow list`` in ProjectA's repository directory.
Tasks and Flows are listed grouped by their ``group`` attribute as specified in the ``cumulusci.yml`` file.
This means it's easy to edit these groups as you see fit!
Any changes made will be reflected in these commands.


Running Tasks and Flows
*******************************
Once you know the specific task or flow you want to run, you can execute it with the ``run`` command:

.. code-block:: console

    $ cci task run task_name --org org_name [Options]
    $ cci flow run flow_name --org org_name [Options]

Where ``task_name`` and ``flow_name`` are the actual name of the task or flow that you would like to run, and ``org_name`` is the name of the org that you want to run the task or flow against. 
(You can see a list of orgs available to you by runnin ``cci org list``).
Tasks usually require additional options to be passed when using the ``cci task run`` command.
See the next section for how to view task specific option information. 



Getting More Information
*******************************
For additional information on tasks use::

    $ cci task info <task_name>

Where ``<task_name>`` is the name of a specific task.
Information about specific tasks includes:

* A description of what the task does
* The specific Python class associated with this task
* The syntax for running the command
* Any options for the task

Information on specific options includes:

* The syntax for the option (``-o option_name value``).
* If the options is required or optional.
* A description of each option.

Example output looks like this:

.. code-block:: console

    $ cci task info util_sleep
    util_sleep

    Description: Sleeps for N seconds

    Class: cumulusci.tasks.util.Sleep

    Command Syntax

        $ cci task run util_sleep

    Options

        -o seconds SECONDS
        Required
        The number of seconds to sleep
        Default: 5

For additional information on flows use::

    $ cci flow info <flow_name>

Where ``<flow_name>`` is the actual name of the flow.
Information on specific flows includes:

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
Errors happen!
That’s why our team strives to provide our users with options for efficiently working with them when they occur.
If you need additional troubleshooting errors or stacktraces, you can reach out to our team on the `CumulusCI Trailblazer Community Group <https://trailblazers.salesforce.com/_ui/core/chatter/groups/GroupProfilePage?g=0F9300000009M9Z>`_.



Reporting Error Logs 
^^^^^^^^^^^^^^^^^^^^
Use the ``cci error gist`` command to send the most recent log file to a `GitHub gist <https://docs.github.com/en/github/writing-on-github/creating-gists>`_ so you can quickly and easily share logs with others. 

For this feature to work you will need to ensure that your `github service is setup with the proper scopes <https://cumulusci.readthedocs.io/en/latest/tutorial.html#github-service>`_.

The following information is included in the gist:
    * The current version of ``cci``
    * The current python version
    * The path to the python executable
    * The ``sysname`` of the host (e.g. Darwin)
    * The machine name of the host (e.g. x86_64)
    * The most recent log file (cci.log) that CumulusCI has created.

The URL for the gist is displayed on the terminal of the user as output, and a web browser will automatically open a tab to the gist.



The ``--debug`` Option
^^^^^^^^^^^^^^^^^^^^^^
All CumulusCI commands can be passed the ``--debug`` option. When this is used, the following occurs:

* Any calls to CumulusCI's logger at the debug level are shown.
* Outgoing HTTP requests will be logged.
* If an error is present, the corresponding stacktrace is shown, and the user is dropped into a `post-mortem debugging <https://docs.python.org/3/library/pdb.html#pdb.post_mortem>`_ session.
    * To exit a debugging session type the command: ``quit`` or ``exit`` 



Log Files
^^^^^^^^^
CumulusCI creates a log file every time a cci command run. There are six rotating log files (``cci.log, cci.log1...5``) with ``cci.log`` being the most recent. Log files are stored under ``~/.cumulusci/logs``. By default, log files capture the the following:
    * The last command that was entered by the user
    * All output from the command (including debug information)
    * If an error is present, the corresponding stacktrace is included.

If you want debug information regarding the ``requests`` module to be captured in a log file you must explicitly run the command with the ``--debug`` option.



Viewing Stacktraces
^^^^^^^^^^^^^^^^^^^
If you encounter an error and want more information on what went wrong, you can use ``cci error info`` to display the last ``n`` lines of the stacktrace (if present) from the last command you executed in CumulusCI.
Note that the stacktrace is a Python stacktrace showing where CumulusCI encountered an error.

.. code-block:: console 

    $ cci error info



Seeing Stack Traces Automatically
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If you would like to investigate bugs in CumulusCI when you find
them, you can set the config option `show_stacktraces` to `True`
in the `cli` section of `~/.cumulusci/cumulusci.yml` and stacktraces
will no longer be suppressed when they are thrown within CumulusCI.
Usage Errors (wrong command line arguments, missing files, etc.)
will not show you exception tracebacks because they are seldom
helpful in that case.

