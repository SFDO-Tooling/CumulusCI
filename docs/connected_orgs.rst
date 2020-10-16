Connect Persistent Orgs
=======================
In order to connect persistent orgs such as a Developer Edition, Enterprise Edition, or Sandbox org to CumulusCI, you first need to have a Connected App configured in a persistent Salesforce org.



The ``org connect`` Command
---------------------------
To connect to a persistent org use::

    $ cci org connect <org_name>

This will automatically open a browser window pointed to a Salesforce login page.
The provided ``<org_name>`` will be the name that CumulusCI associates with org you log into.

If you're connecting to a sandbox use the ``--sandbox`` flag.

By default, ``cci org connect`` stores the OAuth credentials for connected orgs in a *project-specific* keychain.
This means that an org connected while working in Project A's repository, will not be available while working in Project B's repository.
If you would like to make the org available to *all* CumulusCI projects use the ``--global`` flag.

.. note::
    Connecting an org via ``cci org connect`` does *not* expose that org to ``SFDX``.


Verify Your Connected Orgs
--------------------------
You can use ``cci org list`` to look for your org listed under the "Connected Org" table.

The following shows a single persistent org connected to CumulusCI with the name "devhub".

.. image:: images/connected_org.png


You can use ``cci org browser`` to ensure that CumulusCI is able to login to the connected org::

    $ cci org browser <org_name>



CumulusCI's Connected App
-------------------------
CumulusCI comes with a Connected App that you can deploy to any org in your ``sfdx`` keychain.
By default, this this deploy to the org configured as the ``defaultdevhubusername``::
Use the following to deploy the CumulusCI's Connected App to an org::

    $ cci task run connected_app

This command also takes care to setup CumulusCI's ``connected_app`` service in the keychain for you.
If you want to see the information for the Connected App, you can view it with::

    $ cci service info connected_app



Using a Custom Connected App
----------------------------
Most users never need to work with Connected Apps because CumulusCI's out-of-the-box Connected App covers most use cases.
If you need to control the Connected App that CumulusCI uses to authenticate for your specific security of compliance requirements, you can create your own Connected App and configure CumulusCI to use it when connecting to orgs.

To create a custom Connected App, use the ``connected_app`` task to create the Connected App and then manually edit its configuration to suit your requirements. Make sure to create the Connected App in a persistent org other than a sandbox.
You can create a Connected App with the label 'cumulusci' and automatically set it as the ``connected_app`` service in CumulusCI with::

    $ cci task run connected_app --org <org_name> -o label cumulusci -o connect true

For a full list of options see the `connected_app <TODO>`_ task reference documentation.

After the Connected App has been created you can verify that it is connected to CumulusCI by running ``cci service list``.
You can edit the Connected App's OAuth scopes using the following steps:

#. In Lightning Experience, go to Setup --> Apps --> Apps Manager
#. Click the arrow on the far right side of the row that pertains to the newly created Connected App.
#. Click "Edit"
#. Add or remove OAuth scopes as desired.


