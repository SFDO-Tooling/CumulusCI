Connect Persistent Orgs
=======================
Although working with scratch orgs is what we encourage with the `CumulusCI flow TODO`_, it is also sometimes necessary to connect CumulusCI to a persistent org.
CumulusCI stores OAuth credentials to these persistent org in the `CumulusCI keychain TDOO`_.
To connect to an org use the ``cci org connect <org_name>`` command. 

This command will open a browser window where you log into the org you want to connect to.
The ``<org_name>`` you specify in the command is the name CumulusCI will associate with the org.

Production or Developer Edition Orgs
------------------------------------
No options needed for these types of orgs.
Just provide the name you would like to associate with the connected org::

    $ cci org connect <org_name>

Sandboxes
---------
For sandboxes, pass the ``--sandbox`` flag::

    $ cci org connect <org_name> --sandbox

Global Orgs
-----------
Under some circumstances you may want a persistent org to be available across all CumulusCI projects on your computer.
By default, the ``cci org connect`` command stroes OAuth credentials in a *project specific* keychain.
This means that an org connected to Project A, will not be available to Project B.

You can connect and org and make it available to all CumulusCI projects on your computer with::

    $ cci org connect <org_name> --global-org

Verifying Connections
---------------------
You can use the ``cci org list`` command and look for your org under the "Connected Org" section.

The following shows a single persistent org connected to CumulusCI with the name "devhub".

.. image:: images/connected_org.png


You can use the ``cci org browser`` to ensure that CumulusCI is able to login to the connected org::

    $ cci org browser <org_name>



Use a Custom Connected App
--------------------------
