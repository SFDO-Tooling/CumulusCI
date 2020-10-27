Connect Persistent Orgs
=======================
In addition to creating `scratch orgs <TODO>`_, you can connect persistent orgs to your CumulusCI project so that you can run tasks and flows on them.
This supports use cases such as deploying to a Developer Edition org in order to release a package version, or installing to a sandbox for user acceptance testing.

.. note::
    Different setup is required if you are looking to connect to orgs in the context of an automated build. 
    Please see the `continuous integration <TODO>`_ section for more information.



The ``org connect`` Command
---------------------------
To connect to a persistent org use::

    $ cci org connect <org_name>

This will automatically open a browser window pointed to a Salesforce login page.
The provided ``<org_name>`` will be the name that CumulusCI associates with org you log into.

.. note::
    Connecting an org via ``cci org connect`` does *not* expose that org to the Salesforce CLI.

If your org has a custom domain, you can pass in the the `--login-url` option along with the orgs login url.

.. code-block:: console

    cci org connect <org_name> --login-url https://example.my.domain.salesforce.com



Production and Developer Edition Orgs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
No options needed for these org types, just use::

    $ cci org connect <org_name>



Sandboxes
^^^^^^^^^
For sandboxes, pass the ``--sandbox`` flag along with the org name::

    $ cci org connect <org_name> --sandbox

.. note::
    The ``--sandbox`` flag can also be used for connecting a scratch org created externally to CumulusCI.

Verify Your Connected Orgs
--------------------------
You can use ``cci org list`` to look for your org listed under the "Connected Org" table.

The following shows a single persistent org connected to CumulusCI with the name "devhub".

.. code-block:: yaml

    $ cci org list

    ┌Scratch Orgs───────────────────┬─────────┬──────┬─────────┬──────────────┬────────┐
    │ Name                          │ Default │ Days │ Expired │ Config       │ Domain │
    ├───────────────────────────────┼─────────┼──────┼─────────┼──────────────┼────────┤
    │ dev                           │         │ 7    │ ✘       │ dev          │        │
    ├───────────────────────────────┼─────────┼──────┼─────────┼──────────────┼────────┤
    │ feature                       │         │ 1    │ ✘       │ feature      │        │
    ├───────────────────────────────┼─────────┼──────┼─────────┼──────────────┼────────┤
    │ prerelease                    │         │ 1    │ ✘       │ prerelease   │        │
    ├───────────────────────────────┼─────────┼──────┼─────────┼──────────────┼────────┤
    │ qa                            │         │ 7    │ ✘       │ qa           │        │
    ├───────────────────────────────┼─────────┼──────┼─────────┼──────────────┼────────┤
    │ release                       │         │ 1    │ ✘       │ release      │        │
    ├───────────────────────────────┼─────────┼──────┼─────────┼──────────────┼────────┤

    ┌Connected Orgs────┬──────────────────────────────┬────────────┐
    │ Name   │ Default │ Username                     │ Expires    │
    ├────────┼─────────┼──────────────────────────────┼────────────┤
    │ devhub │         │ peter.gibbons@initech.devhub │ Persistent │
    └────────┴─────────┴──────────────────────────────┴────────────┘

You can use ``cci org browser`` to ensure that CumulusCI is able to login to the connected org::

    $ cci org browser <org_name>



Global Orgs
-----------
By default, ``cci org connect`` stores the OAuth credentials for connected orgs in a *project specific* keychain.
This means that an org connected while working in Project A's directory, will not be available while working in Project B's directory.

You can connect an org and make it available to *all* CumulusCI projects on your computer by passing the ``--global-org`` flag::

    $ cci org connect <org_name> --global-org



Using a Custom Connected App
----------------------------
CumulusCI uses a preconfigured Connected App to authenticate to Salesforce orgs using OAuth2.
In most cases this works fine.
If you need to control the Connected App that CumulusCI uses to authenticate for your specific security or compliance requirements, you can create your own Connected App and configure CumulusCI to use it when connecting to orgs.

To create a custom Connected App, use the ``connected_app`` task to create the Connected App and then manually edit its configuration to suit your requirements. Make sure to create the Connected App in a persistent org other than a sandbox.
You can create a Connected App in the devhub org connected to ``SFDX`` with the label 'cumulusci' and automatically set it as the ``connected_app`` service in CumulusCI with::

    $ cci task run connected_app -o label cumulusci -o connect true

For a full list of options see the `connected_app <TODO>`_ task reference documentation.

After the Connected App has been created you can verify that it is connected to CumulusCI by running ``cci service list``.
You can edit the Connected App's OAuth scopes using the following steps:

#. In Lightning Experience, go to Setup --> Apps --> Apps Manager
#. Click the arrow on the far right side of the row that pertains to the newly created Connected App.
#. Click "Edit"
#. Add or remove OAuth scopes as desired.


