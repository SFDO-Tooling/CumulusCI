Configuring CumulusCI
=====================

The ``cumulusci.yml`` File(s)
-----------------------------
For the vast majority of cases in our documentation, when we reference ``cumulusci.yml``, we are referring to the ``cumulusci.yml`` file located in your project's root directory.
In actuality, CumulusCI synthesizes multiple `YAML <https://yaml.org/>`_ files that allow for CumulusCI to be configured at several distinct levels. 
All of thes files are have the same name- ``cumulusci.yml`` -but live in different locations on the file system. 

Global Overrides
^^^^^^^^^^^^^^^^
**File Path:** ``~/.cumulusci/cumulusci.yml``

Configuration of this file will override behavior across *all* CumulusCI projects. 
TODO: Example

Project Overrides
^^^^^^^^^^^^^^^^^
**File Path:** ``~/.cumulusci/<project_name>/cumulusci.yml``

This ``cumulusci.yml`` file lives in the root directory of your project (typically a github repository too).
Configuration made here applies specifically to this project.
Changes to this file can be commited back to a remote repository so other team members can benefit from these customizations.
For example, maybe your project has a set of sObject records that need to be inserted after package installation.
e default ``dev_org`` flow 

Local Project Overrides 
^^^^^^^^^^^^^^^^^^^^^^^
**File Path:** ``path/to/<project_name>/cumulusci.yml``

Configurations made to this ``cumulusci.yml`` file apply to only the project with the given <project_name>.
If you want to make customizations to a project, but don't need them to be available to other team members, you would make those customizations here.

One Last ``cumulusci.yml``
^^^^^^^^^^^^^^^^^^^^^^^^^^^
There is one more configuration file that exists; the internal ``cumulusci.yml`` file that ships with CumulusCI itself.
This master ``cumulusci.yml`` file, contains all of the standard tasks, flows, and configurations that are available out of the box with CumulusCI.



Environment Variables
---------------------
CumulusCI has certain environment variables that are helpful to set when running inside of web applications.
The following is a reference list of available environment variables that can be set.

| ``CUMULUSCI_AUTO_DETECT``
| Set this environment variable to autodetect branch and commit information from ``HEROKU_TEST_RUN_BRANCH`` and ``HEROKU_TEST_RUN_COMMIT_VERSION`` environment variables.
|

| ``CUMULUSCI_DISABLE_REFRESH``
| If present, will instruct CumulusCI to not refresh oAuth tokens for orgs.
|

| ``CUMULUSCI_KEY``
| An alphanumeric string used to encrypt org credentials at rest when an OS keychain is not available.
|

| ``CUMULUSCI_REPO_URL``
| Used for specifying a Github Repository for CumulusCI to use when running in a CI environment.
|

| ``GITHUB_APP_ID``
| Your GitHub App's identifier.
|

| ``GITHUB_APP_KEY``
| Contents of a JSON Web Token (JWT) used to authenticate a GitHub app (see `GitHub’s docs <https://developer.github.com/apps/building-github-apps/authenticating-with-github-apps/#authenticating-as-a-github-app>`_).
|

| ``GITHUB_TOKEN``
| A GitHub `personal access token <https://help.github.com/en/github/authenticating-to-github/creating-a-personal-access-token-for-the-command-line>`_.
|

| ``HEROKU_TEST_RUN_BRANCH``
| Used for specifying a specific branch to test against in a Heroku CI environment
|

| ``HEROKU_TEST_RUN_COMMIT_VERSION``
| Used to specify a specific commit to test against in a Heroku CI environment.
|

| ``SFDX_CLIENT_ID``
| Client ID for a Connected App used to authenticate to a persistent org, e.g. a Developer Hub. Set with SFDX_HUB_KEY.
|

| ``SFDX_HUB_KEY``
| Contents of JSON Web Token (JWT) used to authenticate to a persistent org, e.g. a Developer Hub.  Set with SFDX_CLIENT_ID.
|

| ``SFDX_ORG_CREATE_ARGS``
| Extra arguments passed to ``sfdx force:org:create``. Can be used to pass key-value pairs.
|
