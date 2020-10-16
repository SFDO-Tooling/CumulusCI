Connect Persistent Orgs
=======================
In order to connect persistent orgs such as a Developer Edition, Enterprise Edition, or Sandbox org to CumulusCI, you first need to have a Connected App configured in a persistent Salesforce org.



CumulusCI's Connected App
-------------------------
CumulusCI comes with a connected app that you can deploy to any org in your ``sfdx`` keychain.
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
You may want to be ability to configure the connected app used by CumulusCI in a specific way.
If this is the case, you can use the ``cci task run connected_app`` command to create the connected app and then manually edit its configuration to your liking.

You can create a connected app with the label 'cumulusci' and connect it to CumulusCI with::

    $ cci task run connected_app --org <org_name> -o label cumulusci -o connect true

For a full list of options see the `connected_app <TODO>`_ task reference documentation.

After the connected app has been created you can verify that it is connected to CumulusCI by running ``cci service list``.
You can edit the connected app's OAuth scopes using the following steps:

#. In lightning, go to Setup --> Apps --> Apps Manager
#. Click the arrow on the far right side of the row that pertains to the newly created connected app.
#. Click "Edit"
#. Add or remove OAuth scopes as desired.


