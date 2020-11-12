Continuous Integration
======================
The “CI” in CumulusCI stands for “continuous integration.”
Continuous integration is the practice of automatically running
a project’s tests for any change before that change is merged to the main branch.
This helps keep the main branch in a state where it can be released at
any time, because the repository can be configured to protect the main branch
so that changes can only be merged if the tests have passed.

CumulusCI flows can be run on your own computer, or they can be run
in a CI system such as GitHub Actions, CircleCI, or Azure Pipelines.
This recipe will show how to use GitHub Actions to run Apex tests in a scratch org after every commit.
(For other CI systems the steps should be similar, though the details of the configuration will be different.)


.. toctree::
   :maxdepth: 2

   cumulusci_flow.rst
   github_actions.rst



MetaCI
------
The Salesforce.org release engineering team, which built CumulusCI, also maintains a CI system called `MetaCI <https://github.com/SFDO-Tooling/MetaCI>`_.
MetaCI is an open source app built to run on Heroku, and is designed specifically to work with CumulusCI and Salesforce.
However, MetaCI is a bit complicated to set up and operate, so this recipe aims to provide a simpler alternative that can work fine in many cases.
For additional information on MetaCI visit the `GitHub Repository <https://github.com/SFDO-Tooling/MetaCI>`_.