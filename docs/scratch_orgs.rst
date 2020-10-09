Manage Scratch Orgs
===================

Scratch orgs are temporary Salesforce orgs which can be quickly set up "from scratch" and which last for a limited time (no more than 30 days). We strongly encourage using scratch orgs for development and testing, instead of sandboxes or Developer Edition orgs, because:

* Scratch orgs provide a repeatable starting point without challenge of managing persistent orgs' state over time.
* Scratch orgs are scalable and ensure individual, customized environments are available to everyone in the development lifecycle.
* Scratch orgs facilitate a fully source-driven development process built around best practices.

The CumulusCI Suite offers tools for working with all types of Salesforce orgs, but provides the most value when working with scratch orgs. CumulusCI automation helps realize the promise of scratch orgs as low cost, repeatable, source-driven environments for every phase of the product lifecycle.

Throughout this section, we'll focus on managing scratch orgs in a CumulusCI project. To learn about managing persistent orgs, such as sandboxes, production orgs, and packaging orgs, read TODO: reference "Connecting persistent orgs".

What is an Org in CumulusCI?
----------------------------

CumulusCI takes an approach to creating and using scratch orgs that aims to make the process easy, portable, and repeatable. An org in CumulusCI's keychain starts out as a named configuration, tailored for a specific purpose within the lifecycle of the project. The scratch org is only actually generated the first time you use the scratch org - and once it's expired or been deleted, a new one can easily be created with the same configuration.

CumulusCI offers tools that make it easy to discover predefined org configurations, create scratch orgs based on those configurations, and define new orgs and new configurations.

Set Up the Salesforce CLI
-------------------------

If you haven't already set up the Salesforce CLI, you need to take care of a few steps. For a detailed introduction to setting up Salesforce CLI and Visual Studio Code to work with CumulusCI, we recommend completing `Build Applications with CumulusCI <https://trailhead.salesforce.com/en/content/learn/trails/build-applications-with-cumulusci>`_ on Trailhead.

1. `Install the Salesforce CLI <https://developer.salesforce.com/docs/atlas.en-us.sfdx_setup.meta/sfdx_setup/sfdx_setup_install_cli.htm>`_
2. `Enable Dev Hub in Your Org <https://developer.salesforce.com/docs/atlas.en-us.sfdx_setup.meta/sfdx_setup/sfdx_setup_enable_devhub.htm>`_
3. `Connect SFDX to Your Dev Hub Org <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_auth_web_flow.htm>`_ (be sure to use the ``--setdefaultdevhubusername`` option).

If you already have the ``sfdx`` command installed, have connected to your Dev Hub, and have set the ``defaultdevhubusername`` config setting (use ``sfdx force:org:list`` to verify; the default Dev Hub will be listed with a ``(D)``), you're ready to start using CumulusCI with Salesforce CLI.

See Also
^^^^^^^^

* `Learn more about the Salesforce CLI <https://developer.salesforce.com/platform/dx>`_.

Predefined Orgs
---------------

CumulusCI comes with five predefined org configurations. Every org's keychain starts with these configurations available and ready to be turned into a live scratch org. You can see the predefined org configurations in your project by running

.. code-block:: console

    $ cci org list

* ``dev`` is for development workflows and uses the ``orgs/dev.json`` configuration file. It has a seven-day lifespan.
* ``qa`` is for testing workflows. ``qa`` and ``dev`` are the same out of the box, but can be customized to suit the needs of the project. It has a seven-day lifespan.
* ``feature`` is for use in continuous integration and uses the ``orgs/dev.json`` configuration file. It has a one-day lifespan.
* ``beta`` is for use in continuous integration or hands-on testing. It uses the ``orgs/beta.json`` configuration. It has a one-day lifespan.
* ``release`` is for use in continuous integration, hands-on testing, or demo workflow. It uses the ``orgs/release.json`` configuration. It has a one-day lifespan.

If your project has customized the available orgs, you'll see more orgs, or differences in configuration, compared to a brand-new project.

Create a Scratch Org
--------------------

To create a scratch org from a configuration, simply use it as the target of a CumulusCI command, task, or flow. CumulusCI automatically initializes orgs when they're first used. To create a scratch org from the ``dev`` configuration and review information about the created org, run

.. code-block:: console

    $ cci org info dev

Once the org is created, it's associated with the name ``dev`` in the CumulusCI keychain and can be used with other commands until it expires. Once an org expires or is removed, its associated configuration is left in place, and can be recreated whenever needed.

You can create new orgs in the keychain that inherit their configuration from a built-in org. For example, to create a new org name that uses the same configuration as type ``dev``, you can use the command ::

    $ cci org scratch dev new-org

You can then run ::

    $ cci org info new-org

to create this scratch org, independent of the org ``dev`` but sharing its configuration. You can have as many named orgs as you wish, or none at all: many CumulusCI users work only with the built-in orgs.

Scratch Org Limits
^^^^^^^^^^^^^^^^^^

Each scratch org you create is counted against limits in your Dev Hub. Scratch orgs count against an active scratch org limit, which controls how many orgs you can have at the same time, and a daily scratch org limit, which controls how many total orgs you can create per day.

Scratch org limits are based on your Dev Hub's edition and your Salesforce contract. To review limits and consumption, run the command

.. code-block:: console

    $ sfdx force:limits:api:display -u <username>

where  ``<username>`` is your Dev Hub username. The limit names are ``ActiveScratchOrgs`` and ``DailyScratchOrgs``.

List Orgs
---------

When inside a project repository, you can see all the orgs you have configured or connected:

.. code-block:: console

    $ cci org list


Opening Orgs in the Browser
---------------------------

You can log into any org in the keychain in a new browser tab:

.. code-block:: console

    $ cci org browser <org_name>

Delete Scratch Orgs
-------------------

If an org defined in the keychain has created a scratch org, you can use ``cci org scratch_delete`` to delete the scratch org but leave the configuration to regenerate it in the keychain:

.. code-block:: console

    $ cci org scratch_delete feature-123

Using ``scratch_delete`` will not remove the feature-123 org from your org list.  This is the intended behavior, allowing you to easily recreate scratch orgs from a stored, standardized configuration.

If you want to permanently remove an org from the org list, you can use ``cci org remove`` which will completely remove the org from the list.  If a scratch org has already been created from the config, the associated scratch org will also be deleted.

.. code-block:: console

    $ cci org remove feature-123

It's not necessary to explicitly remove or delete expired orgs. CumulusCI will recreate an expired org the first time you attempt to use it. To clean up expired orgs from the keychain, you can use the ``cci org prune`` command:

.. code-block:: console

    $ cci org prune

Set a Default Org
-----------------

When you run a Flow or Task that performs work on an org, you specify the org with a ``--org <name>`` option:

.. code-block:: console

    $ cci flow run dev_org --org dev

If you're running many commands against the same org, you may wish to set a default:

.. code-block:: console

    $ cci org default dev
    $ cci flow run dev_org

Alternately, you can set a default org when you create a new named configuration:

.. code-block:: console

    $ cci org scratch dev new-org --default

To remove an existing default, run the command

.. code-block:: console

    $ cci org default dev --unset

Configure Predefined Orgs
-------------------------

Projects may choose to customize the set of five configurations available out of the box, and may add further predefined orgs to meet project-specific needs. 

An org configuration has a name, such as ``dev`` or ``qa``, and is defined by options set in ``cumulusci.yml``, plus the contents of a specific ``.json`` scratch org definition file in the ``orgs`` directory. For orgs like ``dev`` and ``qa`` that are predefined for all projects, the configuration is located in the CumulusCI standard library, but can be customized by projects in ``cumulusci.yml``.

Many projects that build managed packages offer a ``dev_namespaced`` org, a developer org that has a namespace. This org is defined like this in ``cumulusci.yml``:

.. code-block:: yaml

    orgs:
        scratch:
            dev_namespaced:
                config_file: orgs/dev.json
                days: 7
                namespaced: True

This org uses the same Salesforce DX configuration file as the ``dev`` org, but has different configuration in ``cumulusci.yml``, resulting in a different org shape and a different use case. The key facets of the org shape that are defined in ``cumulusci.yml`` are whether or not the org has a namespace and the length of the org's lifespan. 

Org definition files stored in the ``orgs`` directory are configured as in the `Salesforce DX Developer Guide <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_scratch_orgs_def_file.htm>`_.

Many projects never need to add a new org definition ``.json`` file, simply modifying the files that are shipped with CumulusCI to add specific features and settings. However, new definitions can be added and referenced in the ``scratch:`` section of ``cumulusci.yml`` to establish org configurations that are completely customized for a project.


Import an Org from the Salesforce CLI
-------------------------------------

CumulusCI can import existing orgs from the Salesforce CLI keychain. To import a scratch org from Salesforce CLI, run

.. code-block:: console

    $ cci org import sfdx_alias cci_alias

For ``sfdx_alias``, you can specify the alias or username of the org in the Salesforce CLI keychain. For ``cci_alias``, provide the name you'd like to use in CumulusCI's keychain.

Note that CumulusCI cannot automatically refresh orgs imported from Salesforce CLI when they expire.

Use a Non-Default Dev Hub
-------------------------

By default, CumulusCI will create scratch orgs using the Dev Hub org that is configured as the ``defaultdevhubusername`` in ``sfdx``. You can switch to a different Dev Hub org within a particular project by configuring the ``devhub`` service:

.. code-block:: console

    $ cci service connect devhub --project
    Username: [type the Dev Hub username here]
    devhub is now configured for this project.
