Connect Persistent Orgs
=======================
In order to connect persistent orgs such as a Developer Edition, Enterprise Edition, or Sandbox org to CumulusCI, you first need to have a Connected App configured in a persistent Salesforce org.



CumulusCI's Connected App
-------------------------
CumulusCI already has a connected app that you can deploy to any org in your ``sfdx`` keychain.
By default, this this deploy to the org configured as the ``defaultdevhubusername``::
Use the following to deploy the CumulusCI's connected app to an org::

    $ cci task run connected_app

This command also takes care to setup CumulusCI's ``connected_app`` service in the keychain for you.
If you want to see the information for the connected app, you can view it with::

    $ cci service info connected_app




The ``org connect`` Command
---------------------------
To connect to a persistent org use::

    $ cci org connect <org_name>

This will automatically open a browser window pointed to a Salesforce login page.
The provided ``<org_name>`` will be the name that CumulusCI associates with org you log into.



Production and Developer Edition Orgs
*******************************************
No options needed for these org types, just use::

    $ cci org connect <org_name>



Sandboxes
********************
For sandboxes, pass the ``--sandbox`` flag along with the org name::

    $ cci org connect <org_name> --sandbox



Global Orgs
*******************
By default, ``cci org connect`` stores the OAuth credentials for connected orgs in a *project specific* keychain.
This means that an org connected while working in Project A's directory, will not be available while working in Project B's directory.

You can connect an org and make it available to *all* CumulusCI projects on your computer with::

    $ cci org connect <org_name> --global-org



Verifying Connections
---------------------
You can use ``cci org list`` to look for your org listed under the "Connected Org" table.

The following shows a single persistent org connected to CumulusCI with the name "devhub".

.. image:: images/connected_org.png


You can use ``cci org browser`` to ensure that CumulusCI is able to login to the connected org::

    $ cci org browser <org_name>


Using a Custom Connected App
----------------------------
Under special circumstances you may want to use your own connected app instead of the one provided by CumulusCI.
