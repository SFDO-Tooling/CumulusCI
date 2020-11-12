.. _GitHub Actions:

Run CumulusCI from Github Actions
=================================
In order to follow along, you should already have a repository that is
hosted on GitHub and configured as a CumulusCI project. In other words,
we're assuming your project already has a ``cumulusci.yml`` and that you are
successfully running CumulusCI flows locally.

.. note::
   GitHub Actions is free for open source (public) repositories.
   Check with GitHub about pricing for private repositories.



Create a GitHub Action Workflow
-------------------------------
In GitHub Actions, you can define *workflows* which run 
automatically in response to events in the repository.
We're going to create an action called ``Apex Tests`` 
which runs whenever commits are pushed to GitHub.

Workflows are defined using files in YAML format in the
``.github/workflows`` folder within the repository. To set up the Apex
Tests workflow, use your editor to create a file named
``apex_tests.yml`` in this folder and add the following contents:

.. code-block:: yaml

   name: Apex Tests

   on: [push]

   env:
     CUMULUSCI_KEYCHAIN_CLASS: cumulusci.core.keychain.EnvironmentProjectKeychain
     CUMULUSCI_SERVICE_github: ${{ secrets.CUMULUSCI_SERVICE_github }}

   jobs:
     unit_tests:
       name: "Run Apex tests"
       runs-on: ubuntu-latest
       steps:
       - uses: actions/checkout@v2
       - name: Install sfdx
         run: |
           mkdir sfdx
           wget -qO- https://developer.salesforce.com/media/salesforce-cli/sfdx-linux-amd64.tar.xz | tar xJ -C sfdx --strip-components 1
           ./sfdx/install
           echo ${{ secrets.SFDX_AUTH_URL }} > sfdx_auth
           sfdx force:auth:sfdxurl:store -f sfdx_auth -d
       - name: Set up Python
         uses: actions/setup-python@v1
         with:
           python-version: "3.8"
       - name: Install CumulusCI
         run: |
           python -m pip install -U pip
           pip install cumulusci
       - run: |
           cci flow run ci_feature --org dev --delete-org

This workflow defines a *job* named ``Run Apex Tests`` which will run
these steps in the CI environment after any commits are pushed:

#.  Check out the repository at the commit that was pushed
#.  Install the Salesforce CLI and authorize a Dev Hub user
#.  Install Python 3.8 and CumulusCI
#.  Run the ``ci_feature`` flow in CumulusCI in the ``dev`` scratch org,
    and then delete the org. The ``ci_feature`` flow deploys the package
    and then runs its Apex tests.

It also configures CumulusCI to use a special keychain, the
``EnvironmentProjectKeychain``, which will load org and service
configuration from environment variables instead of from files.



Configure Secrets
-----------------
You may have noticed that the workflow refers to a couple of "secrets":
``CUMULUSCI_SERVICE_github`` and ``SFDX_AUTH_URL``. You need to add
these secrets to the repository settings before you can use this
workflow.

To find the settings for Secrets, open your repository in GitHub. Click
the Settings tab. Then click the Secrets link on the left.



``CUMULUSCI_SERVICE_github``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
CumulusCI may need access to the GitHub API in order to do things like
look up information about dependency packages. To set this up, we'll set
a secret to configure the CumulusCI github service.

First, follow GitHub's instructions to `create a Personal Access Token
<https://help.github.com/en/github/authenticating-to-github/creating-a-personal-access-token-for-the-command-line>`_.

Now, in your repository's Secrets settings, click the "Add a new secret"
link. Enter ``CUMULUSCI_SERVICE_github`` as the Name of the secret. For
the Value, enter the following JSON:

.. code-block:: json

   {"username": "USERNAME", "password": "TOKEN", "email": "EMAIL"}

But replace ``USERNAME`` with your github username, ``TOKEN`` with the Personal
Access Token you just created, and ``EMAIL`` with your email address.
Finally, click the "Add secret" button to save the secret.



``SFDX_AUTH_URL``
^^^^^^^^^^^^^^^^^
CumulusCI needs to be able to access a Salesforce org with the Dev Hub feature enabled in order to create scratch orgs.
The easiest way to do this is to set up this connection locally, then copy its sfdx auth URL to a secret on GitHub.

Since you already have CumulusCI working locally, you should be able to run ``sfdx force:org:list`` to identify the username that is configured as the default Dev Hub username it is marked with ``(D)``.

Now run ``sfdx force:org:display --verbose -u [username]``, replacing ``[username]`` with your Dev Hub username.
Look for the ``Sfdx Auth Url`` and copy it.

.. warning::
   *Important: Treat this URL like a password. It provides access to log in
   as this user!*

Now in your repository's Secrets settings, click the 'Add a new secret' link.
Enter ``SFDX_AUTH_URL`` as the Name of the secret, and the URL from above as the Value.
Click the 'Add secret' button to save the secret.

.. note::
   Advanced note: These instructions connect sfdx to your Dev Hub using
   the standard Salesforce CLI connected app and a refresh token. It is
   also possible to authenticate sfdx using the ``force:auth:jwt:grant``
   command with a custom connected app client id and private key.

Your Secrets should look like this:

.. image:: images/github_secrets.png
   :alt: Screenshot showing the CUMULUSCI_SERVICE_github and SFDX_AUTH_URL secrets



Test the Workflow
-----------------
Now you should be able to try out the workflow.
Commit the new ``.github/workflows/apex_tests.yml`` file to the repository and push the commit to GitHub.
You should be able to watch the status of this workflow in the repository's Actions tab:

.. image:: images/github_workflow.png
   :alt: Screenshot showing a running GitHub Action workflow

If you open a pull request for a branch that includes the workflow, you will find a section at the bottom of the pull request that shows the results of the checks that were performed by the workflow:

.. image:: images/github_checks.png
   :alt: Screenshot showing a successful check on a GitHub pull request

It is possible to configure the repository's main branch as a *protected branch* so that changes can only be merged to it if these checks are passing.

See GitHub's documentation for instructions to `configure protected branches <https://help.github.com/en/github/administering-a-repository/configuring-protected-branches>`_ and `enable required status checks <https://help.github.com/en/github/administering-a-repository/enabling-required-status-checks>`_.



Run Headless Browser Tests
--------------------------
It is possible to run Robot Framework tests that control a real browser
as long as the CI environment has the necessary software installed. For
Chrome, it must have Chrome and chromedriver. For Firefox, it must have
Firefox and geckodriver.

Fortunately GitHub Actions comes preconfigured with an image that
includes these browsers. However it is necessary to run the browser in
headless mode. When using CumulusCI's ``robot`` task, this can be done
by passing the ``-o vars BROWSER:headlesschrome`` option.

Here is a complete workflow to run Robot Framework tests for any commit:

.. code-block:: yaml

   name: Robot Tests

   on: [push]

   env:
     CUMULUSCI_KEYCHAIN_CLASS: cumulusci.core.keychain.EnvironmentProjectKeychain
     CUMULUSCI_SERVICE_github: ${{ secrets.CUMULUSCI_SERVICE_github }}

   jobs:
     unit_tests:
       name: "Run Robot Framework tests"
       runs-on: ubuntu-latest
       steps:
       - uses: actions/checkout@v2
       - name: Install sfdx
         run: |
           mkdir sfdx
           wget -qO- https://developer.salesforce.com/media/salesforce-cli/sfdx-linux-amd64.tar.xz | tar xJ -C sfdx --strip-components 1
           ./sfdx/install
           echo ${{ secrets.SFDX_AUTH_URL }} > sfdx_auth
           sfdx force:auth:sfdxurl:store -f sfdx_auth -d
       - name: Set up Python
         uses: actions/setup-python@v1
         with:
           python-version: "3.8"
       - name: Install CumulusCI
         run: |
           python -m pip install -U pip
           pip install cumulusci
       - run: |
           cci task run robot --org dev -o vars BROWSER:headlesschrome
       - name: Store robot results
         uses: actions/upload-artifact@v1
         with:
           name: robot
           path: robot/CumulusCI-Test/results
       - name: Delete scratch org
         if: always()
         run: |
           cci org scratch_delete dev



References
----------

- `GitHub Actions Documentation <https://help.github.com/en/actions>`_

