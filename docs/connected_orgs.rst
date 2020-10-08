Connect Persistent Orgs
=======================
In order to connect persistent orgs such as a Developer Edition, Enterprise Edition, or Sandbox org to CumulusCI, you first need to have a Connected App configured in a persistent Salesforce org.



Create a Connected App
-----------------------
You can choose whether to create the Connected App from the command line or via the Salesforce Setup menu.



ce has a default Connected App that CumulusCI can deploy to any org in your ``sfdx`` keychain.
CumulusCI includes a task to easily deploy the default Salesforce Connected App to any org in your ``sfdx`` keychain.
By default, this will deploy to the org configured as the ``defaultdevhubusername``::

    $ cci task run connected_app

This command will also configure CumulusCI's ``connected_app`` service in the keychain for you.
If you want to see hte information for the connected app, you can view it with::

    $ cci service info connected_app



Create via Salesforce Setup
******************************

The ``connect`` Command
-----------------------
To connect to a persistent org use the following::

    $ cci org connect <org_name>

This will automatically open a browser window pointed to a Salesforce login page.
The provided ``<org_name>`` will be the name that CumulusCI associates with your connected org.



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
Under some circumstances you may want a persistent org to be available across all CumulusCI projects on your computer.
By default, ``cci org connect`` stores the OAuth credentials for connected orgs in a *project specific* keychain.
This means that an org connected while working in Project A's directory, will not be available while working in Project B's directory.

You can connect and org and make it available to all CumulusCI projects on your computer with::

    $ cci org connect <org_name> --global-org



Verifying Connections
---------------------
You can use the ``cci org list`` command and look for your org under the "Connected Org" section.

The following shows a single persistent org connected to CumulusCI with the name "devhub".

.. image:: images/connected_org.png


You can use ``cci org browser`` to ensure that CumulusCI is able to login to the connected org::

    $ cci org browser <org_name>


Using a Custom Connected App
----------------------------

