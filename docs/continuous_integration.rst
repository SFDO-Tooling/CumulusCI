Continuous Integration
======================

The "CI" in CumulusCI stands for "continuous integration." Continuous integration is the practice of automatically running a project's tests for any change before that change is merged to the ``main`` branch in the repository. Continuous integration also configures the repository so that changes are merged only if the tests have passed. This practice keeps the ``main`` branch in an error-free state where it can be released any time.

Teams can put in significant effort to create bespoke automation for CumulusCI tailored to their project's needs. When created, the automation is available to all project participants, from Developers and Quality Engineers, to Documentation Writers and Product Managers. CumulusCI takes this reuse of automation one step further by letting it run in the context of CI systems like GitHub Actions, CircleCI, or Azure Pipelines. This consistent reuse of automation from local environments to cloud-based CI systems gives teams the ability to develop, test, and deploy their projects with confidence.



CumulusCI Flow
--------------

CumulusCI Flow is the process by which Salesforce metadata is developed, tested, and deployed to our customers. It is similar to the GitHub Flow with a few tweaks and additions. To learn more about which CumulusCI flows are best designed for CI builds, branching and merging strategies for repositories, generating product documentation during project initialization, and more, see `CumulusCI Flow<TODO>`_.



CumulusCI in GitHub Actions
---------------------------

GitHub Actions specify custom workflows that run directly in your GitHub repository. These workflows perform a variety of tasks, like running test suites, performing linting checks on your code, and creating code coverage reports. CumulusCI makes GitHub Actions even more powerful by letting you leverage the custom automation defined in the ``cumulusci.yml`` file, and execute it from within your custom workflows. This feature gives you the discretion to spin up a scratch org, load in your project's metadata, and execute Apex or Robot tests against the org.

To learn more about sample workflows, the secrets that require configuration, caching dependencies, and more, see `GitHub Actions<TODO>`_ .



MetaCI
------

The Salesforce.org release engineering team that built CumulusCI also maintains *MetaCI*, a specialized lightweight CI server for building Salesforce projects from GitHub repositories using CumulusCI flows. MetaCI is an open source app built to run on Heroku, and is designed specifically to work with CumulusCI and Salesforce.

Setting up MetaCI is an involved process that requires experience working with apps on Heroku and CumulusCI. To learn more about MetaCI and how to run it with a project, see `MetaCI <https://github.com/SFDO-Tooling/MetaCI>`_.
 


Further Reading
---------------

.. toctree::
   :maxdepth: 1

   cumulusci_flow.rst
   github_actions.rst


