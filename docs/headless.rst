Run CumulusCI Headlessly
========================

CumulusCI can be used to run continuous integration builds in your CI system.

This section outlines how to setup services and orgs that can be defined in
a particular environment such that they will be recognized by CumulusCI.

Register Environment Services
------------------------------
It is often the case that services you use for local development
will differ from the services that you want to use in your build system.
For example, devlopers will setup a GitHub service locally that is associated
with their GitHub User, while an integration build may want to run as 
an integration user when interacting with GitHub. By providing environment
variables with specific prefixes, CumulusCI can detect 
and register those services for use when running tasks and flows. 

Name Environment Services
*************************
Environment variables that define CumulusCI services adhere to the following format:

.. code:: console

	CUMULUSCI_SERVICE_<service_type>[__service_name]

All services should start with the prefix ``CUMULUSCI_SERVICE_`` followed 
immediately by the ``service_type`` (for a full list of available services
run ``cci service list``). Additionally, you have the option to provide a
unique name for your service by adding a double underscore (``__``) followed
by the name you wish to use. If a name is specified it is prepended with 
"env-" to help establish that this service is coming from the environment.
If a name is not specified, a defualt name of ``env`` is used for that service.

Here are some examples of environment variable names along with their
corresponding service types and names:

* ``CUMULUSCI_SERVICE_github`` --> A ``github`` service that will have the default name of ``env``
* ``CUMULUSCI_SERVICE_github__integration-user`` --> A ``github`` service that will have the name ``env-integration-user``
* ``CUMULUSCI_SERVICE_connected_app`` --> A ``connected_app`` service with the default name of ``env``
* ``CUMULUSCI_SERVICE_connected_app__sandbox`` --> A ``connected_app`` service with the name ``env-sandbox``

By always prepending `env` to the names of services specified by environment variables,
it is easy to see which services are currently set by environment variables and which are not.

Environment Service Values
***************************
The value of the environment variables (i.e. everything that comes after the ``=`` character) are provided
in the form of a JSON string. The following shows an example that defines a github service via an environment variable:

.. code-block:: console

  CUMULUSCI_SERVICE_github='{"username":"jdoe","email":"jane.doe@some.biz", "token":"<personal_access_token>"}'

These values provide CumulusCI with the required attributes for a particular service. The
easiest way to find what attributes are needed for a particular service is
to look for your service under the `services tag in the CumulusCI standard library <https://github.com/SFDO-Tooling/CumulusCI/blob/34533b4a1caa3f1850c64e223ece26069c83b60e/cumulusci/cumulusci.yml#L1164>`_
and provide values for all "attributes" listed under the desired service.

For example, if you're looking to register a ``connected_app`` service,
then the attributes: ``callback_url``, ``client_id``, and ``client_secret``
would need to be provided in the following format:

.. code-block:: json

	'{"callback_url": "<callback_url>", "client_id": "<client_id>", "client_secret": "<client_secret>"}'

.. note:

	The values ``<callback_url>``, ``<client_id>``, and ``<client_secret>`` should all be replaced with actual values.



Register Persistent Orgs
------------------------
Certain builds may require working with one or more persistent orgs.
Using the JWT flow for authentication is the recommended approach when running
CumulusCI headlessly for continuous integration with an existing org.

First, you need a Connected App that is configured with a certificate in the
"Use digital signatures" setting in its OAuth settings. You can follow the Salesforce
DX Developer Guide to get this set up:

* `Create a private key and self-signed certificate <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_auth_key_and_cert.htm>`_
* `Create a Connected App <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_auth_connected_app.htm>`_

Once you have a Connected App created, you can configure CumulusCI to use this Connected
App to login to a persistent org by setting the following environment variables.

* ``CUMULUSCI_ORG_orgName``
* ``SFDX_CLIENT_ID``
* ``SFDX_HUB_KEY``

See the below entries for the values to use with each.

.. important::

  Setting the above environment variables negates the need to use the ``cci org connect`` command.
  You can simply run a ``cci`` command and pass the ``--org orgName`` option, where ``orgName``
  corresponds to the name used in the ``CUMULUSCI_ORG_*`` environment variable.

In the context of GitHub Actions, all of these environment variables would be declared under the ``env`` section of a workflow.
Below is an example of what this would look like:

.. code-block:: yaml

    env:
        CUMULUSCI_ORG_sandbox: {"username": "just.in@salesforce.org", "instance_url": "https://sfdo--sbxname.my.salesforce.com"}
        SFDX_CLIENT_ID: {{ $secrets.client_id }}
        SFDX_HUB_KEY: {{ $secrets.server_key }}


The above assumes that you have ``client_id`` and ``server_key`` setup in your GitHub
`encrypted secrets <https://docs.github.com/en/free-pro-team@latest/actions/reference/encrypted-secrets>`_


``CUMULUSCI_ORG_orgName``
^^^^^^^^^^^^^^^^^^^^^^^^^
The name of this environment variable defines what name to use for the value of the ``--org`` option. 
For example, a value of ``CUMULUSCI_ORG_mySandbox`` would mean you use ``--org mySandbox`` to use this org in a ``cci`` command.

Set this variable equal to the following json string:

.. code-block:: JSON
  
    {
        "username": "USERNAME",
        "instance_url": "INSTANCE_URL"
    }

* ``USERNAME`` - The username of the user who will login to the target org.
* ``INSTANCE_URL`` - The instance URL for the org. Should begin with the ``https://`` schema.

You can see an example of setting this environment variable in a GitHub actions workflow in our `demo repository <https://github.com/SFDO-Tooling/CumulusCI-CI-Demo/blob/404c5114dac8afd3747963d5abf63be774e61757/.github/workflows/main.yml#L11>`_.

.. admonition:: Wizard Note

  If the target org's instance URL is instanceless (i.e. does not contain a segment like 
  cs46 identifying the instance), then for sandboxes it is also necessary to set 
  ``SFDX_AUDIENCE_URL`` to ``https://test.salesforce.com"``. This instructs CumulusCI to set
  the correct ``aud`` value in the JWT (which is normally determined from the instance URL).



``SFDX_CLIENT_ID``
^^^^^^^^^^^^^^^^^^^^^^
Set this to your Connected App's client id.
This, combined with the ``SFDX_HUB_KEY`` variable instructs CumulusCI to authenticate
to the org using the `JWT Bearer Flow <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_auth_jwt_flow.htm#sfdx_dev_auth_jwt_flow>`_ instead
of the `Web Server Flow <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_auth_web_flow.htm#!>`_.



``SFDX_HUB_KEY``
^^^^^^^^^^^^^^^^
Set this to the private key associated with your Connected App (this is the contents of your ``server.key`` file).
This combined with the ``SFDX_CLIENT_ID`` variable instructs CumulusCI to authenticate
to the org using the `JWT Bearer Flow <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_auth_jwt_flow.htm#sfdx_dev_auth_jwt_flow>`_ instead
of the `Web Server Flow <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_auth_web_flow.htm#!>`_.



Multiple Services of the Same Type
----------------------------------
In rare cases a build may need to utilize multiple services of the same type.
To set a specific service as the default for subsequent tasks/flows run the
``cci service default <service_type> <name>`` command. You can run this 
command again to set a new default service to be used for the given service type.
