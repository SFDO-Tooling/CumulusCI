Manage Scratch Orgs
===================

Throughout this section, we'll focus on scratch org management in the CumulusCI keychain. To learn about managing persistent orgs, such as sandboxes, production orgs, and packaging orgs, read TODO: reference "Connecting persistent orgs".

What is an Org in CumulusCI?
---------------

CumulusCI takes a different approach to creating and using scratch orgs that aims to make the process easier, more portable, and more repeatable. CumulusCI's keychain tracks orgs as named, reproducible configurations, from which you can generate scratch orgs at need. An org in CumulusCI's keychain starts out as a configuration. The scratch org is only actually generated the first time you use the scratch org from the project keychain - and once it's expired or been deleted, a new one can easily be created with the same configuration.



Because org configurations are key to CumulusCI's scratch org strategy, let's start with what goes into an org configuration in CumulusCI. An org configuration has a name, such as ``dev`` or ``qa``, and is defined by options set in the project's ``cumulusci.yml`` or in the CumulusCI standard library, plus the contents of a specific ``.json`` scratch org definition file in the ``orgs`` directory.

These elements come together for a couple of reasons. One is that CumulusCI adds two facets to the org configuration that aren't part of the underlying Salesforce DX org configuration, which is the ``.json`` file in ``orgs``. Those facets are whether or not the org is namespaced, and how many days the org's lifespan is. The other reason is that CumulusCI makes it easy for you to build many named orgs that share the same configuration. Let's look at how that works.

In an out-of-the-box CumulusCI project, you might have a file called ``orgs/dev.json`` that looks like this:

.. code-block: json
    {
        "orgName": "Food-Bank-Demo - Dev Org",
        "edition": "Developer",
        "settings": {
            "lightningExperienceSettings": {
                "enableS1DesktopEnabled": true
            },
            "chatterSettings": {
                "enableChatter": true
            }
            /* more JSON configuration follows */
        }
    }

Then, the CumulusCI standard library (note: you won't see this in your project's ``cumulusci.yml``, because it's an out-of-the-box configuration), an ``orgs:`` entry is defined that uses this configuration file:

.. code-block: yaml
    orgs:
        scratch:
            dev:
                config_file: orgs/dev.json
                days: 7

This tells CumulusCI that we have an org configuration called ``dev``, which is built in Salesforce DX using the ``orgs/dev.json`` configuration file, which has a 7-day lifespan, and which is not namespaced. (If this org were namespaced, we'd have the key ``namespaced: True`` here; it defaults to ``False``).

An org configuration is also a name for an org that you can build by running a flow (we cover running flows in the next section). The flows that you run to build an org often, but not always, have a name that connects to the org configuration. For example, to run the ``dev_org`` flow against an org with the dev configuration, you can just do ::

    $ cci flow run dev_org --org dev

and CumulusCI will build the org for you. The org named ``dev`` has the configuration ``dev``, automatically.

You can create new org names that inherit their configuration from a built-in name. For example, to create a new org name that uses the same configuration as type ``dev``, you can use the command ::

    $ cci org scratch dev new-org

You can then run ::

    $ cci flow run dev_org --org new-org

to build this org, independent of the org dev but sharing its configuration. You can have as many named orgs as you wish, or none at all: many CumulusCI users work only with the built-in org names.

Your project may have other org shapes defined. ``cci org list`` will show you all of the built-in and custom orgs available for a project.

Set Up the Salesforce CLI
-------------------------

If you haven't already set up Salesforce DX, you need to take care of a few steps. For a detailed introduction to setting up Salesforce DX and Visual Studio Code to work with CumulusCI, we recommend completing `Build Applications with CumulusCI <https://trailhead.salesforce.com/en/content/learn/trails/build-applications-with-cumulusci>`_ on Trailhead.

1. `Install the Salesforce CLI <https://developer.salesforce.com/docs/atlas.en-us.sfdx_setup.meta/sfdx_setup/sfdx_setup_install_cli.htm>`_
2. `Enable Dev Hub in Your Org <https://developer.salesforce.com/docs/atlas.en-us.sfdx_setup.meta/sfdx_setup/sfdx_setup_enable_devhub.htm>`_
3. `Connect SFDX to Your Dev Hub Org <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_auth_web_flow.htm>`_ (be sure to use the ``--setdefaultdevhubusername`` option).

If you already have the ``sfdx`` command installed, have connected to your Dev Hub, and have set the ``defaultdevhubusername`` config setting (use ``sfdx force:config:list`` to verify), you're ready to start using CumulusCI with Salesforce DX.

You can learn more about Salesforce DX at https://developer.salesforce.com/platform/dx.


Predefined Orgs
---------------

CumulusCI comes with five org predefined org configurations, each of which is paired with a preferred flow to build that type of org:

* ``dev`` is for use with the ``dev_org`` flow and uses the ``orgs/dev.json`` configuration file. It has a seven-day lifespan.
* ``qa`` is for use with the ``qa_org`` flow. ``qa`` and ``dev`` are the same out of the box, but can be customized to suit the needs of the project. It has a seven-day lifespan.
* ``feature`` is for use in continuous integration with the ``ci_feature`` flow and uses the ``orgs/dev.json`` configuration file. It has a one-day lifespan.
* ``beta`` is for use in continuous integration or hands-on testing, with the ``ci_beta`` or ``install_beta`` flows. It uses the ``orgs/beta.json`` configuration. It has a one-day lifespan.
* ``release`` is for use in continuous integration, hands-on testing, or demo workflows, with the ``ci_release`` or ``install_prod`` flows. It uses the ``orgs/release.json`` configuration. It has a one-day lifespan.


Create a scratch org
--------------------



Implicit creation of scratch orgs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

List orgs
---------

When inside a project repository, you can see all the orgs you have configured or connected:

.. code-block:: console

    $ cci org list


Opening Orgs in the Browser
---------------------------

You can log into any org in the keychain in a new browser tab:

.. code-block:: console

    $ cci org browser <org_name>

Deleting Scratch Orgs
---------------------

If a scratch org in the keychain has actually created a scratch org, you can use ``cci org scratch_delete`` to delete the scratch org but leave the config to regenerate it in the keychain:

.. code-block:: console

    $ cci org scratch_delete feature-123

Using ``scratch_delete`` will not remove the feature-123 org from your org list.  This is the intended behavior, allowing you to easily recreate scratch orgs from a stored, standardized configuration.

If you want to permanently remove an org from the org list, you can use ``cci org remove`` which will completely remove the org from the list.  If the a scratch org has already been created from the config, an attempt to delete the scratch org will be made before removing the org from the keychain:

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

To remove an existing default, run the command

.. code-block:: console

    $ cci org default dev --unset

Add a Predefined Org
--------------------

Projects may choose to add more orgs by adding entries to their ``orgs:`` section in ``cumulusci.yml`` and, optionally, creating further configuration files in the ``orgs`` directory. For example, many projects offer a ``dev_namespaced`` org, a developer org that has a namespace. This org is defined like this in ``cumulusci.yml``: ::

    orgs:
        scratch:
            dev_namespaced:
                config_file: orgs/dev.json
                days: 7
                namespaced: True

This org uses the same SFDX configuration file as the ``dev`` org, but has different configuration in ``cumulusci.yml``, resulting in a different org shape and a different use case.

Many projects never need to add a new org definition ``.json`` file, simply modifying the files that are shipped with CumulusCI. However, new definitions can be added and referenced in the ``scratch:`` section of ``cumulusci.yml`` to establish org configurations that are completely bespoke to a project.

Import an org from the Salesforce CLI
-------------------------------------

CumulusCI can import existing orgs from the Salesforce DX keychain. To import a scratch org from Salesforce DX, run

.. code-block:: console

    $ cci org import sfdx_alias cci_alias

For ``sfdx_alias``, you can specify the alias or username of the org in the SFDX keychain. For ``cci_alias``, provide the name you'd like to use in CumulusCI's keychain.

Note that CumulusCI cannot automatically refresh orgs imported from Salesforce DX when they expire.

Use a non-default Dev Hub
-------------------------

By default, CumulusCI will create scratch orgs using the Dev Hub org that is configured as the ``defaultdevhubusername`` in ``sfdx``. You can switch to a different Dev Hub org within a particular project by configuring the ``devhub`` service:

.. code-block: console

    $ cci service connect devhub --project
    Username: [type the Dev Hub username here]
    devhub is now configured for this project.

