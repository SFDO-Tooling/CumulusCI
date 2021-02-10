Continuous Integration
======================

The "CI" in CumulusCI stands for "continuous integration." Continuous integration is the practice of automatically running a project’s tests for any change before that change is merged to the ``main`` branch. This practice helps keep the ``main`` branch in a state where it can be released at any time, because the repository can be configured to protect the ``main`` branch so that changes can only be merged if the tests have passed.

Teams can put in significant effort to create bespoke automation for CumulusCI that is tailored to their project's specific needs. When created, the automation is available to all project participants; from Developers and Quality Engineers, to Documentation Writers and Product Managers. CumulusCI lets you take this reuse of automation one step further by letting it run in the context of CI systems like GitHub Actions, CircleCI, or Azure Pipelines. This consistent reuse of automation from local environments to cloud based CI systems gives teams the ability to develop, test, and deploy their projects with the confidence.



CumulusCI Flow
--------------

CumulusCI Flow is the process by which Salesforce metadata is developed, tested, and deployed to our customers. It is similar to the GitHub Flow, with a few tweaks and additions. The `CumulusCI Flow<TODO>`_ section covers everything from branching and merging strategies, which CumulusCI flows are intended for CI builds, automatically generating product documentation, and more.



CumulusCI in GitHub Actions
---------------------------

GitHub actions let you to specify custom workflows that can be run directly in your GitHub repository. These workflows can perform a variety of tasks, like running test suites, performing linting checks on your code, and creating code coverage reports. CumulusCI makes GitHub actions even more powerful by letting you leverage the custom automation defined in the ``cumulusci.yml`` file, and execute it from within your custom workflows. This feature lets you do things like spin up a scratch org, load in your projects Metadata, and execute Apex or Robot tests against the org.

If you're an Engineer aiming to set up CumulusCI in GitHub action, the `GitHub Actions<TODO>`_ section includes everything from a sample workflow to which secrets NEED TO configured.



MetaCI
------

The Salesforce.org release engineering team, that built CumulusCI, also maintains a CI system called `MetaCI <https://github.com/SFDO-Tooling/MetaCI>`_. MetaCI is an open source app built to run on Heroku, and is designed specifically to work with CumulusCI and Salesforce. Setting up MetaCI is an involved process that requires experience in working with apps on Heroku and CumulusCI.

For additional information on MetaCI visit the `GitHub Repository <https://github.com/SFDO-Tooling/MetaCI>`_.
 


Further Reading
---------------

.. toctree::
   :maxdepth: 1

   cumulusci_flow.rst
   github_actions.rst


