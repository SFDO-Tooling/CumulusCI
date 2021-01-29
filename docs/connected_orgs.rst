Connect Persistent Orgs
=======================

In addition to creating `scratch orgs<TODO>`_, you can connect persistent orgs to your CumulusCI project to run tasks and flows on them. Connecting persistent orgs supports use cases such as deploying to a Developer Edition org to release a package version, or installing to a sandbox for user acceptance testing.

.. note:: A different setup is required to connect to orgs in the context of an automated build. See `continuous integration<TODO>`_ for more information.



The ``org connect`` Command
---------------------------

To connect to a persistent org:

.. code-block:: console

    $ cci org connect <org_name>

This command automatically opens a browser window pointed to a Salesforce login page. The provided ``<org_name>`` is the name that CumulusCI associates which org you log into.

.. note::
    Connecting an org via ``cci org connect`` does *not* expose that org to the Salesforce CLI.

If your org has a custom domain, use the ``--login-url`` option along with the org's login url.

.. code-block:: console

    cci org connect <org_name> --login-url https://example.my.domain.salesforce.com


Production and Developer Edition Orgs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

No options are needed for these org types. Just run the same command you normally would to connect to a persistent org.

.. code-block:: console

    $ cci org connect <org_name>

Sandboxes
^^^^^^^^^
For sandboxes, pass the ``--sandbox`` flag along with the org name.

.. code-block:: console

    $ cci org connect <org_name> --sandbox

.. note:: The ``--sandbox`` flag can also be used for connecting a scratch org created externally to CumulusCI.

Verify Your Connected Orgs
--------------------------

Run ``cci org list`` to see your org listed under the "Connected Org" table.

    Example: A single persistent org connected to CumulusCI with the name ``devhub``.

.. code-block:: yaml

    $ cci org list

    ┌Scratch Orgs──────────────┬─────────┬──────┬─────────┬──────────────┬────────┐
    │ Name                     │ Default │ Days │ Expired │ Config       │ Domain │
    ├──────────────────────────┼─────────┼──────┼─────────┼──────────────┼────────┤
    │ dev                      │         │ 7    │ X       | dev          │        │
    ├──────────────────────────┼─────────┼──────┼─────────┼──────────────┼────────┤
    │ feature                  │         │ 1    │ X       | feature      │        │
    ├──────────────────────────┼─────────┼──────┼─────────┼──────────────┼────────┤
    │ prerelease               │         │ 1    │ X       | prerelease   │        │
    ├──────────────────────────┼─────────┼──────┼─────────┼──────────────┼────────┤
    │ qa                       │         │ 7    │ X       | qa           │        │
    ├──────────────────────────┼─────────┼──────┼─────────┼──────────────┼────────┤
    │ release                  │         │ 1    │ X       | release      │        │
    ├──────────────────────────┼─────────┼──────┼─────────┼──────────────┼────────┤

    ┌Connected Orgs────┬──────────────────────────────┬────────────┐
    │ Name   │ Default │ Username                     │ Expires    │
    ├────────┼─────────┼──────────────────────────────┼────────────┤
    │ devhub │         │ peter.gibbons@initech.devhub │ Persistent │
    └────────┴─────────┴──────────────────────────────┴────────────┘

Make sure that CumulusCI can login to the connected org.

.. code-block:: console

    $ cci org browser <org_name>



Global Orgs
-----------
By default, ``cci org connect`` stores the OAuth credentials for connected orgs in a *project specific* keychain. These credentials ensure that an org connected in Project A's directory isn't available when you're working in Project B's directory.

Connect an org and make it available to *all* CumulusCI projects on your computer by passing the ``--global-org`` flag.

.. code-block:: console

    $ cci org connect <org_name> --global-org



Use a Custom Connected App
----------------------------
CumulusCI uses a preconfigured Connected App to authenticate to Salesforce orgs that use OAuth2. In most cases this works fine. To control the Connected App for specific security or compliance requirements, create your own Connected App and configure CumulusCI to use it when connecting to orgs.

To create a custom Connected App, run the ``connected_app`` task to create the Connected App and then manually edit its configuration to suit your requirements. Make sure to create the Connected App in a persistent org other than a sandbox. You can create a Connected App in the DevHub org connected to ``SFDX`` with the label ``cumulusci`` and automatically set it as the ``connected_app`` service in CumulusCI.

.. code-block:: console

    $ cci task run connected_app -o label cumulusci -o connect true

For a full list of options see the `connected_app<TODO>`_ task reference documentation.

After the Connected App has been created, verify that it's connected to CumulusCI with ``cci service list``.

To edit the Connected App's OAuth scopes:

#. In Lightning Experience, go to Setup --> Apps --> Apps Manager.
#. Click the arrow on the far right side of the row that pertains to the newly created Connected App.
#. Click "Edit."
#. Add or remove OAuth scopes as desired.
